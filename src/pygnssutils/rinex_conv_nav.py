"""
rinex_conv_nav.py

RINEX Conversion Navigation class.

A preliminary implementation of a RINEX navigation conversion utility.

Converts NAV message data to RINEX Navigation text format.

Data sources currently handled:

- RawNav objects containing data collated from UBX RXM-SFRBX messages
  or other proprietary raw NAV data sources
- RTCM3 ephemerides messages 1019, 1020, 1041-1046 e.g. from RTK receiver
  or NTRIP data stream

Functionality may be extended in future versions - contributions welcome.

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

# pylint: disable=invalid-name, unused-argument, fixme

from datetime import datetime, timezone
from logging import getLogger
from math import pi, sqrt
from types import NoneType
from typing import Any, Literal

from pynmeagps import NMEAMessage, wnotow2utc
from pyrtcm import RTCMMessage
from pyubx2 import UBXMessage

from pygnssutils.exceptions import RINEXProcessingError
from pygnssutils.globals import VERBOSITY_MEDIUM
from pygnssutils.rawnav import RawNav
from pygnssutils.rinex_globals import (
    BDS,
    EPHNAVTYPES,
    EPOCHMIN,
    GAL,
    GLO,
    GPS,
    IRN,
    NAV,
    QZS,
    RINEX4,
    RINEX_URA,
    SBA,
)
from pygnssutils.rinex_helpers import (
    DRNX,
    format_eop,
    format_fileend,
    format_headerend,
    format_ion,
    format_iono_corr,
    format_leapseconds,
    format_nav_typesvmssg,
    format_sto,
    format_time_corr,
    get_fithours,
    get_svcode_rtcm,
)
from pygnssutils.rinex_subframes_gps import (
    GPS_CNAV_SUBFRAME_10,
    GPS_CNAV_SUBFRAME_11,
    GPS_CNAV_SUBFRAME_30,
    GPS_CNAV_SUBFRAME_32,
    GPS_CNAV_SUBFRAME_33,
    GPS_LNAV_SUBFRAME_1,
    GPS_LNAV_SUBFRAME_2,
    GPS_LNAV_SUBFRAME_3,
    GPS_LNAV_SUBFRAME_4_P18,
    GPS_SFRACQ_MAP,
)

AREF = 26559710
BOD = "bod"
CLKBIAS = "clkbias"
CLKDRIFT = "clkdrift"
CLKRATE = "clkrate"
EPH = "EPH"
EPOCH = "epoch"
OMEGADOTREF = -2.6e-9
RECTYPE = "rectype"
TARGET_SFR_GPS_LNAV = 0b111  # SFR 1(1), 2(2), 4p18(4)
TARGET_SFR_GPS_CNAV = 0b111  # SFR 10(1), 11(2), 30(4)


class RinexConverterNavigation:
    """
    Rinex Navigation Converter Class.
    """

    def __init__(
        self,
        app: Any,
        rinex_version: str,
        gnssfilter: list[str],
        obsfilter: list[str],
        datasource: Literal["R", "S", "N", "U"],
        minobs: int,
        verbosity: Literal[-1, 0, 1, 2, 3] = VERBOSITY_MEDIUM,
        logtofile: str = "",
        **kwargs,
    ):  # pylint: disable=too-many-arguments, too-many-positional-arguments
        """
        Constructor.

        :param Any app: application from which this class is invoked
        :param str rinex_version: RINEX protocol version (3.05)
        :param list[str] gnssfilter: List of GNSS codes to process
            (or blank for ALL) e.g. [GPS,GAL]
        :param list[str] obsfilter: List of observation codes to process
            (or blank for ALL) e.g. ["1C","2B"]
        :param Literal["R","S","N","U"] datasource: data source (R)
        :param int minobs: Minimum observations per observation type (10)
        :param Literal[-1,0,1,2,3] verbosity: log message verbosity -1 = critical, 0 = error,
            1 = warning, 2 = info, 3 = debug (1)
        :param str logtofile: fully qualified path to logfile ("" = no logfile)
        :param dict kwargs: user-defined keyword arguments to pass to conversion functions
        """

        self.logger = getLogger(__name__)

        self.__app = app  # pylint: disable=unused-private-member
        self._gnss_filter = gnssfilter
        self._obscode_filter = obsfilter
        self._datasource = "R" if datasource == "" else datasource
        self._minobs = minobs
        self.verbosity = int(verbosity)
        self.logtofile = logtofile
        self._rinex_version = rinex_version
        self._ionocorr = {}
        self._timecorr = {}
        self._eopcorr = {}
        self._leapseconds = ""
        self._navdata = {}  # holder for converted RINEX nav data
        self._navframes = {}  # holder for acquired partial NAV frames
        self._useextepoch = False
        self._station_set = False

    def process_input_data(
        self,
        parsed: UBXMessage | RTCMMessage | NMEAMessage | RawNav,
    ) -> int:
        """
        Process parsed GNSS message(s) containing relevant navigation data.

        :param UBXMessage | RTCMMessage | NMEAMessage | RawNav parsed: \
            parsed message
        :return: number of messages processed
        :rtype: int
        """

        res = 0
        if isinstance(parsed, UBXMessage):
            if parsed.identity == "RXM-SFRBX":
                self._collate_rxmsfrbx(parsed)
                res += 1
        elif isinstance(parsed, RTCMMessage) and self._datasource in ("N"):
            if parsed.identity in ("1005", "1006"):  # station ID
                self._convert_rtcm1005(parsed)
                res += 1
            elif (
                parsed.identity == "1019" and GPS in self._gnss_filter
            ):  # GPS Ephemerides
                self._convert_rtcm1019(parsed)
                res += 1
            elif (
                parsed.identity == "1020" and GLO in self._gnss_filter
            ):  # GLONASS Ephemerides
                self._convert_rtcm1020(parsed)
                res += 1
            elif (
                parsed.identity == "1041" and IRN in self._gnss_filter
            ):  # NavIC/IRNSS Ephemerides
                self._convert_rtcm1041(parsed)
                res += 1
            elif (
                parsed.identity == "1042" and BDS in self._gnss_filter
            ):  # Beidou Ephemerides
                self._convert_rtcm1042(parsed)
                res += 1
            elif (
                parsed.identity == "1044" and QZS in self._gnss_filter
            ):  # QZSS Ephemerides
                self._convert_rtcm1044(parsed)
                res += 1
            elif (
                parsed.identity == "1045" and GAL in self._gnss_filter
            ):  # Galileo F/NAV Ephemerides
                self._convert_rtcm1045(parsed)
                res += 1
            elif (
                parsed.identity == "1046" and GAL in self._gnss_filter
            ):  # Galileo I/NAV Ephemerides
                self._convert_rtcm1046(parsed)
                res += 1
        elif isinstance(parsed, NMEAMessage):
            if parsed.identity[2:] == "RMC":
                self._get_rmc_epoch(parsed)
        return res

    def process_output_file(self):
        """
        Process RINEX navigation file.
        """

        self._format_header()
        self._format_nav_data(self._navdata)
        self.__app.output(format_fileend(), NAV)

    def _format_nav_data(self, navdata: dict[tuple, dict] | str = ""):
        """
        Format navigation data for each svcode/iodc from navdata dict.

        Format of navdata dict:

            navdata = {
                (svcode (str), iodc (int)): {
                    "epoch": epoch (datetime),
                    "rectype: rectype (str),
                    "clkbias": clkbias (float),
                    "clkdrift": clkdrift (float),
                    "clkrate": clkrate (float),
                    "bod": [
                        [
                            parm1 (float),
                            parm2 (float),
                            parm3 (float),
                            parm4 (float),
                        ],
                    ], # # broadcast orbit data blocks * 3, 4 or 7
                },
                ...
            }

        :param dict[tuple, dict] | str navdata: observation data dictionary
        """

        if navdata == "":
            navdata = {}

        if self._rinex_version >= RINEX4:
            for _, sto in self._timecorr.items():  # RINEX 4 system time offsets
                self.__app.output(sto, NAV)
            for _, ion in self._ionocorr.items():  # RINEX 4 ionospheric corrections
                self.__app.output(ion, NAV)
            for _, eop in self._eopcorr.items():  # RINEX 4 earth orient corrections
                self.__app.output(eop, NAV)

        for (svcode, _), data in navdata.items():  # TODO sort???
            if self._rinex_version >= RINEX4:
                rectyp = format_nav_typesvmssg(EPH, svcode, data[RECTYPE])
            else:
                rectyp = ""
            epoch = data[EPOCH].strftime("%Y %m %d %H %M %S")
            clkbias = data[CLKBIAS]
            clkdrift = data[CLKDRIFT]
            clkrate = data[CLKRATE]
            nav = (
                f"{rectyp}"
                f"{svcode} {epoch}{DRNX(clkbias,19,12)}"
                f"{DRNX(clkdrift,19,12)}{DRNX(clkrate,19,12)}\n"
            )
            for parm1, parm2, parm3, parm4 in data[BOD]:
                nav += (
                    f"    {DRNX(parm1,19,12)}{DRNX(parm2,19,12)}"
                    f"{DRNX(parm3,19,12)}{DRNX(parm4,19,12)}\n"
                )
            self.__app.output(nav, NAV)

    def _format_header(self):
        """
        Format navigation header lines.
        """

        hdr = self.__app.format_header_common(NAV)
        if self._rinex_version < RINEX4:
            for _, ion in self._ionocorr.items():  # RINEX 3 ionospheric corrections
                hdr += ion
            for _, sto in self._timecorr.items():  # RINEX 3 system time offsets
                hdr += sto
        hdr += format_leapseconds(
            self.__app.get_start_epoch(NAV),  # TODO check this is correct date
            self._gnss_filter,
        )
        hdr += format_headerend()
        self.__app.output(hdr, NAV)

    def _convert_rtcm1005(self, data: RTCMMessage):
        """
        Format NTRIP station ID as user comment.

        :param RTCMMessage data: parsed 1005/6 NTRIP station ID message
        """

        if not self._station_set:
            sid = data.DF003
            x, y, z = data.DF025, data.DF026, data.DF027
            self.__app.user_comments.append(f"Format: RTCM3, Station ID: {sid}")
            self.__app.user_comments.append(
                f"Station ECEF: {DRNX(x,10,8)} {DRNX(y,10,8)} {DRNX(z,10,8)}"
            )
            self._station_set = True

    def _convert_rtcm1019(self, data: RTCMMessage):
        """
        Format GPS broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L361

        :param RTCMMessage data: parsed 1019 GPS Ephemerides message
        """

        svcode = get_svcode_rtcm(GPS, data.DF009)
        epoch = self._get_epoch(wno=data.DF076, toc=data.DF081, gnss=GPS)
        tom = data.DF093
        if epoch == EPOCHMIN:
            return
        iodc = data.DF085
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]

        nvd[EPOCH] = epoch
        nvd[RECTYPE] = EPHNAVTYPES[GPS, "L1 C/A"]
        nvd[CLKBIAS] = data.DF084  # clock bias
        nvd[CLKDRIFT] = data.DF083  # clock drift
        nvd[CLKRATE] = data.DF082  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # Multiply by pi to convert semicircles to radians
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.DF071  # - IODnav Issue of Data of the nav batch
        nvb[0][1] = data.DF086  # - Crs (meters)
        nvb[0][2] = data.DF087 * pi  # - Delta n (radians/sec)
        nvb[0][3] = data.DF088 * pi  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF089  # - Cuc (radians)
        nvb[1][1] = data.DF090  # - e Eccentricity
        nvb[1][2] = data.DF091  # - Cus (radians)
        nvb[1][3] = data.DF092  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF093  # - Toe Time of Ephemeris (sec of GAL week)
        nvb[2][1] = data.DF094  # - Cic (radians)
        nvb[2][2] = data.DF095 * pi  # - OMEGA0 (radians)
        nvb[2][3] = data.DF096  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF097 * pi  # - i0 (radians)
        nvb[3][1] = data.DF098  # - Crc (meters)
        nvb[3][2] = data.DF099 * pi  # - omega (radians)
        nvb[3][3] = data.DF100 * pi  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF079 * pi  # - IDOT (radians/sec)
        nvb[4][1] = data.DF078  # - codes on L2 channel
        nvb[4][2] = data.DF076  # - GPS Week # (to go with TOE)
        nvb[4][3] = data.DF103  # - L2 P data flag
        # BROADCAST ORBIT - 6
        nvb[5][0] = RINEX_URA[GPS].get(data.DF077, 0)  # - SV accuracy (meters)
        nvb[5][1] = data.DF102  # - SV health
        nvb[5][2] = data.DF101  # - TGD (seconds)
        nvb[5][3] = data.DF085  # - IODC, clock
        # BROADCAST ORBIT - 7
        nvb[6][0] = tom * 4  # HOW tow (17 LSB) shifted to 19 bits
        nvb[6][1] = get_fithours(data.DF085, data.DF137, GPS)  # FIT hours
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

    def _convert_rtcm1020(self, data: RTCMMessage):
        """
        Format GLONASS broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L394

        :param RTCMMessage data: parsed 1020 GLONASS Ephemerides message
        """

        svcode = get_svcode_rtcm(GLO, data.DF038)

        # TODO which GLONASS fields represent wno and toc?
        # epoch = self._get_epoch(wno=data.DF???, toc=data.DF???, gnss=GLO)
        epoch = self._get_external_epoch(NAV)
        if epoch == EPOCHMIN:
            return
        iodc = data.DF107  # tk
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]
        nvd[EPOCH] = epoch
        nvd[RECTYPE] = EPHNAVTYPES[GLO, "L1 C/A"]
        nvd[CLKBIAS] = (
            data.DF124
        )  # SV clock bias (sec) (-TauN) TODO should val be negated?
        nvd[CLKDRIFT] = data.DF115  # SV relative frequency bias (+GammaN)
        # Message frame time (tk+(nd*86400))
        nvd[CLKRATE] = data.DF107 + (data.DF132 * 86400)
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(4):  # broadcast orbit data blocks * 4
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.DF112  # - Satellite position X (km)
        nvb[0][1] = data.DF111  # - velocity X dot (km/sec)
        nvb[0][2] = data.DF113  # - X acceleration (km/sec2)
        nvb[0][3] = data.DF108  # - health (0=healthy, 1=unhealthy) (MSB of 3-bit Bn)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF115  # - Satellite position Y (km)
        nvb[1][1] = data.DF114  # - velocity Y dot (km/sec)
        nvb[1][2] = data.DF116  # - Y acceleration (km/sec2)
        nvb[1][3] = data.DF040  # - frequency number (-7...+13) (-7...+6 ICD 5.1)
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF118  # - Satellite position Z (km)
        nvb[2][1] = data.DF117  # - velocity Z dot (km/sec)
        nvb[2][2] = data.DF119  # - Z acceleration (km/sec2)
        nvb[2][3] = data.DF126  # - Age of oper. information (days) (E)
        # BROADCAST ORBIT - 4
        nvb[3][0] = ""  # TODO data.status  # - Status Flags (FLOAT → INTEGER)
        nvb[3][1] = data.DF125  # - L1/L2 group delay difference .(in seconds)
        nvb[3][2] = data.DF105  # - URAI ; GLO-M/K only – raw accuracy index
        nvb[3][3] = data.DF104  # - Health Flags (FLOAT → INTEGER)

    def _convert_rtcm1045(self, data: RTCMMessage):
        """
        Format Galileo 1045 F/NAV broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L868

        :param RTCMMessage data: parsed 1045 Galileo Ephemerides message
        """

        svcode = get_svcode_rtcm(GAL, data.DF252)
        epoch = self._get_epoch(wno=data.DF289, toc=data.DF304, gnss=GAL)
        tom = data.DF304
        if epoch == EPOCHMIN:
            return
        iodc = data.DF290
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]
        nvd[EPOCH] = epoch
        nvd[RECTYPE] = EPHNAVTYPES[GAL, "E5a"]
        nvd[CLKBIAS] = data.DF296  # clock bias
        nvd[CLKDRIFT] = data.DF295  # clock drift
        nvd[CLKRATE] = data.DF294  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.DF290  # - IODnav Issue of Data of the nav batch
        nvb[0][1] = data.DF297  # - Crs (meters)
        nvb[0][2] = data.DF298 * pi  # - Delta n (radians/sec)
        nvb[0][3] = data.DF299 * pi  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF300  # - Cuc (radians)
        nvb[1][1] = data.DF301  # - e Eccentricity
        nvb[1][2] = data.DF302  # - Cus (radians)
        nvb[1][3] = data.DF303  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF304  # - Toe Time of Ephemeris (sec of GAL week)
        nvb[2][1] = data.DF305  # - Cic (radians)
        nvb[2][2] = data.DF306 * pi  # - OMEGA0 (radians)
        nvb[2][3] = data.DF307  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF308 * pi  # - i0 (radians)
        nvb[3][1] = data.DF309  # - Crc (meters)
        nvb[3][2] = data.DF310 * pi  # - omega (radians)
        nvb[3][3] = data.DF311 * pi  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF292 * pi  # - IDOT (radians/sec)
        nvb[4][1] = ""  # data.sources  # - TODO Data sources (FLOAT → INTEGER)
        nvb[4][2] = data.DF289  # - GAL Week # (to go with TOE)
        nvb[4][3] = ""  # - Spare
        # BROADCAST ORBIT - 6
        nvb[5][0] = data.DF291  # - SISA Signal in space accuracy (meters)
        # TODO data.DF314 & data.DF315  # - SV HS/DVS
        nvb[5][1] = ""
        nvb[5][2] = data.DF312  # - BGD E5a/E1 (seconds)
        nvb[5][3] = 0  # - BGD E5b/E1 (seconds)
        # BROADCAST ORBIT - 7
        nvb[6][0] = tom
        nvb[6][1] = ""  # - Spare
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

    def _convert_rtcm1046(self, data: RTCMMessage):
        """
        Format Galileo 1046 I/NAV broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L899

        :param RTCMMessage data: parsed 1046 Galileo Ephemerides message
        """

        svcode = get_svcode_rtcm(GAL, data.DF252)
        epoch = self._get_epoch(wno=data.DF289, toc=data.DF304, gnss=GAL)
        tom = data.DF304
        if epoch == EPOCHMIN:
            return
        iodc = data.DF290
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]
        nvd[EPOCH] = epoch
        nvd[RECTYPE] = EPHNAVTYPES[GAL, "E5b"]
        nvd[CLKBIAS] = data.DF296  # clock bias
        nvd[CLKDRIFT] = data.DF295  # clock drift
        nvd[CLKRATE] = data.DF294  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.DF290  # - IODnav Issue of Data of the nav batch
        nvb[0][1] = data.DF297  # - Crs (meters)
        nvb[0][2] = data.DF298 * pi  # - Delta n (radians/sec)
        nvb[0][3] = data.DF299 * pi  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF300  # - Cuc (radians)
        nvb[1][1] = data.DF301  # - e Eccentricity
        nvb[1][2] = data.DF302  # - Cus (radians)
        nvb[1][3] = data.DF303  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF304  # - Toe Time of Ephemeris (sec of GAL week)
        nvb[2][1] = data.DF305  # - Cic (radians)
        nvb[2][2] = data.DF306 * pi  # - OMEGA0 (radians)
        nvb[2][3] = data.DF307  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF308 * pi  # - i0 (radians)
        nvb[3][1] = data.DF309  # - Crc (meters)
        nvb[3][2] = data.DF310 * pi  # - omega (radians)
        nvb[3][3] = data.DF311 * pi  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF292 * pi  # - IDOT (radians/sec)
        nvb[4][1] = ""  # data.sources  # - TODO Data sources (FLOAT → INTEGER)
        nvb[4][2] = data.DF289  # - GAL Week # (to go with TOE)
        nvb[4][3] = ""  # - Spare
        # BROADCAST ORBIT - 6
        nvb[5][0] = data.DF286  # - SISA Signal in space accuracy (meters)
        # TODO data.DF316 & data.DF317 & data.287 & data.DF288  # - SV HS/DVS
        nvb[5][1] = ""
        nvb[5][2] = data.DF312  # - BGD E5a/E1 (seconds)
        nvb[5][3] = data.DF313  # - BGD E5b/E1 (seconds)
        # BROADCAST ORBIT - 7
        nvb[6][0] = tom
        nvb[6][1] = ""  # - Spare
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

    def _convert_rtcm1042(self, data: RTCMMessage):
        """
        Format Beidou broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L805

        :param RTCMMessage data: parsed 1042 Beidou Ephemerides message
        """

        svcode = get_svcode_rtcm(BDS, data.DF488)
        epoch = self._get_epoch(wno=data.DF489, toc=data.DF493, gnss=BDS)
        tom = data.DF505
        if epoch == EPOCHMIN:
            return
        iodc = data.DF497
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]

        nvd[EPOCH] = epoch
        nvd[RECTYPE] = EPHNAVTYPES[BDS, "B1C"]  # TODO
        nvd[CLKBIAS] = data.DF496  # clock bias
        nvd[CLKDRIFT] = data.DF495  # clock drift
        nvd[CLKRATE] = data.DF494  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.DF492  # - AODE Age of Data, Ephemeris
        nvb[0][1] = data.DF498  # - Crs (meters)
        nvb[0][2] = data.DF499 * pi  # - Delta n (radians/sec)
        nvb[0][3] = data.DF500 * pi  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF501  # - Cuc (radians)
        nvb[1][1] = data.DF502  # - e Eccentricity
        nvb[1][2] = data.DF503  # - Cus (radians)
        nvb[1][3] = data.DF504  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF505  # - Toe Time of Ephemeris (sec of BDT week)
        nvb[2][1] = data.DF506  # - Cic (radians)
        nvb[2][2] = data.DF507 * pi  # - OMEGA0 (radians)
        nvb[2][3] = data.DF508  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF509 * pi  # - i0 (radians)
        nvb[3][1] = data.DF510  # - Crc (meters)
        nvb[3][2] = data.DF511 * pi  # - omega (radians)
        nvb[3][3] = data.DF512 * pi  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF491 * pi  # - IDOT (radians/sec)
        nvb[4][1] = ""  # - Spare
        nvb[4][2] = data.DF489  # - BDT Week # (to go with TOE)
        nvb[4][3] = ""  # - Spare
        # BROADCAST ORBIT - 6
        nvb[5][0] = data.DF490  # - SV accuracy (metres)
        nvb[5][1] = data.DF515  # - SatH1 SV Health
        nvb[5][2] = data.DF513  # - TGD1 B1/B3 (seconds)
        nvb[5][3] = data.DF514  # - TGD2 B2/B3 (seconds)
        # BROADCAST ORBIT - 7
        nvb[6][0] = tom
        nvb[6][1] = data.DF497  # - AODC Age of Data Clock
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

    def _convert_rtcm1044(self, data: RTCMMessage):
        """
        Format QZSS broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L836

        :param RTCMMessage data: parsed 1044 QZSS Ephemerides message
        """

        svcode = get_svcode_rtcm(QZS, data.DF429)
        epoch = self._get_epoch(wno=data.DF452, toc=data.DF442, gnss=QZS)
        tom = data.DF442
        if epoch == EPOCHMIN:
            return
        iodc = data.DF456
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]

        nvd[EPOCH] = epoch
        nvd[RECTYPE] = EPHNAVTYPES[QZS, "L1 C/A"]  # TODO
        nvd[CLKBIAS] = data.DF433  # clock bias
        nvd[CLKDRIFT] = data.DF432  # clock drift
        nvd[CLKRATE] = data.DF431  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.DF434  # - IODE Issue of Data, Ephemeris
        nvb[0][1] = data.DF435  # - Crs (meters)
        nvb[0][2] = data.DF436 * pi  # - Delta n (radians/sec)
        nvb[0][3] = data.DF437 * pi  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF438  # - Cuc (radians)
        nvb[1][1] = data.DF439  # - e Eccentricity
        nvb[1][2] = data.DF440  # - Cus (radians)
        nvb[1][3] = data.DF441  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF442  # - Toe Time of Ephemeris (sec of GAL week)
        nvb[2][1] = data.DF443  # - Cic (radians)
        nvb[2][2] = data.DF444 * pi  # - OMEGA0 (radians)
        nvb[2][3] = data.DF445  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF446 * pi  # - i0 (radians)
        nvb[3][1] = data.DF447  # - Crc (meters)
        nvb[3][2] = data.DF448 * pi  # - omega (radians)
        nvb[3][3] = data.DF449 * pi  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF450 * pi  # - IDOT (radians/sec)
        nvb[4][1] = data.DF451  # - Codes on L2 channel
        nvb[4][2] = data.DF452  # - GPS Week # (to go with TOE)
        nvb[4][3] = 1  # - L2P data flag set to 1
        # BROADCAST ORBIT - 6
        nvb[5][0] = data.DF453  # - SV accuracy (meters)
        nvb[5][1] = data.DF454  # - SV health (FLOAT → INTEGER)
        nvb[5][2] = data.DF455  # - TGD (seconds)
        nvb[5][3] = data.DF456  # - IODC Issue of Data, Clock
        # BROADCAST ORBIT - 7
        nvb[6][0] = tom
        nvb[6][1] = data.DF457  # - Fit interval flag (0 / 1)
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

    def _convert_rtcm1041(self, data: RTCMMessage):
        """
        Format NavIC broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L772

        :param RTCMMessage data: parsed 1041 NavIC Ephemerides message
        """

        svcode = get_svcode_rtcm(IRN, data.DF516)
        epoch = self._get_epoch(wno=data.DF517, toc=data.DF522, gnss=IRN)
        tom = data.DF537
        if epoch == EPOCHMIN:
            return
        iodc = data.DF525
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]

        nvd[EPOCH] = epoch
        nvd[RECTYPE] = EPHNAVTYPES[IRN, "L1"]  # TODO
        nvd[CLKBIAS] = data.DF518  # clock bias
        nvd[CLKDRIFT] = data.DF519  # clock drift
        nvd[CLKRATE] = data.DF520  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.DF525  # - Issue of Data, Ephemeris and Clock
        nvb[0][1] = data.DF534  # - Crs (meters)
        nvb[0][2] = data.DF524 * pi  # - Delta n (radians/sec)
        nvb[0][3] = data.DF536 * pi  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF529  # - Cuc (radians)
        nvb[1][1] = data.DF538  # - e Eccentricity
        nvb[1][2] = data.DF530  # - Cus (radians)
        nvb[1][3] = data.DF539  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF537  # - Toe Time of Ephemeris (sec of NAVIC week)
        nvb[2][1] = data.DF531  # - Cic (radians)
        nvb[2][2] = data.DF540 * pi  # - OMEGA0 (radians)
        nvb[2][3] = data.DF532  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF543 * pi  # - i0 (radians)
        nvb[3][1] = data.DF533  # - Crc (meters)
        nvb[3][2] = data.DF541 * pi  # - omega (radians)
        nvb[3][3] = data.DF542 * pi  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF535 * pi  # - IDOT (radians/sec)
        nvb[4][1] = ""  # Spare
        nvb[4][2] = data.DF517  # - TODO check this IRN Week # (to go with TOE)
        nvb[4][3] = ""  # - Spare
        # BROADCAST ORBIT - 6
        nvb[5][0] = data.DF521  # - User Range Accuracy (metres)
        nvb[5][1] = ""  # TODO data.DF527 & data.DF528 # - SV health (FLOAT → INTEGER)
        nvb[5][2] = data.DF523  # - TGD (seconds)
        nvb[5][3] = ""  # - Spare
        # BROADCAST ORBIT - 7
        nvb[6][0] = tom
        nvb[6][1] = ""  # - Spare
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

    def _convert_rawnav_gps_lnav(self, data: RawNav):
        """
        Format RawNav GPS LNAV broadcast orbit blocks.

        :param RawNav data: RawNav object containing data \
            collated from UBX RXM-SFRBX messages or other \
            raw NAV subframe sources.
        """

        svcode = get_svcode_rtcm(data.gnss, data.svid)
        epoch = self._get_epoch(wno=data.wn, toc=data.toc, gnss=data.gnss)
        iodc = data.iodc
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]

        nvd[EPOCH] = epoch
        nvd[RECTYPE] = "LNAV"
        nvd[CLKBIAS] = data.af0  # clock bias
        nvd[CLKDRIFT] = data.af1  # clock drift
        nvd[CLKRATE] = data.af2  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # Multiply by pi to convert semicircles to radians
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.iode  # - Issue of Data, Ephemeris
        nvb[0][1] = data.crs  # - Crs (meters)
        nvb[0][2] = data.deltan * pi  # - Delta n (radians/sec)
        nvb[0][3] = data.m0 * pi  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.cuc  # - Cuc (radians)
        nvb[1][1] = data.e  # - e Eccentricity
        nvb[1][2] = data.cus  # - Cus (radians)
        nvb[1][3] = data.sqrta  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.toe  # - Toe Time of Ephemeris (sec of NAVIC week)
        nvb[2][1] = data.cic  # - Cic (radians)
        nvb[2][2] = data.omega0 * pi  # - OMEGA0 (radians)
        nvb[2][3] = data.cis  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.i0 * pi  # - i0 (radians)
        nvb[3][1] = data.crc  # - Crc (meters)
        nvb[3][2] = data.omega * pi  # - omega (radians)
        nvb[3][3] = data.omegadot * pi  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.idot * pi  # - IDOT (radians/sec)
        nvb[4][1] = data.l2codes  # codes on L2 channel
        nvb[4][2] = data.wn  # - continuous week number, NOT mod 1024
        nvb[4][3] = data.l2pdata  # - L2 P data
        # BROADCAST ORBIT - 6
        nvb[5][0] = RINEX_URA[GPS].get(data.ura, 0)  # - SV Accuracy (metres)
        nvb[5][1] = data.svhealth  # - SV health (FLOAT → INTEGER)
        nvb[5][2] = data.tgd  # - TGD (seconds)
        nvb[5][3] = data.iodc  # Issue of Data, Clock
        # BROADCAST ORBIT - 7
        nvb[6][0] = data.tow * 4  # HOW tow (17 LSB) shifted to 19 bits
        nvb[6][1] = get_fithours(data.iodc, data.fit, data.gnss)  # FIT hours
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

    def _convert_rawnav_gps_cnav(self, data: RawNav):
        """
        Format RawNav GPS CNAV broadcast orbit blocks.

        :param RawNav data: RawNav object containing data \
            collated from UBX RXM-SFRBX messages or other \
            raw NAV subframe sources.
        """

        svcode = get_svcode_rtcm(data.gnss, data.svid)
        epoch = self._get_epoch(wno=data.wn, toc=data.toc, gnss=data.gnss)
        iodc = data.toc  # TODO confirm
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]

        nvd[EPOCH] = epoch
        nvd[RECTYPE] = "CNAV"
        nvd[CLKBIAS] = data.af0n  # clock bias
        nvd[CLKDRIFT] = data.af1n  # clock drift
        nvd[CLKRATE] = data.af2n  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(8):  # broadcast orbit data blocks * 8
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # Multiply by pi to convert semicircles to radians
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.adot  # - Issue of Data, Ephemeris SFR10
        nvb[0][1] = data.crs  # - Crs (meters) SFR11
        nvb[0][2] = data.deltan0 * pi  # - Delta n (radians/sec) SFR10
        nvb[0][3] = data.m0 * pi  # - M0 (radians) SFR10
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.cuc  # - Cuc (radians) SFR11
        nvb[1][1] = data.e  # - e Eccentricity SFR10
        nvb[1][2] = data.cus  # - Cus (radians) SFR11
        # nvb[1][3] = data.sqrta  # - sqrt(a) (sqrt(m)) SFR37
        nvb[1][3] = sqrt(AREF - data.deltaa)  # - sqrt(a) (sqrt(m)) SFR10
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.top  # - Toe Time of Ephemeris (sec of NAVIC week) SFR10
        nvb[2][1] = data.cic  # - Cic (radians) SFR11
        nvb[2][2] = data.omega0 * pi  # - OMEGA0 (radians) SFR11
        nvb[2][3] = data.cis  # - Cis (radians) SFR11
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.i0 * pi  # - i0 (radians) SFR11
        nvb[3][1] = data.crc  # - Crc (meters) SFR11
        nvb[3][2] = data.omega * pi  # - omega (radians) SFR10
        # nvb[3][3] = data.omegadot * pi  # - OMEGA DOT (radians/sec) SFR37
        nvb[3][3] = (
            OMEGADOTREF - data.deltaomegadot
        ) * pi  # - OMEGA DOT (radians/sec) SFR11
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.idot * pi  # - IDOT (radians/sec) SFR11
        nvb[4][1] = data.deltan0 * pi  # SFR10
        nvb[4][2] = data.uraned0  # - user range error NED0 SFRCLK
        nvb[4][3] = data.uraned1  # - user range error NED1 SFRCLK
        # BROADCAST ORBIT - 6
        nvb[5][0] = data.uraed  # - user range error ED SFR10
        nvb[5][1] = (
            data.l1health | (data.l2health << 1) | (data.l5health << 2)
        )  # - L1,L2,L5 health SFR10
        nvb[5][2] = data.tgd  # - TGD (seconds) SFR30
        nvb[5][3] = data.uraned2  # user range error NED2 SFRCLK
        # BROADCAST ORBIT - 7
        nvb[6][0] = data.iscl1ca  # iono delay SFR30
        nvb[6][1] = data.iscl2c  # iono delay SFR30
        nvb[6][2] = data.iscl5i5  # iono delay SFR30
        nvb[6][3] = data.iscl5q5  # iono delay SFR30
        # BROADCAST ORBIT - 8
        nvb[7][0] = data.tow  # time of transmission TODO confirm value?
        nvb[7][1] = data.wn  # continuous week number SFR10
        nvb[7][2] = data.integrity | (data.l2phase << 1) | (data.alert << 2)

    def _convert_ionocorr(self, data: RawNav):
        """
        Format ionospheric correction blocks.

        RINEX 3 places these as IONOSPHERIC CORR header lines
        RINEX 4 places these as ION Navigation record types

        :param RawNav data: data containing ionospheric corrections
        """

        msgtype = "LNAV" if data.sigid == "1C" else "CNAV"
        tot = data.top if msgtype == "CNAV" else data.tot
        svcode = f"{data.gnss}{data.svid:02d}"
        if self._rinex_version < RINEX4:  # RINEX 3.05
            # timemark is tow converted to hour of day
            # and then to A-X character
            tm = chr(int((data.tow % 86400) / 3600) + 65)
            self._ionocorr["GPSA"] = format_iono_corr(
                corrtype="GPSA",
                svid=data.svid,
                timemark=tm,
                parm1=data.alpha0,
                parm2=data.alpha1,
                parm3=data.alpha2,
                parm4=data.alpha3,
            )
            self._ionocorr["GPSB"] = format_iono_corr(
                corrtype="GPSB",
                svid=data.svid,
                timemark=tm,
                parm1=data.beta0,
                parm2=data.beta1,
                parm3=data.beta2,
                parm4=data.beta3,
            )
        else:  # RINEX 4.02
            epoch = wnotow2utc(
                wno=data.wn,
                tow=int(tot * 1000),
                ls=0,  # use GPS time, not UTC time
                gnss=data.gnss,
                autoroll=True,
                modwno=False,
            )
            self._ionocorr[(svcode, epoch)] = format_ion(
                svcode=svcode,
                msgtype=msgtype,
                msgsubtype="",
                epoch=epoch,
                a0=data.alpha0,
                a1=data.alpha1,
                a2=data.alpha2,
                a3=data.alpha3,
                b0=data.beta0,
                b1=data.beta1,
                b2=data.beta2,
                b3=data.beta3,
            )

    def _convert_eopcorr(self, data: RawNav):
        """
        Format earth orientation correction blocks.

        RINEX 4 places these as EOP Navigation record types

        TODO check epoch and repetition

        :param RawNav data: data containing eop corrections
        """

        if self._rinex_version < RINEX4:  # # RINEX 3.05
            return

        svcode = f"{data.gnss}{data.svid:02d}"
        msgtype = "LNAV" if data.sigid == "1C" else "CNAV"
        tot = data.top if msgtype == "CNAV" else data.tot
        epoch = wnotow2utc(
            wno=data.wn,
            tow=int(tot * 1000),
            ls=0,  # use GPS time, not UTC time
            gnss=data.gnss,
            autoroll=True,
            modwno=False,
        )
        self._eopcorr[(svcode, epoch)] = format_eop(
            svcode=svcode,
            msgtype=msgtype,
            msgsubtype="",
            epoch=epoch,
            tom=data.teop,
            xp=data.pmx,
            dxpdt=data.pmxdot,
            dxpdt2=0,
            yp=data.pmy,
            dypdt=data.pmydot,
            dypdt2=0,
            deltaut1=data.deltautgps,
            ddeltaut1dt=data.deltautgpsdot,
            d2deltaut1dt2=0,
        )

    def _convert_timecorr(self, data: RawNav):
        """
        Format time correction blocks.

        RINEX 3 places these as TIME SYSTEM CORR header lines
        RINEX 4 places these as STO Navigation record types

        TODO check epoch and repetition

        :param RawNav data: data containing time corrections
        """

        svcode = f"{data.gnss}{data.svid:02d}"
        msgtype = "LNAV" if data.sigid == "1C" else "CNAV"
        tot = data.top if msgtype == "CNAV" else data.tot
        if self._rinex_version < RINEX4:  # RINEX 3.05
            self._timecorr["GPUT"] = format_time_corr(
                corrtype="GPUT",
                svcode=svcode,
                source="0",
                timeref=tot,
                weekno=data.wn,
                a0=data.a0,
                a1=data.a1,
            )
        else:  # RINEX 4.02
            epoch = wnotow2utc(
                wno=data.wn,
                tow=int(tot * 1000),
                ls=0,  # use GPS time, not UTC time
                gnss=data.gnss,
                autoroll=True,
                modwno=False,
            )
            self._timecorr[(svcode, epoch)] = format_sto(
                svcode=svcode,
                msgtype=msgtype,
                msgsubtype="",
                epoch=epoch,
                timecode="GPUT",
                sbasid="",
                utcid="UTC(USNO)",
                tot=tot,
                a0=data.a0,
                a1=data.a1,
                a2=getattr(data, "a2", 0),
            )

    def _collate_rxmsfrbx(self, data: UBXMessage):
        """
         Collate raw NAV subframes from UBX RXM-SFRBX message
         using RawNav utility method.

        CURRENTLY ONLY GPS LNAV AND CNAV IMPLEMENTED, BUT
        METHOD READILY EXTENSIBLE.

         :param UBXMessage data: UBX RXM-SFRBX message
        """

        sfrdata = RawNav.process_rxm_sfrbx(data)

        # GPS LNAV
        if sfrdata.get("gnss", "") == GPS and sfrdata.get("sigid", "") == "1C":
            self._collate_rxmsfrbx_gps_lnav(sfrdata)
        # GPS CNAV
        elif sfrdata.get("gnss", "") == GPS and sfrdata.get("sigid", "") in (
            "2L",
            "2S",
            "5I",
            "5Q",
        ):
            self._collate_rxmsfrbx_gps_cnav(sfrdata)
        # GPS CNV2
        elif sfrdata.get("gnss", "") == GPS and sfrdata.get("sigid", "") in (
            "1S",
            "1L",
        ):
            pass  # TODO self._collate_rxmsfrbx_gps_cnv2(sfrdata)
        # GALILEO FNAV/INAV
        elif sfrdata.get("gnss", "") == GAL:
            pass  # TODO  self._collate_rxmsfrbx_gal_fnav(sfrdata)
        # GLONASS FDMA
        elif sfrdata.get("gnss", "") == GLO and sfrdata.get("sigid", "") in ("??",):
            pass  # TODO  self._collate_rxmsfrbx_glo_fdma(sfrdata)
        # GLONASS L1OC CDMA
        elif (
            sfrdata.get("gnss", "") == GLO
            and sfrdata.get("sigid", "") in ("??",)
            and self._rinex_version >= RINEX4
        ):
            pass  # TODO self._collate_rxmsfrbx_glo_l1oc(sfrdata)
        # GLONASS L3OC CDMA
        elif (
            sfrdata.get("gnss", "") == GLO
            and sfrdata.get("sigid", "") in ("??",)
            and self._rinex_version >= RINEX4
        ):
            pass  # TODO self._collate_rxmsfrbx_glo_l3oc(sfrdata)
        # QZSS LNAV
        elif sfrdata.get("gnss", "") == QZS and sfrdata.get("sigid", "") in ("??",):
            pass  # TODO self._collate_rxmsfrbx_qzs_lnav(sfrdata)
        # QZSS CNAV
        elif sfrdata.get("gnss", "") == QZS and sfrdata.get("sigid", "") in ("??",):
            pass  # TODO self._collate_rxmsfrbx_qzs_cnav(sfrdata)
        # QZSS CNV2
        elif sfrdata.get("gnss", "") == QZS and sfrdata.get("sigid", "") in ("??",):
            pass  # TODO self._collate_rxmsfrbx_qzs_cnv2(sfrdata)
        # BEIDOU D1/D2
        elif sfrdata.get("gnss", "") == BDS and sfrdata.get("sigid", "") in ("??",):
            pass  # TODO self._collate_rxmsfrbx_bds_d1d2(sfrdata)
        # BEIDOU CNV1
        elif sfrdata.get("gnss", "") == BDS and sfrdata.get("sigid", "") in ("??",):
            pass  # TODO self._collate_rxmsfrbx_bds_cnv1(sfrdata)
        # BEIDOU CNV2
        elif sfrdata.get("gnss", "") == BDS and sfrdata.get("sigid", "") in ("??",):
            pass  # TODO self._collate_rxmsfrbx_bds_cnv2(sfrdata)
        # BEIDOU CNV3
        elif sfrdata.get("gnss", "") == BDS and sfrdata.get("sigid", "") in ("??",):
            pass  # TODO self._collate_rxmsfrbx_bds_cnv3(sfrdata)
        #  SBAS
        elif sfrdata.get("gnss", "") == SBA:
            pass  # TODO self._collate_rxmsfrbx_sba(sfrdata)
        # NAVIC LNAV
        elif sfrdata.get("gnss", "") == IRN and sfrdata.get("sigid", "") in ("??",):
            pass  # TODO self._collate_rxmsfrbx_irn_lnav(sfrdata)
        # NAVIC L1NV
        elif (
            sfrdata.get("gnss", "") == IRN
            and sfrdata.get("sigid", "") in ("??",)
            and self._rinex_version >= RINEX4
        ):
            pass  # TODO self._collate_rxmsfrbx_irn_l1nv(sfrdata)

    def _collate_rxmsfrbx_gps_lnav(
        self, sfrdata: dict[str, str | int | float | NoneType]
    ):
        """
        Collate raw GPS LNAV subframes from UBX RXM-SFRBX message
        using RawNav utility method.

        :param dict[str, str | int | float | NoneType] sfrdata: raw subframe data
        """

        gnss = sfrdata["gnss"]
        svid = sfrdata["svid"]
        sigid = sfrdata["sigid"]
        subframeid = sfrdata["subframeid"]
        svcode = sfrdata.get("svcode", 0)
        subframe = sfrdata["subframe"]

        try:
            self._navframes[(gnss, svid, sigid)] = self._navframes.get(
                (gnss, svid, sigid), RawNav(gnss, svid, sigid)
            )
            nav = self._navframes[(gnss, svid, sigid)]
            if subframeid == 1:  # clock parameters, sv health, etc.
                nav.parse(subframe, GPS_LNAV_SUBFRAME_1, GPS_SFRACQ_MAP)
            elif subframeid == 2:  # ephemerides
                nav.parse(subframe, GPS_LNAV_SUBFRAME_2, GPS_SFRACQ_MAP)
            elif subframeid == 3:  # ephemerides
                nav.parse(subframe, GPS_LNAV_SUBFRAME_3, GPS_SFRACQ_MAP)
            elif subframeid == 4:
                if svcode == 56:  # page 18, ionospheric & time corrections
                    nav.parse(subframe, GPS_LNAV_SUBFRAME_4_P18, GPS_SFRACQ_MAP)
                    self._convert_ionocorr(nav)
                    self._convert_timecorr(nav)
            # when all the relevant subframes have been acquired, create a NAV record
            if nav.sfracq & 0b111 == TARGET_SFR_GPS_LNAV:  # 1,2,3
                self._convert_rawnav_gps_lnav(self._navframes.pop((gnss, svid, sigid)))
        except RINEXProcessingError as err:
            raise RINEXProcessingError("Error process RXM-SFRBX data") from err

    def _collate_rxmsfrbx_gps_cnav(
        self, sfrdata: dict[str, str | int | float | NoneType]
    ):
        """
        Collate raw GPS CNAV subframes from UBX RXM-SFRBX message
        using RawNav utility method.

        :param dict[str, str | int | float | NoneType] sfrdata: raw subframe data
        """

        gnss = sfrdata["gnss"]
        svid = sfrdata["svid"]
        sigid = sfrdata["sigid"]
        subframeid = sfrdata["subframeid"]
        subframe = sfrdata["subframe"]

        try:
            self._navframes[(gnss, svid, sigid)] = self._navframes.get(
                (gnss, svid, sigid), RawNav(gnss, svid, sigid)
            )
            nav = self._navframes[(gnss, svid, sigid)]
            if subframeid == 10:  # ephemeris 1
                nav.parse(subframe, GPS_CNAV_SUBFRAME_10, GPS_SFRACQ_MAP)
            elif subframeid == 11:  # ephemeris 2
                nav.parse(subframe, GPS_CNAV_SUBFRAME_11, GPS_SFRACQ_MAP)
            elif subframeid == 30:  # clock, iono & group delay
                nav.parse(subframe, GPS_CNAV_SUBFRAME_30, GPS_SFRACQ_MAP)
                self._convert_ionocorr(nav)
            elif subframeid == 32 and self._rinex_version >= RINEX4:  # clock, eop
                nav.parse(subframe, GPS_CNAV_SUBFRAME_32, GPS_SFRACQ_MAP)
                self._convert_eopcorr(nav)
            elif subframeid == 33:  # clock, utc
                nav.parse(subframe, GPS_CNAV_SUBFRAME_33, GPS_SFRACQ_MAP)
                self._convert_timecorr(nav)
            # when all the relevant subframes have been acquired, create a NAV record
            if nav.sfracq & 0b111 == TARGET_SFR_GPS_CNAV:  # 10,11,30
                self._convert_rawnav_gps_cnav(self._navframes.pop((gnss, svid, sigid)))
        except RINEXProcessingError as err:
            raise RINEXProcessingError("Error process RXM-SFRBX data") from err

    def _get_external_epoch(self, rt: str) -> datetime:
        """
        Get epoch from external source (e.g. other NAV
        message in same data stream).

        :param str rt: RINEX observation type (OBS/NAV)
        :return: GNSS epoch
        :rtype: datetime
        """

        return self.__app.get_current_epoch(rt)

    def _get_epoch(
        self, wno: int, toc: int, gnss: Literal["G", "E", "C", "J", "I"]
    ) -> datetime:
        """
        Get epoch from message wno, tow.

        :param int wno: week number in GNSS time system
        :param int toc: time of week in seconds in GNSS time system
        :param Literal["G","E","C","J","I"] gnss: GNSS time system to use
        :return: GNSS epoch
        :rtype: datetime
        """

        epoch = wnotow2utc(
            wno=wno,
            tow=int(toc * 1000),
            ls=0,  # use GPS time, not UTC time
            gnss=gnss,
            autoroll=True,
            modwno=False,
        )
        self.__app.set_current_epoch(epoch, NAV)
        return epoch

    def _get_rmc_epoch(self, data: NMEAMessage) -> datetime | NoneType:
        """
        Get current epoch from NMEA RMC navigation message
        in same data stream.

        :param NMEAMessage data: parsed NMEA message
        :return: formatted GNSS epoch
        :rtype: datetime | NoneType
        """

        try:
            epoch = datetime(
                data.date.year,
                data.date.month,
                data.date.day,
                data.time.hour,
                data.time.minute,
                data.time.second,
                data.time.microsecond,
                tzinfo=timezone.utc,
            )
            if self._useextepoch:
                self.__app.set_current_epoch(epoch, NAV)
            else:
                self.logger.debug(f" RMC epoch: {epoch}")
            return epoch
        except (AttributeError, TypeError) as err:
            print(f"something went wrong {err}")
            return None
