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
    prog_callback,
    set_common_args,
)
from pygnssutils.globals import CLIAPP, EPILOG
from pygnssutils.rinex_conv import RinexConverter
from pygnssutils.rinex_globals import (
    MET,
    MINOBS,
    NAV,
    NMEA,
    OBS,
    PYRINEXCONV_VERSION,
    RINEX_NORECS,
    RINEX_OK,
    RINEXTYPE,
    RINEXVER_DEFAULT,
    RTCM3,
    UBLOX,
)
from pygnssutils.rinex_helpers import tuplefy


def main():
    """
    CLI Entry point.
    """

    ap = ArgumentParser(
        epilog=EPILOG,
        description=("NB: %(prog)s is currently an experimental facility."),
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
        help="RINEX Version",
        type=str,
        choices=("3.05", "4.02"),
        default=RINEXVER_DEFAULT,
    )
    ap.add_argument(
        "-T",
        "--rinextype",
        required=False,
        help=(
            f"Comma-separated list of RINEX output type(s), or blank for all: "
            f"{OBS} {RINEXTYPE[OBS]}, {NAV} {RINEXTYPE[NAV]},"
            f" {MET} {RINEXTYPE[MET]} e.g. '{OBS},{NAV}'. "
        ),
        type=str,
        default=f"{OBS},{NAV},{MET}",
    )
    ap.add_argument(
        "-G",
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
        "-O",
        "--obsfilter",
        required=False,
        help="Comma-separated list of observation codes to process, or blank for all e.g. '1C,2S'",
        type=str,
        default="",
    )
    ap.add_argument(
        "-S",
        "--svfilter",
        required=False,
        help="Comma-separated list of satellite codes to process, or blank for all e.g. 'G01,E22'",
        type=str,
        default="",
    )
    ap.add_argument(
        "-os",
        "--obssource",
        required=False,
        help=("Source of observation data"),
        type=str,
        choices=(UBLOX,),
        default=UBLOX,
    )
    ap.add_argument(
        "-ns",
        "--navsource",
        required=False,
        help=("Source of navigation data"),
        type=str,
        choices=(UBLOX, RTCM3),
        default=UBLOX,
    )
    ap.add_argument(
        "-ms",
        "--metsource",
        required=False,
        help=("Source of meteorology data"),
        type=str,
        choices=(NMEA,),
        default=NMEA,
    )
    ap.add_argument(
        "--starttime",
        required=False,
        help=(
            "Approximate start time of RTCM3 data in format "
            "'YYYYMMDDHHMMSS±ZZZZ' e.g. '20260508090123+0100' (defaults "
            "to current UTC datetime)"
        ),
        type=str,
        default="",
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
        "--antennahed",
        required=False,
        help="Comma-separated list of antenna delta height, east, down",
        type=str,
        default="0,0,0",
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
        "--doi",
        required=False,
        help="Digital Object Identifier (RINEX 4 only)",
        type=str,
        default="",
    )
    ap.add_argument(
        "--license",
        required=False,
        help="License of Use (RINEX 4 only)",
        type=str,
        default="",
    )
    ap.add_argument(
        "--station",
        required=False,
        help="Station Information (RINEX 4 only)",
        type=str,
        default="",
    )
    ap.add_argument(
        "--timecorr",
        required=False,
        help="Include time system corrections (STO)",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--ionocorr",
        required=False,
        help="Include ionospheric corrections (ION)",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--eopcorr",
        required=False,
        help="Include earth orientation parameters (EOP) (RINEX 4 only)",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--comments",
        required=False,
        help="Comma-separated list of header user comment(s)",
        type=str,
    )

    kwargs = set_common_args("rinexconvertor", ap)
    infile = kwargs.pop("infile")

    print(f"Processing input file: {infile}")
    rc = RinexConverter(
        CLIAPP,
        rinex_version=kwargs.pop("rinexver", RINEXVER_DEFAULT),
        rinex_types=tuplefy(kwargs.pop("rinextype", f"{OBS},{NAV},{MET}").upper()),
        gnssfilter=tuplefy(kwargs.pop("gnssfilter", "")),
        obsfilter=tuplefy(kwargs.pop("obsfilter", "")),
        svfilter=tuplefy(kwargs.pop("svfilter", "")),
        obssource=kwargs.pop("obssource", UBLOX),
        navsource=kwargs.pop("navsource", UBLOX),
        metsource=kwargs.pop("metsource", NMEA),
        starttime=kwargs.pop("starttime", ""),
        minobs=int(kwargs.pop("minobs", MINOBS)),
        marker=tuplefy(kwargs.pop("marker", "")),
        antenna=tuplefy(kwargs.pop("antenna", "")),
        antennahed=tuplefy(kwargs.pop("antennahed", "0.0,0.0,0.0")),
        receiver=tuplefy(kwargs.pop("receiver", "")),
        observer=kwargs.pop("observer", ""),
        comments=tuplefy(kwargs.pop("comments", "")),
        doi=kwargs.pop("doi", ""),
        license=kwargs.pop("license", ""),
        station=kwargs.pop("station", ""),
        timecorr=bool(kwargs.pop("timecorr", 1)),
        ionocorr=bool(kwargs.pop("ionocorr", 1)),
        eopcorr=bool(kwargs.pop("eopcorr", 1)),
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
