"""
ubxsave.py

NB: ONLY FOR GENERATION 9+ UBX DEVICES e.g. NEO-M9N, ZED-F9P

CLI utility which saves Generation 9+ UBX device configuration data to a file. `ubxsave` polls
configuration data via the device's serial port using a series of CFG-VALGET poll messages. It
parses the responses to these polls, converts them to CFG-VALSET command messages and saves these
to a binary file. This binary file can then be loaded into any compatible UBX device (e.g. via
the `ubxload` utility) to restore the saved configuration.

The CFG-VALSET commands are stored as a single transaction, so if one or more fails on reload, the
entire set will be rejected.

*NB*: The utility relies on receiving a complete set of poll responses within a specified
`waittime`. If the device is exceptionally busy or the transmit buffer is full, poll responses
may be delayed or dropped altogether. If the utility reports errors, try increasing the
waittime and/or baudrate or temporarily reducing periodic message rates.

Usage (all kwargs are optional):

> ubxsave port=/dev/ttyACM1 baud=9600 timeout=0.02 outfile=ubxconfig.ubx verbose=1

Created on 06 Jan 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""
# pylint: disable=invalid-name

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from math import ceil
from queue import Queue
from threading import Event, Lock, Thread
from time import sleep, strftime

from pyubx2 import (
    POLL_LAYER_RAM,
    SET_LAYER_RAM,
    TXN_COMMIT,
    TXN_ONGOING,
    TXN_START,
    UBX_CONFIG_DATABASE,
    UBX_PROTOCOL,
    UBXMessage,
    UBXReader,
)
from serial import Serial

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import EPILOG

# try increasing these values if device response is too slow:
DELAY = 0.02  # delay between polls
WRAPUP = 5  # delay for final responses


def progbar(i: int, lim: int, inc: int = 50):
    """
    Display progress bar on console.
    """

    i = min(i, lim)
    pct = int(i * inc / lim)
    if not i % int(lim / inc):
        print(
            f"{int(pct*100/inc):02}% " + "\u2593" * pct + "\u2591" * (inc - pct),
            end="\r",
        )


class UBXSaver:
    """UBX Configuration Saver Class."""

    def __init__(self, file: object, stream: object, **kwargs):
        """Constructor."""

        self._file = file
        self._stream = stream
        self._verbose = int(kwargs.get("verbosity", 1))
        self._waittime = ceil(kwargs.get("waittime", WRAPUP))

        self._ubxreader = UBXReader(stream, protfilter=UBX_PROTOCOL)

        self._serial_lock = Lock()
        self._save_queue = Queue()
        self._send_queue = Queue()
        self._stop_event = Event()

        self._write_thread = Thread(
            target=self._write_data,
            daemon=True,
            args=(
                stream,
                self._send_queue,
                self._serial_lock,
            ),
        )
        self._read_thread = Thread(
            target=self._read_data,
            daemon=True,
            args=(
                self._stream,
                self._ubxreader,
                self._save_queue,
                self._serial_lock,
                self._stop_event,
            ),
        )
        self._save_thread = Thread(
            target=self._save_data,
            daemon=True,
            args=(
                self._file,
                self._save_queue,
            ),
        )

        self._msg_write = (
            self._msg_sent
        ) = self._msg_rcvd = self._msg_save = self._cfgkeys = 0

    def _write_data(self, stream: object, queue: Queue, lock: Lock):
        """
        Read send queue containing CFG-VALGET poll requests and
        send these to the device
        """

        while True:
            message = queue.get()
            lock.acquire()
            stream.write(message.serialize())
            self._msg_write += 1
            if self._verbose > 1:
                print(f"WRITE {self._msg_write} - {message.identity}")
            lock.release()
            queue.task_done()

    def _read_data(
        self,
        stream: object,
        ubr: UBXReader,
        queue: Queue,
        lock: Lock,
        stop: Event,
    ):
        """
        Read incoming CFG-VALGET poll responses from device and
        place on save queue. NB: we won't know how many poll
        responses to expect.
        """
        # pylint: disable=broad-except

        while not stop.is_set():
            try:
                if stream.in_waiting:
                    lock.acquire()
                    (raw_data, parsed_data) = ubr.read()
                    lock.release()
                    if parsed_data is not None:
                        if parsed_data.identity == "CFG-VALGET":
                            queue.put((raw_data, parsed_data))
                            self._msg_rcvd += 1
                            if self._verbose > 1:
                                print(
                                    f"RESPONSE {self._msg_rcvd} - {parsed_data.identity}"
                                )
            except Exception as err:
                if not stop.is_set():
                    print(f"\n\nSomething went wrong {err}\n\n")
                continue

    def _save_data(self, file: object, queue: Queue):
        """
        Get CFG-VALGET poll responses from save queue, convert to
        CFG-VALSET commands and save to binary file.
        """

        i = 0
        while True:
            cfgdata = []
            while queue.qsize() > 0:
                (_, parsed) = queue.get()
                if parsed.identity == "CFG-VALGET":
                    for keyname in dir(parsed):
                        if keyname[0:3] == "CFG":
                            cfgdata.append((keyname, getattr(parsed, keyname)))
                queue.task_done()
                if len(cfgdata) >= 64:  # up to 64 keys in each CFG-VALSET
                    txn = TXN_ONGOING if i else TXN_START
                    self._file_write(file, txn, cfgdata)
                    cfgdata = []
                    i += 1
            if len(cfgdata) > 0:
                self._file_write(file, TXN_COMMIT, cfgdata)

    def _file_write(self, file: object, txn: int, cfgdata: list):
        """
        Write binary CFG-VALSET message data to output file.
        """

        if len(cfgdata) == 0:
            return
        self._msg_save += 1
        self._cfgkeys += len(cfgdata)
        data = UBXMessage.config_set(
            layers=SET_LAYER_RAM, transaction=txn, cfgData=cfgdata
        )
        if self._verbose > 1:
            print(f"SAVE {self._msg_save} - {data.identity}")
        file.write(data.serialize())

    def run(self):
        """
        Main save routine.
        """

        rc = 1
        if self._verbose:
            print(
                f"\nSaving configuration from {self._stream.port} to {self._file.name} ..."
            )
            print("Press Ctrl-C to terminate early.")

        # loop until all commands sent or user presses Ctrl-C
        try:
            self._write_thread.start()
            self._read_thread.start()

            layer = POLL_LAYER_RAM
            position = 0
            keys = []
            for i, key in enumerate(UBX_CONFIG_DATABASE):
                if self._verbose == 1:
                    progbar(i, len(UBX_CONFIG_DATABASE), 50)
                keys.append(key)
                msg = UBXMessage.config_poll(layer, position, keys)
                self._send_queue.put(msg)
                self._msg_sent += 1
                if self._verbose > 1:
                    print(f"POLL {i} - {msg.identity}")
                keys = []
                sleep(DELAY)

            if self._verbose:
                for i in range(self._waittime):
                    print(
                        f"Waiting {self._waittime - i} seconds for final responses..."
                        + " " * 20,
                        end="\r",
                    )
                    sleep(1)
            # sleep(self._waittime)

            self._stop_event.set()
            self._send_queue.join()
            self._save_thread.start()
            self._save_queue.join()

        except KeyboardInterrupt:  # capture Ctrl-C
            self._stop_event.set()
            print("\n\nTerminated by user. WARNING! Configuration may be incomplete.")

        if self._msg_rcvd == self._cfgkeys:
            if self._verbose:
                print(
                    "Configuration successfully saved." + " " * 15,
                    f"\n{self._msg_save} CFG-VALSET messages saved to {self._file.name}",
                )
        else:
            rc = 0
            if self._verbose:
                print(
                    "WARNING! Configuration not successfully saved",
                    f"\n{self._msg_sent} CFG-VALGET polls sent to {self._stream.port}",
                    f"\n{self._msg_rcvd} CFG-VALGET responses received",
                    f"\n{self._msg_save} CFG-VALSET messages containing {self._cfgkeys} keys",
                    f"({self._cfgkeys*100/self._msg_rcvd:.1f}%) written to {self._file.name}",
                    f"\nConsider increasing waittime to >{self._waittime}.",
                )

        return rc


def main():
    """
    CLI Entry Point.

    :param: as per UBXSaver constructor.
    """

    ap = ArgumentParser(epilog=EPILOG, formatter_class=ArgumentDefaultsHelpFormatter)
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument("-P", "--port", required=True, help="Serial port")
    ap.add_argument(
        "-O",
        "--outfile",
        required=False,
        help="Output file",
        default=f"ubxconfig-{strftime('%Y%m%d%H%M%S')}.ubx",
    )
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
        default=0.2,
    )
    ap.add_argument(
        "--waittime",
        required=False,
        help="Wait time in seconds",
        type=int,
        default=WRAPUP,
    )
    ap.add_argument(
        "--verbosity",
        required=False,
        help="Verbosity 0 = low, 1 = medium, 2 = high, 3 = debug",
        type=int,
        choices=[0, 1, 2, 3],
        default=1,
    )

    args = ap.parse_args()

    with open(args.outfile, "wb") as outfile:
        with Serial(args.port, args.baudrate, timeout=args.timeout) as serial_stream:
            ubs = UBXSaver(
                outfile, serial_stream, verbosity=args.verbosity, waittime=args.waittime
            )
            ubs.run()


if __name__ == "__main__":
    main()
