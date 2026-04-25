"""
rinex_helpers.py

RINEX conversion static helper methods.

Mainly header string formatting.

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

# pylint: disable=invalid-name

from datetime import datetime, timezone
from getpass import getuser
from pathlib import Path
from types import NoneType
from typing import Literal

from pynmeagps import leapsecond

from pygnssutils.rinex_globals import (
    BDS,
    DATAWIDTH,
    EPOCH0_BEIDOU,
    EPOCH0_GPS,
    EPOCHMAX,
    EPOCHMIN,
    GLO,
    MIX,
    PYRINEXCONV_VERSION,
    QZS,
    RINEXGNSSR,
    RINEXTYPE,
    SBA,
    TIME_BEIDOU,
    TIME_GPS,
    TIME_UNDEFINED,
    UBXRINEXGNSS,
    UBXRINEXOBSCODE,
)

TIMEUNITS = ((1, "S"), (60, "M"), (60, "H"), (24, "D"), (365, "Y"))


def FRNX(num: float | int | str, length: int, dp: int) -> str:
    """
    Format float to RINEX FORTAN-style string.

    :param float | int | str num: number
    :param int length: length
    :param int dp: decimal places
    :return: formatted string
    :rtype: str
    """

    if isinstance(num, (float, int)):
        num = f"{num:.{dp}f}"
    return f"{num:>{length}}"


def DRNX(num: float | int | str, length: int, sig: int) -> str:
    """
    Format float to RINEX SCIENTIFIC-style string.

    :param float | int | str num: number
    :param int length: length
    :param int sig: significant digits
    :return: formatted string
    :rtype: str
    """

    if isinstance(num, (float, int)):
        num = f"{num:.{sig}e}"
    return f"{num:>{length}}"


def adjust_time_units(value: float) -> tuple[int, str]:
    """
    Adjust time units to keep to 2 integers, as required
    in RINEX filename period and frequency fields.

    :param float value: time value in seconds
    :return: adjusted value and time units
    :rtype: tuple[int, str]
    """

    try:
        i = 0
        val = value * TIMEUNITS[i][0]
        unit = TIMEUNITS[i][1]
        while val > 100:
            i += 1
            val /= TIMEUNITS[i][0]
            unit = TIMEUNITS[i][1]
        return int(round(val, 0)), unit
    except (ValueError, TypeError, IndexError):
        return 0, "U"  # undefined


def get_svcode_ubx(gnss: int, prn: int) -> str:
    """
    Convert GNSS and prn values to RINEX svid string e.g "G29", "E 4"

    :param int gnss: GNSS code
    :param int prn: prn code
    :return: svid as string
    :rtype: str
    """

    gnssr = UBXRINEXGNSS[gnss]
    if gnssr == SBA:  # SBAS
        prn -= 100
    elif gnssr == QZS:  # QZSS
        prn -= 192

    return f"{gnssr}{prn:02d}"


def get_svcode_rtcm(gnssr: str, prn: int, freqno: int | NoneType = None) -> str:
    """
    Convert GNSS and prn values to RINEX svid string e.g "G29", "E 4"

    :param str gnss: GNSS code
    :param int prn: prn code
    :param int | NoneType freqno: GLONASS frequency no
    :return: svid as string
    :rtype: str
    """

    if gnssr == SBA:  # SBAS
        prn -= 100
    elif gnssr == QZS:  # QZSS
        prn -= 192

    return f"{gnssr}{prn:02d}"


def get_obscode(gnss: int, sigid: int) -> str:
    """
    Convert GNSS and Signal ID to RINEX observation code e.g. "1C", "2B"
    """

    return UBXRINEXOBSCODE[(gnss, sigid)]


def get_ssi(cno: float) -> int:
    """
    Convert CNO in dbHz to RINEX signal strength indicator (SSI) value

    :param float cno: CNO in dbHz
    :return: SSI as integer
    :rtype: int
    """

    return min(max(int(cno / 6), 1), 9)


def format_filename(
    rinextype: Literal["O", "N", "M"],
    gnssfilter: list[str],
    startepoch: datetime,
    endepoch: datetime,
    interval: int | float,
    outputpath: Path = Path("."),
    source: Literal["R", "S", "N", "U"] = "R",
) -> Path:
    """
    Format output file name using RINEX long filename format.

    e.g. pygpsdata_R_202604101416_30M_01S_MO.rnx

    :param Literal["O","N","M"] rinextype: RINEX type
    :param list[str] gnssfilter: list of GNSS systems included (G, E, etc.)
    :param datetime startepoch: first observation epoch
    :param datetime endepoch: last observation epoch
    :param int | float interval: observation interval in seconds
    :param Path | str outputpath: fully-qualified file path (".")
    :param Literal["R","S","N","U"] source: source of observations (R = Receiver)
    :return: fully-qualified output file path
    :rtype: Path
    """

    if startepoch == EPOCHMAX or endepoch == EPOCHMIN:
        period = TIME_UNDEFINED
    else:
        per, peru = adjust_time_units((endepoch - startepoch).total_seconds())
        period = f"{per:02d}{peru}"

    if interval == 0:
        frequency = TIME_UNDEFINED
    else:
        freq, frequ = adjust_time_units(interval)
        frequency = f"{freq:02d}{frequ}"

    gnssr = gnssfilter[0] if (len(gnssfilter) == 1 and gnssfilter[0] != "") else "M"
    start = startepoch.strftime("%Y%m%d%H%M")
    gnu = gnssr.upper()
    rtu = rinextype.upper()
    src = "S" if source == "N" else source  # treat NTRIP as Stream
    return Path.joinpath(
        outputpath, f"pygpsdata_{src}_{start}_{period}_{frequency}_{gnu}{rtu}.rnx"
    )


def format_comments(comments: list | str = "") -> str:
    """
    Format comments.

    :param list | str comments: comments
    :return: formatted string
    :rtype: str
    """

    if comments == "":
        comments = []
    elif isinstance(comments, str):
        comments = [comments]

    out = ""
    for comment in list(comments):
        while len(comment) > 0:
            comm = comment[0:DATAWIDTH]
            out += f"{comm:<{DATAWIDTH}}COMMENT\n"  # A60
            comment = comment[DATAWIDTH:]
    return out


def format_version(
    rinexver: str, rinextype: Literal["O", "N", "M"], gnssr: list[str] | str
) -> str:
    """
    Format RINEX version.

    :param str rinexver: RINEX version e.g. "3.05"
    :param Literal["O","N","M"] rinextype: RINEX filetype
    :param list[str] | str gnssr: RINEX GNSS code(s)
    :return: formatted string
    :rtype: str
    """

    # F9.2, 11X A1,19X A1,19X
    filedesc = RINEXTYPE[rinextype].upper()
    filetype = f"{rinextype}: {filedesc}"
    gnsstypes = [gnssr] if isinstance(gnssr, str) else gnssr
    gnsstypes = MIX if (len(gnsstypes) > 1 or gnssr in ([""], ["M"])) else gnsstypes[0]
    gnssdesc = RINEXGNSSR[gnsstypes].upper()
    gnsstype = f"{gnsstypes}: {gnssdesc}"
    return (
        f"{str(rinexver):>9}{'':>11}{filetype:<20}{gnsstype:<20}RINEX VERSION / TYPE\n"
    )


def format_runby(
    pgm: str = f"pyrinexconv {PYRINEXCONV_VERSION}",
    runby: str = getuser(),
    rundate: datetime | str = "",
) -> str:
    """
    Format Name of program/agency creating current file and run time.

    :param str version: programme version
    :param str runby: runtime user
    :param datetime | str rundate: run date & timezone (now if blank)
    :return: formatted string
    :rtype: str
    """

    if rundate == "":
        rundate = datetime.now(timezone.utc)
    runds = rundate.strftime("%Y%m%d %H%M%S %Z")
    pgms = pgm[0:20].upper()
    runbys = runby[0:20].upper()

    # A20, A20, A20
    return f"{pgms:<20}{runbys:<20}{runds:<20}PGM / RUN BY / DATE\n"


def format_marker(mkrname: str = "", mkrnum: str = "", mkrtype: str = "") -> str:
    """
    Format antenna marker name, number (optional) and type.

    :param str name: marker name
    :param str name: marker number
    :param str name: marker type
    :return: formatted string
    :rtype: str
    """

    out = f"{str(mkrname):<{DATAWIDTH}}MARKER NAME\n"  # A60
    if mkrnum != "":
        out += f"{str(mkrnum):<{DATAWIDTH}}MARKER NUMBER\n"  # A20
    out += f"{str(mkrtype):<{DATAWIDTH}}MARKER TYPE\n"  # A20,40X
    return out


def format_observer(observer: str = "") -> str:
    """
    Format Name of observer / agency.

    :param str observer: observer / agency
    :return: formatted string
    :rtype: str
    """

    return f"{observer:<{DATAWIDTH}}OBSERVER / AGENCY\n"  # A20,A40


def format_rcvrtype(rcvrnum: str = "", rcvrtype: str = "", rcvrver: str = "") -> str:
    """
    Format Receiver number, type, and version.

    :param str rcvrnum: record number
    :param str rcvrtype: record type
    :param str rcvrver: record version
    :return: formatted string
    :rtype: str
    """

    return f"{rcvrnum:<20}{rcvrtype:<20}{rcvrver:<20}REC # / TYPE / VERS\n"  # 3A20


def format_antennatype(antnum: str = "", anttype: str = "") -> str:
    """
    Format antenna type.

    :param str antenna: antenna number
    :param str antenna: antenna type
    :return: formatted string
    :rtype: str
    """

    return f"{antnum:<20}{anttype:<20}{'':<20}ANT # / TYPE\n"  # 2A20


def format_approxpos(approxpos: list[float] | str = "") -> str:
    """
    Format approx ECEF marker position (prefer ITRS) (optional for moving platforms).

    :param list[float] | str approxpos: approx ECEF pos [X,Y,Z]
    :return: formatted string
    :rtype: str
    """

    if approxpos != "":
        x, y, z = approxpos
        return (
            f"{FRNX(x,14,4)}{FRNX(y,14,4)}"
            f"{FRNX(z,14,4)}{'':<18}APPROX POSITION XYZ\n"
        )  # 3F14.4
    return ""


def format_antennadeltahen(
    height: float | str = "", eccen: list[float] | str = ""
) -> str:
    """
    Format Antenna height: Height and Horizontal eccentricity of the antenna reference point
    (ARP) relative to the marker.

    :param float | str height: height relative to marker (m)
    :param list[float] | str eccen: eccentricity (E,N) (m)
    :return: formatted string
    :rtype: str
    """

    if height == "":
        height = 0.0
    if eccen == "":
        eccen = [0.0, 0.0]
    e, n = eccen
    # F14.4, 2F14.4
    return (
        f"{FRNX(height,14,4)}{FRNX(e,14,4)}{FRNX(n,14,4)}{'':<18}ANTENNA: DELTA H/E/N\n"
    )


def format_antennadeltaxyz(deltaxyz: list[float] | str = "") -> str:
    """
    Format Position of antenna reference point for antenna on vehicle (optional).

    :param list[float] | str deltaxyz: approx pos [X,Y,Z]
    :return: formatted string
    :rtype: str
    """

    if deltaxyz != "":
        x, y, z = deltaxyz
        return (
            f"{FRNX(x,14,4)}{FRNX(y,14,4)}"
            f"{FRNX(z,14,4)}{'':<18}ANTENNA: DELTA X/Y/Z\n"
        )  # 3F14.4
    return ""


def format_sys_antennaphasecentre(
    antphasecentres: dict | str = "",
) -> str:
    """
    Format Average phase center position with respect to antenna reference point (optional)

    Format of antphasecentres dict::

        antphasecentres = {
            gnssr (str) : {
                "obstype": obstype (str),
                "phasecenter": [x (float, y (float), z (float)],
            },
            gnssr (str) : {
                "obstype": obstype (str),
                "phasecenter": [x (float, y (float), z (float)],
            },
        }

    :param dict | str antphasecentres: antenna phase centres
    :return: formatted string
    :rtype: str
    """

    if antphasecentres == "":
        antphasecentres = {}

    out = ""
    for gnssr, antps in antphasecentres.items():
        obstype = antps["obstype"]
        x, y, z = antps["phasecenter"]
        # A1 1X,A3 F9.4 2F14.4
        out += (
            f"{gnssr}{obstype:>4}{FRNX(x,9,4)}{FRNX(y,14,4)}"
            f"{FRNX(z,14,4)}{'':<18}ANTENNA: PHASECENTER\n"
        )
    return out


def format_antennabsight(bsight: list[float] | str = "") -> str:
    """
    Format Direction of the “vertical” antenna axis towards the GNSS
    satellites (optional).

    :param list[float] | str  bsight : direction of antenna axis (X,Y,Z)
    :return: formatted string
    :rtype: str
    """

    if bsight != "":
        x, y, z = bsight
        return (
            f"{FRNX(x,14,4)}{FRNX(y,14,4)}{FRNX(z,14,4)}"
            f"{'':<18}ANTENNA: B.SIGHT XYZ\n"
        )  # 3F14.4
    return ""


def format_antennazerodirazi(azi: float | str = "") -> str:
    """
    Format Azimuth of the zero-direction of a fixed antenna (optional).

    :param float | str  azi: azimuth
    :return: formatted string
    :rtype: str
    """

    if azi != "":
        return f"{FRNX(azi,14,4)}{'':<46}ANTENNA: ZERODIR AZI\n"  # F14.4
    return ""


def format_antennazerodirxyz(zerodir: list[float] | str = "") -> str:
    """
    Format Zero-direction of antenna Antenna on vehicle (optional).

    :param list[float] | str  zerodir: zero-direction of antenna (X,Y,Z)
    :return: formatted string
    :rtype: str
    """

    if zerodir != "":
        x, y, z = zerodir
        return (
            f"{FRNX(x,14,4)}{FRNX(y,14,4)}"
            f"{FRNX(z,14,4)}{'':<18}ANTENNA: ZERODIR XYZ\n"
        )  # 3F14.4
    return ""


def format_centermass(centermass: list[float] | str = "") -> str:
    """
    Format Current center of mass (X,Y,Z, meters) of vehicle in body-fixed
    coordinate system (optional).

    :param list[float] | str centermass: centermass [x,y,z]
    :return: formatted string
    :rtype: str
    """

    if centermass != "":
        x, y, z = centermass
        return (
            f"{FRNX(x,14,4)}{FRNX(y,14,4)}"
            f"{FRNX(z,14,4)}{'':<18}CENTER OF MASS: XYZ\n"
        )  # 3F14.4
    return ""


def format_obstypes(obstypes: dict | str = "") -> str:
    """
    Format observation type(s).

    Format of obstypes dict::

        obstypes = {
            gnssr (str) : {
                BDS+obstype: num (int),
                "L"+obstype: num (int),
                "D"+obstype: num (int),
                "S"+obstype: num (int),
            },
            gnssr (str) : {
                BDS+obstype: num (int),
                "L"+obstype: num (int),
                "D"+obstype: num (int),
                "S"+obstype: num (int),
            },
        }

    :param dict | str obstypes: observation types
    :return: formatted string
    :rtype: str
    """

    if obstypes == "":
        obstypes = {}

    out = ""
    for gnssr, obstype in obstypes.items():
        numobst = len(obstype)
        obst = f"{gnssr}{str(numobst):>5}"
        for i, obstype in enumerate(obstype):
            obst += f"{obstype:>4}"
            if len(obst) > 56 or i == numobst - 1:
                out += f"{obst:<{DATAWIDTH}}SYS / # / OBS TYPES\n"
                obst = f"{'':>6}"
    return out


def format_cnrunit(unit: str = "dbHz") -> str:
    """
    Format Unit of the carrier to noise ratio observables (optional).

    :param str unit: CNo unit
    :return: formatted string
    :rtype: str
    """

    return f"{unit.upper():<20}{'':<40}SIGNAL STRENGTH UNIT\n"  # A20,40X


def format_interval(interval: float | str = "") -> str:
    """
    Format Observation interval in seconds (optional).

    :param float | str interval: interval in seconds
    :return: formatted string
    :rtype: str
    """

    if interval != "":
        return f"{FRNX(interval, 10, 3)}{'':<50}INTERVAL\n"  # F10.3
    return ""


def format_obstime(utc: datetime, source: str = "GPS") -> str:
    """
    Format observation time and source.

    :param datetime utc: utc time
    :param str source: time source e.g. "GPS"
    :return: formatted time string
    :rtype: str
    """

    return (
        f"{str(utc.year):>6}{str(utc.month):>6}{str(utc.day):>6}"
        f"{str(utc.hour):>6}{str(utc.minute):>6}"
        f"{FRNX(utc.second+utc.microsecond/1000000,13,7)}"
        f"{'':>5}{source:>3}"
    )  # 5I6,F13.7 5X,A3


def format_timefirstlast(tim: datetime, mode: Literal["FIRST", "LAST"]) -> str:
    """
    Format header observation first and last time markers (optional).

    :param datetime tim: time
    :param Literal["FIRST", "LAST"]
    :return: formatted string
    :rtype: str
    """

    return f"{format_obstime(tim):<{DATAWIDTH}}TIME OF {mode} OBS\n"


def format_clockoffset(offset: int | str = "") -> str:
    """
    Format Epoch, code, and phase are corrected by applying the
    real-time-derived receiver clock offset (optional).

    :param int | str: offset flag
    :return: formatted string
    :rtype: str
    """

    if offset not in (0, ""):
        return f"{offset:<6}{'':<54}RCV CLOCK OFFS APPL\n"  # I6
    return ""


def format_sys_dcbsapplied(dcbsapplied: dict | str = "") -> str:
    """
    Format Program name used to apply differential code bias corrections
    (optional).

    Format of dcbsapplied dict::

        dcbsapplied = {
            gnssr (str) ) {
                "pgmname": pgmname (str),
                "source": source (str),
            },
            gnssr (str) ) {
                "pgmname": pgmname (str),
                "source": source (str),
            },
        }

    :param dict | str dcbsapplied: dcbs applied
    :return: formatted string
    :rtype: str
    """

    if dcbsapplied == "":
        dcbsapplied = {}

    out = ""
    for gnssr, dcbs in dcbsapplied.items():
        pgmname = dcbs["pgmname"]
        source = dcbs["source"]
        out += f"{gnssr} {pgmname:<17} {source:<40}SYS / DCBS APPLIED\n"  # A1 1X,A17 1X,A40
    return out


def format_sys_pcvsapplied(pcvsapplied: dict | str = "") -> str:
    """
    Format Program name used to apply phase center variation corrections
    (optional).
    Requires pcvs applied to be previously stored as a dict with structure::

    Format of pcvsapplied dict::

        pcvsapplied = {
            gnssr (str) ) {
                "pgmname": pgmname (str),
                "source": source (str),
            },
            ...
        }

    :param dict | str pcvsapplied: pcvs applied
    :return: formatted string
    :rtype: str
    """

    if pcvsapplied == "":
        pcvsapplied = {}

    out = ""
    for gnssr, dcbs in pcvsapplied.items():
        pgmname = dcbs["pgmname"]
        source = dcbs["source"]
        out += f"{gnssr} {pgmname:<17} {source:<40}SYS / PVCS APPLIED\n"  # A1 1X,A17 1X,A40
    return out


def format_sys_scalefactor(
    scalefactors: dict | str = "",
) -> str:
    """
    Format Factor to divide stored observations with before (optional).

    Format of scalefactors dict::

        scale_factors = {
            gnssr (str) : {
                "scale": scale (float),
                "obstypes": [obstype (str), obstype (str), ...] # ["C01", "C02", etc.]
            },
            ...
        }

    :param dict | str scalefactors: gnssr scale factors
    :return: formatted string
    :rtype: str
    """

    if scalefactors == "":
        scalefactors = {}

    out = ""
    for gnssr, factors in scalefactors.items():
        # A1 1X,I4 2X,I2 12(1X,A3) 10X 12(1X,A3)
        scale = factors["scale"]
        obstypes = factors["obstypes"]
        numobst = len(obstypes)
        sf = f"{gnssr} {scale:<4}  {numobst:<2}"
        for i, obstype in enumerate(obstypes):
            sf += f"{obstype:>4}"
            if len(sf) > 56 or i == numobst - 1:
                out += f"{sf:<{DATAWIDTH}}SYS / SCALE FACTOR\n"
                sf = f"{'':<10}"
    return out


def format_sys_phaseshift(phaseshifts: dict | str = "") -> str:
    """
    Format Phase shift correction used to generate phases consistent
    with respect to cycle shifts.

    Format of phaseshifts dict::

        phaseshifts = {
            gnssr (str) : {
                "obscode": obscode (str),
                "correction": correction (float)
                "sats": [svcode (str), svcode (str), svcode (str), ...] # ["E03", "E04", etc.]
            },
            ...
        }

    :param dict | str phaseshifts: phase shifts
    :return: formatted string
    :rtype: str
    """

    if phaseshifts == "":
        phaseshifts = {}

    out = ""
    for gnssr, shifts in phaseshifts.items():
        # A1,1X A3,1X F8.5 2X,I2.2 10(1X,A3) 18X 10(1X,A3)
        freq = shifts["freq"]
        correction = shifts["correction"]
        sats = shifts["sats"]
        numsats = len(sats)
        if numsats == 0:
            ps = f"{gnssr} {freq:<3} {FRNX(correction,8,5)}"
            out += f"{ps:<{DATAWIDTH}}SYS / PHASE SHIFT\n"
        else:
            ps = f"{gnssr} {freq:<3} {FRNX(correction,8,5)}  {numsats:<2}"
            for i, sat in enumerate(sats):
                ps += f"{sat:>4}"
                if len(ps) > 56 or i == numsats - 1:
                    out += f"{ps:<{DATAWIDTH}}SYS / PHASE SHIFT\n"
                    ps = f"{'':<18}"
    return out


def format_glonassfrq(sats: dict | str = "") -> str:
    """
    Format GLONASS slot and frequency numbers (mandatory).

    Format of sats dict::

        sats = {
            svcode (str): freq (int),
            svcode (str): freq (int),
        }

    :param dict | str sats: dict of {svcode: frq}
    :return: formatted string
    :rtype: str
    """

    if sats == "":
        sats = {}

    numsats = len(sats)
    if numsats == 0:
        return f"{'':<{DATAWIDTH}}GLONASS SLOT / FRQ\n"

    # I3,1X 8(A1,I2.2, 1X,I2,1X)
    out = ""
    ps = f"{numsats:>3} "
    for i, (svcode, freq) in enumerate(sorted(sats.items())):
        ps += f"{svcode:>3} {freq:>2} "  # A1,I2.2, 1X,I2,1X
        if len(ps) > 54 or i == numsats - 1:
            out += f"{ps:<{DATAWIDTH}}GLONASS SLOT / FRQ\n"
            ps = f"{'':<4}"
    return out


def format_glonassphasebias(corrs: dict | str = "") -> str:
    """
    Format GLONASS Phase bias correction used to align code and phase observations
    (mandatory).

    Format of corrs dict::

        corrs = {
            code (str) : bias (float),
            code (str) : bias (float),
        }

    :param dict | NoneType corrs: dict of {code: phase bias correction}
    :return: formatted string
    :rtype: str
    """

    if corrs == "":
        corrs = {}

    # 4(X1,A3,X1,F8.3)
    pb = ""
    for code, bias in corrs.items():
        pb += f" {code:<3} {FRNX(bias,8,3)}"
    return f"{pb:<60}GLONASS COD/PHS/BIS\n"


def format_leapseconds(
    epoch: datetime | str = "",
    gnssfilter: list[str] | str = "",
) -> str:
    """
    Format Current Number of leap seconds (optional).

    TODO check intention here - not clear from specs which date
    this refers to; have assumed first observation date

    :param datetime | str epoch: epoch to which leapsecond refers
    :param list[str] | str gnssfilter: list of gnss included
    :return: formatted string
    :rtype: str
    """

    if epoch == "" or gnssfilter in (GLO, [GLO]):  # omit if only GLONASS
        return ""

    timesource, e0 = (
        (TIME_BEIDOU, EPOCH0_BEIDOU)
        if gnssfilter in (BDS, [BDS])
        else (TIME_GPS, EPOCH0_GPS)
    )
    wno = int((epoch - e0).total_seconds() / 604800)
    ls = leapsecond(epoch, "C" if timesource == TIME_BEIDOU else "G")
    dno = epoch.weekday()  # GPS Monday = 1, BDS Monday = 0
    dno = (dno + 1) % 7 if timesource == TIME_GPS else dno

    if epoch > datetime.now(timezone.utc):
        leapsecs = ""
        futureleapsecs = ls
    else:
        leapsecs = ls
        futureleapsecs = ""

    return (
        f"{leapsecs:>6}{futureleapsecs:>6}{wno:>6}"
        f"{dno:>6}{timesource:>3}{'':<33}LEAPSECONDS\n"
    )  # I6 I6 I6 I6 A3


def format_numsats(numsats: int | str = "") -> str:
    """
    Format Number of satellites, for which observations are stored in the file (optional).

    :param int | str numsats: number of satellites
    :return: formatted string
    :rtype: str
    """

    if numsats != "":
        return f"{numsats:>6}{'':<54}# OF SATELLITES\n"
    return ""


def format_iono_corr(ionocorr: dict | str = "") -> str:
    """
    Format Ionospheric Corrections.

    Format of ionocorr dict::

        ionocorr = {
            corrtype (str) : {
                "parm1" : parm1 (float),
                "parm2" : parm2 (float),
                "parm3" : parm3 (float),
                "parm4" : parm4 (float),
                "timemark" : timemark (str),
                "svid" : svid (str),
            },
        }

    :param dict | str ionocorr: ionospheric correction dictionary
    :return: formatted string
    :rtype: str
    """

    if ionocorr == "":
        ionocorr = {}

    out = ""
    for corrtype, values in ionocorr.items():
        parm1 = values["parm1"]
        parm2 = values["parm2"]
        parm3 = values["parm3"]
        parm4 = values["parm4"]
        timemark = values["timemark"]
        svid = values["svid"]
        # A4,1X 4D12.4 1X,A1 1X,I2
        out += (
            f"{corrtype:<4} {DRNX(parm1,12,4)}{DRNX(parm2,12,4)}{DRNX(parm3,12,4)}"
            f"{DRNX(parm4,12,4)} {timemark} {svid:02d}  IONOSPHERIC CORR\n"
        )
    return out


def format_time_corr(timecorr: dict | str = "") -> str:
    """
    Format Time System Corrections.

    Format of timecorr dict::

        timecorr = {
            corrtype (str) : {
                "a0" : a0 (float),
                "a1" : a1 (float),
                "timeref" : timeref (int),
                "weekno" : weekno (int),
                "svcode" : svcode (str),
                "source" : source (str),
            },
        }

    :param dict | str timecorr: time corrections dictionary
    :return: formatted string
    :rtype: str
    """

    if timecorr == "":
        timecorr = {}

    out = ""
    for corrtype, values in timecorr.items():
        a0 = values["a0"]
        a1 = values["a1"]
        timeref = values["timeref"]
        weekno = values["weekno"]
        svcode = values["svcode"]
        source = values["source"]
        # A4,1X D17.10 D16.9 1XI6 1XI4 1X,A5,1X I2,1X
        out += (
            f"{corrtype:<4} {DRNX(a0,17, 10)}{DRNX(a1,16, 9)} "
            f"{timeref:<6} {weekno:<4} {svcode:>5} {source:>2} TIME SYSTEM CORR\n"
        )
    return out


def format_nav_epoch(epoch: datetime) -> str:
    """
    Format nav epoch as string.

    :param datetime epoch: epoch
    """

    return (
        f"{epoch.year:04d} {epoch.month:02d} {epoch.day:02d} "
        f"{epoch.hour:02d} {epoch.minute:02d} {epoch.second:02d}"
    )


def format_met_obstypes(sensortypes: dict[str, dict] | str) -> str:
    """
    Format Number of different meteorological observation types.

    :param dict[str,dict] | str sensortypes: sensor types
    :return: formatted string
    :rtype: str
    """

    if sensortypes == "":
        sensortypes = {}

    # I6, 9(4X,A2) (6X,9(4X,A2))
    out = ""
    numobs = len(sensortypes)
    ps = f"{numobs:>6}"
    for i, obstype in enumerate(sensortypes):
        ot = obstype
        ps += f"    {ot:<2}"
        if len(ps) > 56 or i == numobs - 1:
            out += f"{ps:<{DATAWIDTH}}# / TYPES OF OBSERV\n"
            ps = f"{'':<6}"
    return out


def format_met_sensortype(sensortypes: dict[str, dict] | str) -> str:
    """
    Format Description of the met sensor.

    :param dict[str,dict] | str sensortypes: sensor types
    :return: formatted string
    :rtype: str
    """

    if sensortypes == "":
        sensortypes = {}

    # A20, A20,6X, F7.1,4X, A2,1X
    out = ""
    for obstype, values in sensortypes.items():
        sensmod = values["sensmod"]
        senstyp = values["senstyp"]
        accuracy = values["accuracy"]
        out += (
            f"{sensmod:<20}{senstyp:<20}      {FRNX(accuracy,7,1)}"
            f"    {obstype:<2} SENSOR MOD/TYPE/ACC\n"
        )
    return out


def format_met_sensorpos(senspos: list[float] | str, obstype: str = "PR") -> str:
    """
    Format Approximate position of the met sensor.

    :param list[float] | str sensortypes: sensor types
    :return: formatted string
    :rtype: str
    """

    # 3F14.4, 1F14.4, 1X,A2,1X
    if senspos == "":
        senspos = [0, 0, 0, 0]

    x, y, z, h = senspos
    return (
        f"{FRNX(x,14,4)}{FRNX(y,14,4)}{FRNX(z,14,4)}"
        f"{FRNX(h,14,4)} {obstype:<2} SENSOR POS XYZ/H\n"
    )


def format_headerend() -> str:
    """
    Format header end.

    :return: formatted string
    :rtype: str
    """

    return f"{'':<{DATAWIDTH}}END OF HEADER\n"


def format_fileend():
    """
    Format file end.
    """

    return format_comments("END OF FILE")


def listify(arg: list[str] | str | NoneType) -> list[str]:
    """
    Convert comma-separated CLI argument str to list type.

    :parm list[str] | str | NoneType arg: argument
    :return: argument as list
    :rtype: list[str]
    """

    if arg is None:
        return [""]
    if isinstance(arg, (list, tuple)):
        return list(arg)
    return [i.strip() for i in arg.split(",")]
