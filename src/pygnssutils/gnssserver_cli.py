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
from pygnssutils.globals import EPILOG
from pygnssutils.gnssserver import GNSSSocketServer


def main():
    """
    CLI Entry point.

    :param int waittime: response wait time in seconds (1)
    :param: as per NSSSocketServer constructor.
    """

    arp = ArgumentParser(
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    arp.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    arp.add_argument("-I", "--inport", required=False, help="Input serial port")
    arp.add_argument("-S", "--socket", required=False, help="Input socket host:port")
    arp.add_argument(
        "-O",
        "--outport",
        required=False,
        help="Output TCP port",
        type=int,
        default=50010,
    )
    arp.add_argument(
        "--ipprot",
        required=False,
        help="IP protocol",
        choices=["IPv4", "IPv6"],
        default="IPv4",
    )
    arp.add_argument(
        "-H",
        "--hostip",
        required=False,
        help="Host IP Address Binding (0.0.0.0/:: = all)",
        default="0.0.0.0",
    )
    arp.add_argument(
        "-N",
        "--ntripmode",
        required=False,
        help="NTRIP Mode 0 = socket server, 1 = NTRIP caster",
        type=int,
        choices=[0, 1],
        default=0,
    )
    arp.add_argument(
        "--ntripuser",
        required=False,
        type=str,
        help="NTRIP caster authentication user",
        default=os.getenv("PYGPSCLIENT_USER", "anon"),
    )
    arp.add_argument(
        "--ntrippassword",
        required=False,
        type=str,
        help="NTRIP caster authentication password",
        default=os.getenv("PYGPSCLIENT_PASSWORD", "password"),
    )
    arp.add_argument(
        "--baudrate",
        required=False,
        help="Serial baud rate",
        type=int,
        choices=[4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800],
        default=9600,
    )
    arp.add_argument(
        "--timeout",
        required=False,
        help="Serial timeout in seconds",
        type=float,
        default=3.0,
    )
    arp.add_argument(
        "--format",
        required=False,
        help="Output format 1 = parsed, 2 = binary, 4 = hex, 8 = tabulated hex,"
        + "16 = parsed as string, 32 = JSON (can be OR'd)",
        type=int,
        default=2,
    )
    arp.add_argument(
        "-v",
        "--validate",
        required=False,
        help="1 = validate checksums, 0 = do not validate",
        type=int,
        choices=[0, 1],
        default=1,
    )
    arp.add_argument(
        "--msgmode",
        required=False,
        help="0 = GET, 1 = SET, 2 = POLL",
        type=int,
        choices=[0, 1, 2],
        default=0,
    )
    arp.add_argument(
        "--maxclients",
        required=False,
        help="Maximum number of clients",
        type=int,
        choices=range(1, 21),
        default=5,
    )
    arp.add_argument(
        "--parsebitfield",
        required=False,
        help="1 = parse UBX 'X' attributes as bitfields, 0 = leave as bytes",
        type=int,
        choices=[0, 1],
        default=1,
    )
    arp.add_argument(
        "--quitonerror",
        required=False,
        help="0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors",
        type=int,
        choices=[0, 1, 2],
        default=1,
    )
    arp.add_argument(
        "--protfilter",
        required=False,
        help="1 = NMEA, 2 = UBX, 4 = RTCM3 (can be OR'd)",
        type=int,
        default=7,
    )
    arp.add_argument(
        "--msgfilter",
        required=False,
        help="Comma-separated string of message identities e.g. 'NAV-PVT,GNGSA'",
        default=None,
    )
    arp.add_argument(
        "--limit",
        required=False,
        help="Maximum number of messages to read (0 = unlimited)",
        type=int,
        default=0,
    )
    arp.add_argument(
        "--verbosity",
        required=False,
        help="Log message verbosity 0 = low, 1 = medium, 2 = high, 3 = debug",
        type=int,
        choices=[0, 1, 2, 3],
        default=1,
    )
    arp.add_argument(
        "--outfile",
        required=False,
        help="Fully qualified path to output file",
        default=None,
    )
    arp.add_argument(
        "--waittime",
        required=False,
        help="Response wait time",
        type=int,
        default=1,
    )
    arp.add_argument(
        "--logtofile",
        required=False,
        help="0 = log to stdout, 1 = log to file '/logpath/gnssserver-timestamp.log'",
        type=int,
        choices=[0, 1],
        default=0,
    )
    arp.add_argument(
        "--logpath",
        required=False,
        help="Fully qualified path to logfile folder",
        default=".",
    )

    args = arp.parse_args()
    kwargs = vars(args)
    if kwargs["hostip"] == "0.0.0.0" and kwargs["ipprot"] == "IPv6":
        kwargs["hostip"] = "::"

    try:
        with GNSSSocketServer(None, **kwargs) as server:
            goodtogo = server.run()

            while goodtogo:  # run until user presses CTRL-C
                sleep(args.waittime)
            sleep(args.waittime)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
