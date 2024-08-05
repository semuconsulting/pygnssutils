"""
ubxsimulator_cli.py

CLI wrapper for UBXSimulator class.

Created on 24 Jul 2024

:author: semuadmin
:copyright: SEMU Consulting © 2024
:license: BSD 3-Clause
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from logging import getLogger

from pyubx2 import UBXReader

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import CLIAPP, EPILOG
from pygnssutils.helpers import set_common_args
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
        help="Simulated navigation interval in milliseconds (Hz = 1000/interval)",
        default=1000,
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
    kwargs = set_common_args(ap)

    logger = getLogger("pygnssutils.ubxsimulator")

    with UBXSimulator(CLIAPP, **kwargs) as stream:

        try:
            ubr = UBXReader(stream)
            i = 0
            for _, parsed in ubr:
                logger.debug(str(parsed))
                i += 1
        except KeyboardInterrupt:
            logger.info(f"Terminated by user, {i} messages processed")


if __name__ == "__main__":

    main()
