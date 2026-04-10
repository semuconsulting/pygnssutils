"""
rinex_conv_cli.py

CLI wrapper for RinexConvertor class.

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

from pygnssutils import (
    NMEA_PROTOCOL,
    RTCM3_PROTOCOL,
    UBX_PROTOCOL,
    prog_callback,
    set_common_args,
)
from pygnssutils.globals import CLIAPP, EPILOG
from pygnssutils.rinex_conv import RinexConverter
from pygnssutils.rinex_globals import (
    ALLGNSS,
    ALLOBS,
    MET,
    MINOBS,
    NAV,
    OBS,
    PYRINEXCONV_VERSION,
    RINEX_NORECS,
    RINEX_OK,
    RINEXTYPE,
    RINEXVER_DEFAULT,
)
from pygnssutils.rinex_helpers import listify


def main():
    """
    CLI Entry point.
    """

    ap = ArgumentParser(
        epilog=EPILOG,
        description=(
            "NB: %(prog)s is currently an experimental facility with "
            "limited functionality. NOT FOR PRODUCTION USE."
        ),
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument(
        "-V", "--version", action="version", version="%(prog)s " + PYRINEXCONV_VERSION
    )
    ap.add_argument(
        "-I",
        "--infile",
        required=True,
        help="Fully-qualified path to binary GNSS log file",
        type=str,
    )
    ap.add_argument(
        "-R",
        "--rinexver",
        required=False,
        help="RINEX Version e.g. '3.05'",
        type=str,
        default=RINEXVER_DEFAULT,
    )
    ap.add_argument(
        "-T",
        "--rinextype",
        required=False,
        help=(
            f"Comma-separated list of RINEX output type(s), or blank for all: "
            f"{OBS} {RINEXTYPE[OBS]}, {NAV} {RINEXTYPE[NAV]},"
            f" {MET} {RINEXTYPE[MET]} e.g. '{OBS},{MET}'. "
        ),
        type=str,
        default="",
    )
    ap.add_argument(
        "--gnssfilter",
        required=False,
        help=(
            "Comma-separated list of GNSS to process, or blank for all: "
            "G GPS, R GLONASS, E GALILEO, C BEIDOU, S SBAS, J QZSS, I NAVIC e.g. 'G,E'"
        ),
        type=str,
        default="",
    )
    ap.add_argument(
        "--obsfilter",
        required=False,
        help="Comma-separated list of observation codes to process, or blank for all e.g '1C,2B'",
        type=str,
        default="",
    )
    ap.add_argument(
        "--datasource",
        required=False,
        help=(
            "Comma-separated list of data sources for each of (OBS, NAV, MET): "
            "R Receiver, S Stream, N NTRIP, U Unknown e.g 'R,S,R'"
        ),
        type=str,
        default="R,R,R",
    )
    ap.add_argument(
        "--minobs",
        required=False,
        help="Minimum number of observations required per observation type",
        type=str,
        default=MINOBS,
    )
    ap.add_argument(
        "--marker",
        required=False,
        help="Comma-separated list of marker name, number, type",
        type=str,
        default="",
    )
    ap.add_argument(
        "--antenna",
        required=False,
        help="Comma-separated list of antenna number, type",
        type=str,
        default="",
    )
    ap.add_argument(
        "--receiver",
        required=False,
        help="Comma-separated list of receiver number, type, version",
        type=str,
        default="",
    )
    ap.add_argument(
        "--observer",
        required=False,
        help="Observer / Agency name",
        type=str,
        default="",
    )
    ap.add_argument(
        "--comments",
        required=False,
        help="Comma-separated list of header user comment(s)",
        type=str,
    )
    ap.add_argument(
        "--protfilter",
        required=False,
        help=(
            f"Input protocol mask - NMEA={NMEA_PROTOCOL}, UBX={UBX_PROTOCOL}, "
            f"RTCM3={RTCM3_PROTOCOL}. Can be OR'd"
        ),
        type=int,
        default=NMEA_PROTOCOL | UBX_PROTOCOL | RTCM3_PROTOCOL,
    )

    kwargs = set_common_args("rinexconvertor", ap)
    infile = kwargs.pop("infile")

    print(f"Processing input file: {infile}")
    rc = RinexConverter(
        CLIAPP,
        rinex_version=kwargs.pop("rinexver", RINEXVER_DEFAULT),
        rinex_types=listify(kwargs.pop("rinextype", ALLOBS)),
        gnssfilter=listify(kwargs.pop("gnssfilter", ALLGNSS)),
        obsfilter=listify(kwargs.pop("obsfilter", [""])),
        datasource=listify(kwargs.pop("datasource", ["R", "R", "R"])),
        minobs=int(kwargs.pop("minobs", MINOBS)),
        marker=listify(kwargs.pop("marker", [""])),
        antenna=listify(kwargs.pop("antenna", [""])),
        receiver=listify(kwargs.pop("receiver", [""])),
        observer=kwargs.pop("observer", ""),
        comments=listify(kwargs.pop("comments", [""])),
        protfilter=int(
            kwargs.pop("protfilter", NMEA_PROTOCOL | UBX_PROTOCOL | RTCM3_PROTOCOL)
        ),
        **kwargs,
    )
    res = rc.process_input(
        infile=infile, stopevent=None, progcallback=prog_callback, **kwargs
    )
    if res == RINEX_OK:
        print(
            "Processing successful. Output file names and number of records processed:"
        )
        for rt, (filename, count) in rc.outputs.items():
            print(f"{RINEXTYPE[rt].capitalize()}: {filename} - {count:,}")
    elif res == RINEX_NORECS:
        print("No parsable records found in input file")
    else:
        print(f"Processing failed - {res} (see verbose log for details)")


if __name__ == "__main__":
    main()
