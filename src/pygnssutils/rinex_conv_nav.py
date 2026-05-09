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
from math import pi
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
    EPOCHMIN,
    GAL,
    GLO,
    GPS,
    IRN,
    NAV,
    QZS,
    RINEX_URA,
)
from pygnssutils.rinex_helpers import (
    DRNX,
    format_fileend,
    format_headerend,
    format_iono_corr,
    format_leapseconds,
    format_time_corr,
    get_fithours,
    get_svcode_rtcm,
)
from pygnssutils.rinex_subframes_gps import (
    GPS_LNAV_SUBFRAME_1,
    GPS_LNAV_SUBFRAME_2,
    GPS_LNAV_SUBFRAME_3,
    GPS_LNAV_SUBFRAME_4_P18,
)

BOD = "bod"
CLKBIAS = "clkbias"
CLKDRIFT = "clkdrift"
CLKRATE = "clkrate"
EPOCH = "epoch"
TARGET_SFR = 0b111


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
                self._convert_rxmsfrbx(parsed)
                res += 1
        elif isinstance(parsed, RawNav) and self._datasource in ("R", "S", "U"):
            self._convert_rawnav(parsed)
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

        Format of navdata dict::

            navdata = {
                (svcode (str), iodc (int)): {
                    "epoch": epoch (datetime),
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

        for (svcode, _), data in navdata.items():  # TODO sort???
            epoch = data[EPOCH].strftime("%Y %m %d %H %M %S")
            clkbias = data[CLKBIAS]
            clkdrift = data[CLKDRIFT]
            clkrate = data[CLKRATE]
            nav = (
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

        hdr = (
            self.__app.format_header_common(NAV)
            + format_iono_corr(self._ionocorr)
            + format_time_corr(self._timecorr)
            + format_leapseconds(
                self.__app.get_start_epoch(NAV),  # TODO check this is correct date
                self._gnss_filter,
            )
            + format_headerend()
        )
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
        Format Galileo 1045 F/NAV, 1046 I/NAV broadcast orbit blocks.

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

    # def _convert_navsource_sbas(self, data: RTCMMessage):
    #     """
    #     Format SBAS broadcast orbit blocks.

    #     :param RTCMMessage data: parsed SBAS Ephemerides message
    #     """

    #     svcode = get_svcode_rtcm(SBA, data.DF009)
    #     if self._useextepoch:
    #         epoch = self._get_external_epoch(NAV)
    #     else:
    #         epoch = self._get_local_epoch(data.wno, data.tow, SBA)
    #     if epoch == EPOCHMIN:
    #         return
    #     iodc = data.iodc
    #     self._navdata[(svcode, iodc)] = {}
    #     nvd = self._navdata[(svcode, iodc)]

    #     nvd[EPOCH] = epoch
    #     nvd[CLKBIAS] = data.a0  # clock bias
    #     nvd[CLKDRIFT] = data.a1  # clock drift
    #     nvd[CLKRATE] = data.a2  # clock drift rate
    #     nvd[BOD] = []
    #     nvb = nvd[BOD]
    #     for _ in range(3):  # broadcast orbit data blocks * 3
    #         nvb.append(["", "", "", ""])  # 4X,4D19.12
    #     # BROADCAST ORBIT - 1
    #     nvb[0][0] = data.posX  # - Satellite position X (km)
    #     nvb[0][1] = data.velX  # - velocity X dot (km/sec)
    #     nvb[0][2] = data.accX  # - X acceleration (km/sec2)
    #     nvb[0][3] = data.svhealth  # - health (0=healthy, 1=unhealthy) (MSB of 3-bit Bn)
    #     # BROADCAST ORBIT - 2
    #     nvb[1][0] = data.posY  # - Satellite position Y (km)
    #     nvb[1][1] = data.velY  # - velocity Y dot (km/sec)
    #     nvb[1][2] = data.accY  # - Y acceleration (km/sec2)
    #     nvb[1][3] = data.ura  # - Accuracy code (URA, meters)
    #     # BROADCAST ORBIT - 3
    #     nvb[2][0] = data.posZ  # - Satellite position Z (km)
    #     nvb[2][1] = data.velZ  # - velocity Z dot (km/sec)
    #     nvb[2][2] = data.accZ  # - Z acceleration (km/sec2)
    #     nvb[2][3] = data.iodn  # - IODN (Issue of Data Navigation

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

    def _convert_rawnav(self, data: RawNav):
        """
        Format RawNav broadcast orbit blocks.

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

    def _convert_ionocorr(self, data: Any, gnss: str):
        """
        Format ionospheric correction header blocks.

        :param Any data: data containing ionospheric corrections
        :param str gnss: gnss code
        """

        if gnss == GPS:
            # timemark is tow converted to hour of day
            # and then to A-X character
            tm = chr(int((data.tow % 86400) / 3600) + 65)
            self._ionocorr["GPSA"] = {
                "parm1": data.alpha0,
                "parm2": data.alpha1,
                "parm3": data.alpha2,
                "parm4": data.alpha3,
                "timemark": tm,
                "svid": data.svid,
            }
            self._ionocorr["GPSB"] = {
                "parm1": data.beta0,
                "parm2": data.beta1,
                "parm3": data.beta2,
                "parm4": data.beta3,
                "timemark": tm,
                "svid": data.svid,
            }

    def _convert_timecorr(self, data: Any, gnss: str):
        """
        Format time correction header blocks.

        :param Any data: data containing time corrections
        :param str gnss: gnss code
        """

        if gnss == GPS:
            self._timecorr["GPUT"] = {
                "a0": data.a0,
                "a1": data.a1,
                "timeref": data.tot,
                "weekno": data.wnt,
                "svcode": f"{data.gnss}{data.svcode:02d}",
                "source": 0,
            }

    def _convert_rxmsfrbx(self, data: UBXMessage):
        """
        Process UBX RXM-SFRBX raw NAV subframe messages
        using RawNav utility method.

        :param UBXMessage data: UBX RXM-SFRBX message
        """

        sfrdata = RawNav.process_rxm_sfrbx(data)
        # NB: remove gnss and sigid constraints once other GNSS are
        # transcribed
        if sfrdata.get("gnss", "") != GPS or sfrdata.get("sigid", "") not in (
            "1C",
            "2L",
        ):
            return

        gnss = sfrdata["gnss"]
        svid = sfrdata["svid"]
        sigid = sfrdata["sigid"]
        subframeid = sfrdata["subframeid"]
        svcode = sfrdata.get("svcode", 0)
        subframe = sfrdata["subframe"]

        try:
            self._navframes[(gnss, svid)] = self._navframes.get(
                (gnss, svid), RawNav(gnss, svid, sigid)
            )
            nav = self._navframes[(gnss, svid)]
            if subframeid == 1:  # clock parameters, sv health, etc.
                nav.parse(subframe, GPS_LNAV_SUBFRAME_1)
            elif subframeid == 2:  # ephemerides
                nav.parse(subframe, GPS_LNAV_SUBFRAME_2)
            elif subframeid == 3:  # ephemerides
                nav.parse(subframe, GPS_LNAV_SUBFRAME_3)
            elif subframeid == 4:
                if svcode == 56:  # page 18, ionospheric corrections
                    navit = RawNav(gnss, svid, sigid)
                    navit.parse(subframe, GPS_LNAV_SUBFRAME_4_P18)
                    self._convert_ionocorr(navit, gnss)
                    self._convert_timecorr(navit, gnss)
            if nav.sfracq & 0b111 == TARGET_SFR:
                self._convert_rawnav(self._navframes.pop((gnss, svid)))
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
