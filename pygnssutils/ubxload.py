"""
ubxload.py

NB: ONLY FOR GENERATION 9+ UBX DEVICES e.g. NEO-M9N, ZED-F9P

This command line utility reads UBX configuration data from a
binary file and loads this into a compatible UBX device via its
serial port. It then confirms that the data has been
successfully acknowledged by the device, or reports any errors.

The binary file is created using the ubxsave utility and contains
a series of CFG-VALSET messages representing the complete
configuration of the source device.

Usage (all kwargs are optional):

> ubxload port=/dev/ttyACM1 baud=9600 timeout=0.05 infile=ubxconfig.ubx verbose=1

Created on 06 Jan 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

import sys
from math import ceil
from datetime import datetime, timedelta
from threading import Thread, Event, Lock
from queue import Queue
from serial import Serial
from pyubx2 import UBXReader, UBX_PROTOCOL, SET, UBXMessageError, UBXParseError
from pygnssutils._version import __version__ as VERSION
from pygnssutils.helpstrings import UBXLOAD_HELP

ACK = "ACK-ACK"
NAK = "ACK-NAK"
# try increasing these values if device response is too slow:
DELAY = 0.05  # delay between sends
WRAPUP = 5  # final wrap up delay
WAITTIME = 5  # wait time for acknowledgements


class UBXLoader:
    """UBX Configuration Loader Class."""

    def __init__(self, file: object, stream: object, **kwargs):
        """
        Constructor.

        :param object file: input file
        :param object stream: output serial stream
        """

        self._file = file
        self._stream = stream
        self._waittime = ceil(kwargs.get("waitime", WAITTIME))
        self._verbose = int(kwargs.get("verbosity", 1))
        self._ubxreader = UBXReader(self._stream, protfilter=UBX_PROTOCOL)
        self._ubxloader = UBXReader(self._file, protfilter=UBX_PROTOCOL, msgmode=SET)

        self._serial_lock = Lock()
        self._out_queue = Queue()
        self._stop_event = Event()
        self._last_ack = datetime.fromordinal(1)

        self._write_thread = Thread(
            target=self._write_data,
            daemon=True,
            args=(
                stream,
                self._out_queue,
                self._serial_lock,
            ),
        )
        self._read_thread = Thread(
            target=self._read_data,
            daemon=True,
            args=(
                stream,
                self._ubxreader,
                self._serial_lock,
                self._stop_event,
            ),
        )

        self._msg_ack = self._msg_nak = self._msg_write = self._msg_load = 0

    def _load_data(self, ubr: UBXReader, queue: Queue):
        """
        Get CFG-VALSET data from file and place it on output queue.
        """

        eof = False
        while not eof:

            (_, parsed_data) = ubr.read()
            if parsed_data is None:
                eof = True
            else:
                self._msg_load += 1
                queue.put(parsed_data)
                if self._verbose > 1:
                    print(f"LOAD {self._msg_load} - {parsed_data.identity}")

    def _write_data(self, stream: object, queue: Queue, lock: Lock):
        """
        Read output queue and send CFG-VALSET messages to device.
        """

        while True:

            parsed_data = queue.get()
            if parsed_data is not None:
                lock.acquire()
                stream.write(parsed_data.serialize())
                lock.release()
                self._msg_write += 1
                if self._verbose > 1:
                    print(f"WRITE {self._msg_write} - {parsed_data.identity}")
            queue.task_done()

    def _read_data(
        self,
        stream: object,
        ubr: UBXReader,
        lock: Lock,
        stop: Event,
    ):
        """
        Read incoming acknowledgements from device
        """
        # pylint: disable=broad-except

        # read until expected no of acknowledgements has been received
        # or waittime has been exceeded.
        while not stop.is_set():

            if stream.in_waiting:
                try:
                    lock.acquire()
                    (_, parsed_data) = ubr.read()
                    lock.release()
                    if parsed_data is not None:
                        if (
                            parsed_data.identity in (ACK, NAK)
                            and parsed_data.clsID == 6  # CFG
                            and parsed_data.msgID == 138  # CFG-VALSET
                        ):
                            self._last_ack = datetime.now()
                            if parsed_data.identity == ACK:
                                self._msg_ack += 1
                            else:
                                self._msg_nak += 1
                            if self._verbose > 1:
                                print(
                                    f"ACKNOWLEDGEMENT {self._msg_ack + self._msg_nak} - {parsed_data}"
                                )
                    if (
                        self._msg_ack + self._msg_nak >= self._msg_load
                        or datetime.now()
                        > self._last_ack + timedelta(seconds=self._waittime)
                    ):
                        stop.set()
                except (UBXMessageError, UBXParseError):
                    continue
                except Exception as err:
                    if not stop.is_set():
                        print(f"\n\nSomething went wrong {err}\n\n")
                    continue

    def run(self):
        """
        Run configuration load routines.
        """

        if self._verbose:
            print(
                f"\nLoading configuration from {self._file.name} to {self._stream.port} ...",
                "\nPress Ctrl-C to terminate early.",
            )

        self._load_data(self._ubxloader, self._out_queue)
        self._write_thread.start()
        self._read_thread.start()

        # loop until all commands sent or user presses Ctrl-C
        while not self._stop_event.is_set():
            try:
                pass
            except KeyboardInterrupt:  # capture Ctrl-C
                print(
                    "\n\nTerminated by user. WARNING! Configuration may be incomplete."
                )
                self._stop_event.set()

        self._out_queue.join()

        if self._verbose:
            if self._msg_ack == self._msg_load:
                print(
                    "\nConfiguration successfully loaded.",
                    f"\n{self._msg_load} CFG-VALSET messages sent and acknowledged.",
                )
            else:
                null = self._msg_load - self._msg_ack - self._msg_nak
                print(
                    "\nWARNING! Configuration was not successfully loaded.",
                    f"\n{self._msg_load} CFG-VALSET messages sent,",
                    f"{self._msg_ack} acknowledged, {self._msg_nak} rejected,",
                    f"{null} null responses.",
                )
                if null:
                    print(f"Consider increasing waittime to >{self._waittime}.")
                if self._msg_nak:
                    print(f"Check device is compatible with this saved configuration.")


def main():
    """
    CLI Entry point.

    :param: as per UBXLoader constructor.
    """

    if len(sys.argv) > 1:
        if sys.argv[1] in {"-h", "--h", "help", "-help", "--help", "-H"}:
            print(UBXLOAD_HELP)
            sys.exit()
        if sys.argv[1] in {"-v", "--v", "-V", "--V", "version", "-version"}:
            print(VERSION)
            sys.exit()

    kwgs = dict(arg.split("=") for arg in sys.argv[1:])

    infile = kwgs.get("infile", "ubxconfig.ubx")
    port = kwgs.get("port", "/dev/ttyACM0")
    baudrate = int(kwgs.get("baud", 9600))
    timeout = float(kwgs.get("timeout", 0.05))
    waittime = ceil(kwgs.get("waittime", 5))
    verbosity = int(kwgs.get("verbosity", 1))

    with open(infile, "rb") as infile:
        with Serial(port, baudrate, timeout=timeout) as serial_stream:
            ubl = UBXLoader(
                infile, serial_stream, verbosity=verbosity, waittime=waittime
            )
            ubl.run()


if __name__ == "__main__":

    main()
