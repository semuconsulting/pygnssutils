"""
gnssdump_cli.py

CLI wrapper for GNSSStreamer class.

Created on 24 Jul 2024

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import CLIAPP, EPILOG
from pygnssutils.gnssstreamer import GNSSStreamer
from pygnssutils.helpers import set_common_args


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
            "Output format 1 = parsed, 2 = binary, 4 = hex, 8 = tabulated hex, "
            "16 = parsed as string, 32 = JSON (can be OR'd)"
        ),
        type=int,
        default=1,
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
        "--outfile",
        required=False,
        help="Fully qualified path to output file",
        default=None,
    )
    ap.add_argument(
        "--outputhandler",
        required=False,
        help="Either writeable output medium or evaluable expression",
    )
    ap.add_argument(
        "--errorhandler",
        required=False,
        help="Either writeable output medium or evaluable expression",
    )
    kwargs = set_common_args(ap)

    try:
        with GNSSStreamer(CLIAPP, **kwargs) as gns:
            gns.run()

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
