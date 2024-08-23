"""
gnssserver_cli.py

CLI wrapper for GNSSSocketServer class.

Created on 24 Jul 2024

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

import os
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from time import sleep

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import CLIAPP, EPILOG
from pygnssutils.gnssserver import GNSSSocketServer
from pygnssutils.helpers import set_common_args


def main():
    """
    CLI Entry point.

    :param int waittime: response wait time in seconds (1)
    :param: as per NSSSocketServer constructor.
    """

    ap = ArgumentParser(
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument("-I", "--inport", required=False, help="Input serial port")
    ap.add_argument("-S", "--socket", required=False, help="Input socket host:port")
    ap.add_argument(
        "-O",
        "--outport",
        required=False,
        help="Output TCP port",
        type=int,
        default=50010,
    )
    ap.add_argument(
        "--ipprot",
        required=False,
        help="IP protocol",
        choices=["IPv4", "IPv6"],
        default="IPv4",
    )
    ap.add_argument(
        "-H",
        "--hostip",
        required=False,
        help="Host IP Address Binding (0.0.0.0/:: = all)",
        default="0.0.0.0",
    )
    ap.add_argument(
        "-N",
        "--ntripmode",
        required=False,
        help="NTRIP Mode 0 = socket server, 1 = NTRIP caster",
        type=int,
        choices=[0, 1],
        default=0,
    )
    ap.add_argument(
        "--ntripversion",
        required=False,
        help="NTRIP version",
        type=str,
        choices=["1.0", "2.0"],
        default="2.0",
    )
    ap.add_argument(
        "--ntripuser",
        required=False,
        type=str,
        help="NTRIP caster authentication user",
        default=os.getenv("PYGPSCLIENT_USER", "anon"),
    )
    ap.add_argument(
        "--ntrippassword",
        required=False,
        type=str,
        help="NTRIP caster authentication password",
        default=os.getenv("PYGPSCLIENT_PASSWORD", "password"),
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
        help="Output format 1 = parsed, 2 = binary, 4 = hex, 8 = tabulated hex,"
        + "16 = parsed as string, 32 = JSON (can be OR'd)",
        type=int,
        default=2,
    )
    ap.add_argument(
        "-v",
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
        help="0 = GET, 1 = SET, 2 = POLL",
        type=int,
        choices=[0, 1, 2],
        default=0,
    )
    ap.add_argument(
        "--maxclients",
        required=False,
        help="Maximum number of clients",
        type=int,
        choices=range(1, 21),
        default=5,
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
        default=7,
    )
    ap.add_argument(
        "--msgfilter",
        required=False,
        help="Comma-separated string of message identities e.g. 'NAV-PVT,GNGSA'",
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
        "--outfile",
        required=False,
        help="Fully qualified path to output file",
        default=None,
    )
    ap.add_argument(
        "--waittime",
        required=False,
        help="Response wait time",
        type=int,
        default=1,
    )
    kwargs = set_common_args("gnssserver", ap)

    if kwargs["hostip"] == "0.0.0.0" and kwargs["ipprot"] == "IPv6":
        kwargs["hostip"] = "::"

    try:
        with GNSSSocketServer(CLIAPP, **kwargs) as server:
            goodtogo = server.run()

            while goodtogo:  # run until user presses CTRL-C
                sleep(kwargs["waittime"])
            sleep(kwargs["waittime"])

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
