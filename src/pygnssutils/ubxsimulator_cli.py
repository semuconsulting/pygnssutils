"""
ubxsimulator_cli.py

CLI wrapper for UBXSimulator class.

Created on 24 Jul 2024

:author: semuadmin
:copyright: SEMU Consulting © 2024
:license: BSD 3-Clause
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

from pyubx2 import UBXReader

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import (
    CLIAPP,
    EPILOG,
    VERBOSITY_CRITICAL,
    VERBOSITY_DEBUG,
    VERBOSITY_HIGH,
    VERBOSITY_LOW,
    VERBOSITY_MEDIUM,
)
from pygnssutils.ubxsimulator import DEFAULT_PATH, UBXSimulator


def main():
    """
    CLI Entry point.
    """

    ap = ArgumentParser(
        description="pygnssutils EXPERIMENTAL UBX Serial Device Simulator",
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument(
        "-I",
        "--interval",
        required=False,
        type=float,
        help="Simulated navigation interval in seconds (Hz = 1/interval)",
        default=1,
    )
    ap.add_argument(
        "-T",
        "--timeout",
        required=False,
        type=float,
        help="Simulated serial read timeout in seconds",
        default=3,
    )
    ap.add_argument(
        "-C",
        "--configfile",
        required=False,
        type=str,
        help="Fully qualified path to json configuration file",
        default=DEFAULT_PATH + ".json",
    )
    ap.add_argument(
        "--verbosity",
        required=False,
        help=(
            f"Log message verbosity "
            f"{VERBOSITY_CRITICAL} = critical, "
            f"{VERBOSITY_LOW} = low (error), "
            f"{VERBOSITY_MEDIUM} = medium (warning), "
            f"{VERBOSITY_HIGH} = high (info), {VERBOSITY_DEBUG} = debug"
        ),
        type=int,
        choices=[
            VERBOSITY_CRITICAL,
            VERBOSITY_LOW,
            VERBOSITY_MEDIUM,
            VERBOSITY_HIGH,
            VERBOSITY_DEBUG,
        ],
        default=VERBOSITY_MEDIUM,
    )
    ap.add_argument(
        "--logtofile",
        required=False,
        help="fully qualified log file name, or '' for no log file",
        type=str,
        default="",
    )

    kwargs = vars(ap.parse_args())

    with UBXSimulator(CLIAPP, **kwargs) as stream:

        try:
            ubr = UBXReader(stream)
            i = 0
            for _, parsed in ubr:
                print(parsed)
                i += 1
        except KeyboardInterrupt:
            print(f"Terminated by user, {i} messages read")


if __name__ == "__main__":

    main()
