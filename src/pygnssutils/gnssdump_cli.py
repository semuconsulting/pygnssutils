"""
gnssdump_cli.py

CLI wrapper for GNSSStreamer class.

Created on 24 Jul 2024

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from queue import Queue
from threading import Thread

from serial import Serial

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import (
    CLIAPP,
    EPILOG,
    FORMAT_BINARY,
    FORMAT_HEX,
    FORMAT_HEXTABLE,
    FORMAT_JSON,
    FORMAT_PARSED,
    FORMAT_PARSEDSTRING,
    OUTPUT_FILE,
    OUTPUT_HANDLER,
    OUTPUT_NONE,
    OUTPUT_SERIAL,
    OUTPUT_SOCKET,
)
from pygnssutils.gnssstreamer import GNSSStreamer
from pygnssutils.helpers import set_common_args
from pygnssutils.socket_server import runserver


def runclient(**kwargs):
    """
    Start GNSSStreamer with CLI parameters.
    """

    with GNSSStreamer(CLIAPP, **kwargs) as gns:
        gns.run()


def main():
    """
    CLI Entry point.

    :param: as per GNSSStreamer constructor.
    :raises: ParameterError if parameters are invalid
    """
    # pylint: disable=raise-missing-from

    ap = ArgumentParser(
        description="One of either -P port, -S socket or -F filename must be specified",
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument("-P", "--port", required=False, help="Serial port")
    ap.add_argument("-F", "--filename", required=False, help="Input file path/name")
    ap.add_argument(
        "-S",
        "--socket",
        required=False,
        help="Input socket host:port; enclose IPv6 host in []",
    )
    ap.add_argument(
        "--ipprot",
        required=False,
        help="IP protocol (for Socket connections)",
        choices=["IPv4", "IPv6"],
        default="IPv4",
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
        default=3.0,
    )
    ap.add_argument(
        "--format",
        required=False,
        help=(
            f"{FORMAT_PARSED} - parsed as object; "
            f"{FORMAT_BINARY} - binary (raw); "
            f"{FORMAT_HEX} - hexadecimal; "
            f"{FORMAT_HEXTABLE} - tabular hexadecimal; "
            f"{FORMAT_PARSEDSTRING} - parsed as string; "
            f"{FORMAT_JSON} - JSON. "
            f"Options can be OR'd e.g. {FORMAT_PARSED} | {FORMAT_HEXTABLE}."
        ),
        type=int,
        default=FORMAT_PARSED,
    )
    ap.add_argument(
        "--validate",
        required=False,
        help="1 = validate checksums, 0 = do not validate",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--msgmode",
        required=False,
        help="0 = GET, 1 = SET, 2 = POLL, 3 = SETPOLL",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
    )
    ap.add_argument(
        "--parsebitfield",
        required=False,
        help="1 = parse UBX 'X' attributes as bitfields, 0 = leave as bytes",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--quitonerror",
        required=False,
        help="0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors",
        type=int,
        choices=[0, 1, 2],
        default=1,
    )
    ap.add_argument(
        "--protfilter",
        required=False,
        help="1 = NMEA, 2 = UBX, 4 = RTCM3 (can be OR'd)",
        type=int,
        choices=[1, 2, 3, 4, 5, 6, 7],
        default=7,
    )
    ap.add_argument(
        "--msgfilter",
        required=False,
        help=(
            "Comma-separated string of message identities e.g. 'NAV-PVT,GNGSA,1087'. "
            + "A period clause may be added to each msg identity e.g. 1087(10), "
            + "signifying the minimum period in seconds between messages of this type."
        ),
        default=None,
    )
    ap.add_argument(
        "--limit",
        required=False,
        help="Maximum number of messages to read (0 = unlimited)",
        type=int,
        default=0,
    )
    ap.add_argument(
        "--clioutput",
        required=False,
        help=(
            f"CLI output type {OUTPUT_NONE} = none, "
            f"{OUTPUT_FILE} = binary file, "
            f"{OUTPUT_SERIAL} = serial port, "
            f"{OUTPUT_SOCKET} = TCP socket server, "
            f"{OUTPUT_HANDLER} = evaluable Python expression"
        ),
        type=int,
        choices=[
            OUTPUT_NONE,
            OUTPUT_FILE,
            OUTPUT_SERIAL,
            OUTPUT_SOCKET,
            OUTPUT_HANDLER,
        ],
        default=OUTPUT_NONE,
    )
    ap.add_argument(
        "--output",
        required=False,
        help=(
            f"Output medium as formatted string. "
            f"If clioutput = {OUTPUT_FILE}, format = file name (e.g. '/home/myuser/ubxdata.ubx'); "
            f"If clioutput = {OUTPUT_SERIAL}, format = port@baudrate (e.g. '/dev/tty.ACM0@38400'); "
            f"If clioutput = {OUTPUT_SOCKET}, format = hostip:port (e.g. '0.0.0.0:50010'); "
            f"If clioutput = {OUTPUT_HANDLER}, format = evaluable Python expression. "
            "NB: gnssdump will have exclusive use of any serial or server port."
        ),
        default=None,
    )
    kwargs = set_common_args(ap)

    cliout = int(kwargs.pop("clioutput", OUTPUT_NONE))
    try:
        if cliout == OUTPUT_FILE:
            filename = kwargs["output"]
            ftyp = "wb" if int(kwargs["format"]) == FORMAT_BINARY else "w"
            with open(filename, ftyp) as output:
                kwargs["output"] = output
                runclient(**kwargs)
        elif cliout == OUTPUT_SERIAL:
            port, baud = kwargs["output"].split("@")
            with Serial(port, int(baud), timeout=3) as output:
                kwargs["output"] = output
                runclient(**kwargs)
        elif cliout == OUTPUT_SOCKET:
            host, port = kwargs["output"].split(":")
            kwargs["output"] = Queue()
            # socket server runs as background thread, piping
            # output from ntrip client via a message queue
            Thread(
                target=runserver,
                args=(host, int(port), kwargs["output"]),
                daemon=True,
            ).start()
            runclient(**kwargs)
        elif cliout == OUTPUT_HANDLER:
            kwargs["output"] = eval(kwargs["output"])  # pylint: disable=eval-used
            runclient(**kwargs)
        else:
            kwargs["output"] = None
            runclient(**kwargs)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
