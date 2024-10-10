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

Created on 06 Jan 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

# pylint: disable=invalid-name

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from datetime import datetime, timedelta
from logging import getLogger
from math import ceil
from queue import Queue
from threading import Event, Lock, Thread
from time import sleep

from pyubx2 import (
    NMEA_PROTOCOL,
    SETPOLL,
    UBX_PROTOCOL,
    UBXMessageError,
    UBXParseError,
    UBXReader,
)
from serial import Serial

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import EPILOG, VERBOSITY_HIGH
from pygnssutils.helpers import progbar, set_common_args

ACK = "ACK-ACK"
NAK = "ACK-NAK"
WAITTIME = 5  # wait time for acknowledgements
WRITETIME = 0.02  # wait time between writes


class UBXLoader:
    """UBX Configuration Loader Class."""

    def __init__(self, stream: object, **kwargs):
        """
        Constructor.

        :param object file: input file
        :param object stream: output serial stream
        """

        self.logger = getLogger(__name__)
        self._stream = stream
        self._filename = kwargs["infile"]
        self._waittime = ceil(kwargs.get("waittime", WAITTIME))
        self._ubxreader = UBXReader(
            self._stream, protfilter=NMEA_PROTOCOL | UBX_PROTOCOL
        )
        self._serial_lock = Lock()
        self._out_queue = Queue()
        self._stop_event = Event()
        self._last_ack = datetime.now()
        self._read_thread = Thread(
            target=self._read_data,
            daemon=True,
            args=(
                stream,
                self._ubxreader,
                self._out_queue,
                self._stop_event,
            ),
        )

        self._msg_ack = self._msg_nak = self._msg_write = self._msg_load = 0

    def _load_data(self, filename: str, queue: Queue):
        """
        Get CFG-VALSET data from file and place it on output queue.
        """

        with open(filename, "rb") as stream:
            ubl = UBXReader(stream, msgmode=SETPOLL)
            eof = False
            while not eof:
                (raw_data, parsed_data) = ubl.read()
                if raw_data is None:
                    eof = True
                else:
                    self._msg_load += 1
                    queue.put(parsed_data)
                    self.logger.debug(f"LOAD {self._msg_load} - {parsed_data.identity}")

    def _read_data(
        self,
        stream: object,
        ubr: UBXReader,
        queue: Queue,
        stop: Event,
    ):
        """
        Read incoming acknowledgements from device
        """
        # pylint: disable=broad-except

        # read until expected no of acknowledgements has been received
        # or waittime has been exceeded.
        while not stop.is_set():
            try:
                (_, parsed_data) = ubr.read()
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
                        self.logger.debug(
                            f"ACKNOWLEDGEMENT {self._msg_ack + self._msg_nak} - {parsed_data}"
                        )

                # send config message(s) to receiver
                if not queue.empty():
                    i = 0
                    while not queue.empty():
                        i += 1
                        n = ceil(50 / self._msg_load)
                        progbar(i * n, self._msg_load * n, 50)
                        parsed_data = queue.get()
                        self._msg_write += 1
                        self.logger.debug(
                            f"WRITE {self._msg_write} {parsed_data.identity}"
                        )
                        stream.write(parsed_data.serialize())
                        sleep(WRITETIME)
                    queue.task_done()

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
                    self.logger.error(f"Something went wrong {err}")
                continue

    def run(self):
        """
        Run configuration load routines.
        """

        rc = 1
        self.logger.info(
            f"Loading configuration from {self._filename} to {self._stream.port}. "
            "Press Ctrl-C to terminate early.",
        )

        self._load_data(self._filename, self._out_queue)
        self._read_thread.start()

        # loop until all commands sent or user presses Ctrl-C
        while not self._stop_event.is_set():
            try:
                sleep(1)
            except KeyboardInterrupt:  # capture Ctrl-C
                self.logger.warning(
                    "Terminated by user. Configuration may be incomplete."
                )
                self._stop_event.set()

        self._read_thread.join()

        if self._msg_ack == self._msg_load:
            self.logger.info(
                "Configuration successfully loaded. "
                f"{self._msg_load} CFG-VALSET messages sent and acknowledged."
            )
        else:
            null = self._msg_load - self._msg_ack - self._msg_nak
            rc = 0
            self.logger.warning(
                "Configuration may be incomplete. "
                f"{self._msg_load} CFG-VALSET messages sent, "
                f"{self._msg_ack} acknowledged, {self._msg_nak} rejected, "
                f"{null} null responses."
            )
            if null:
                self.logger.warning(
                    f"Consider increasing waittime to >{self._waittime} seconds."
                )
            if self._msg_nak:
                self.logger.warning(
                    "Check device is compatible with this saved configuration."
                )

        return rc


def main():
    """
    CLI Entry point.

    :param: as per UBXLoader constructor.
    """

    ap = ArgumentParser(epilog=EPILOG, formatter_class=ArgumentDefaultsHelpFormatter)
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument("-I", "--infile", required=True, help="Input file")
    ap.add_argument("-P", "--port", required=True, help="Serial port")
    ap.add_argument(
        "--baudrate",
        required=False,
        help="Serial baud rate",
        type=int,
        choices=[4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800],
        default=9600,
    )
    ap.add_argument(
        "--timeout",
        required=False,
        help="Serial timeout in seconds",
        type=float,
        default=3.0,
    )
    ap.add_argument(
        "--waittime",
        required=False,
        help="Wait time in seconds",
        type=float,
        default=WAITTIME,
    )

    kwargs = set_common_args("ubxload", ap, logdefault=VERBOSITY_HIGH)

    with Serial(
        kwargs.pop("port"), kwargs.pop("baudrate"), timeout=kwargs.pop("timeout")
    ) as serial_stream:
        ubl = UBXLoader(serial_stream, **kwargs)
        ubl.run()


if __name__ == "__main__":
    main()
