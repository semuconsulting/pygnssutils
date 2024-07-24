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
from pygnssutils.globals import CLIAPP, EPILOG
from pygnssutils.ubxsimulator import DEFAULT_PATH, UBXSimulator


def main():
    """
    CLI Entry point.
    """

    arp = ArgumentParser(
        description="pygnssutils EXPERIMENTAL UBX Serial Device Simulator",
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    arp.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    arp.add_argument(
        "-I",
        "--interval",
        required=False,
        type=float,
        help="Simulated navigation interval in seconds (Hz = 1/interval)",
        default=1,
    )
    arp.add_argument(
        "-T",
        "--timeout",
        required=False,
        type=float,
        help="Simulated serial read timeout in seconds",
        default=3,
    )
    arp.add_argument(
        "-C",
        "--configfile",
        required=False,
        type=str,
        help="Fully qualified path to json configuration file",
        default=DEFAULT_PATH + ".json",
    )

    kwargs = vars(arp.parse_args())

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
