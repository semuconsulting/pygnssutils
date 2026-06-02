"""
rinex_conv_nav.py

RINEX Conversion Navigation class.

Converts NAV message data to RINEX Navigation text format.

NB: Alpha release currently limited to following data sources:

- RawNav objects containing data collated from UBX RXM-SFRBX messages
  (GPS LNAV/CNAV, GAL FNAV,INAV, BDS D1 only)
- RTCM3 ephemerides messages 1019, 1020, 1041-1046 e.g. from RTK receiver
  or NTRIP data stream

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

# pylint: disable=invalid-name, unused-argument, fixme

from datetime import datetime, timezone
from logging import getLogger
from math import pi, sqrt
from types import MethodType, NoneType
from typing import Any, Literal

from pynmeagps import NMEAMessage
from pyrtcm import RTCMMessage
from pyubx2 import UBXMessage

from pygnssutils.exceptions import RINEXProcessingError
from pygnssutils.globals import VERBOSITY_MEDIUM
from pygnssutils.rawnav import RawNav, RawNavReader
from pygnssutils.rinex_globals import (
    AREF,
    BDS,
    BOD,
    CNAV,
    D1,
    D2,
    EOP,
    EPHNAVTYPES,
    EPOCHMIN,
    FNAV,
    GAL,
    GLO,
    GPS,
    INAV,
    ION,
    IRN,
    KLOB,
    LNAV,
    NAV,
    NEQUICK,
    OMEGADOTREF,
    QZS,
    RINEX4,
    RINEXGNSSR,
    STO,
    TARGET,
)
from pygnssutils.rinex_helpers import (  # format_timefirstlast,
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
    get_epoch,
    get_fithours,
    get_svcode_rtcm,
    gpsura2m,
)
from pygnssutils.rinex_subframes_bds import BDS_SUBFRAMEACQ_MAP
from pygnssutils.rinex_subframes_gal import GAL_SUBFRAMEACQ_MAP
from pygnssutils.rinex_subframes_gps import GPS_SUBFRAMEACQ_MAP

CLKBIAS = "clkbias"
CLKDRIFT = "clkdrift"
CLKRATE = "clkrate"
EPH = "EPH"
EPOCH = "epoch"
RECTYPE = "rectype"


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
        self._navstart = {}  # holder for first subframe markers
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
                self._format_rtcm1005(parsed)
                res += 1
            elif (
                parsed.identity == "1019" and GPS in self._gnss_filter
            ):  # GPS Ephemerides
                self._format_rtcm1019(parsed)
                res += 1
            elif (
                parsed.identity == "1020" and GLO in self._gnss_filter
            ):  # GLONASS Ephemerides
                self._format_rtcm1020(parsed)
                res += 1
            elif (
                parsed.identity == "1041" and IRN in self._gnss_filter
            ):  # NavIC/IRNSS Ephemerides
                self._format_rtcm1041(parsed)
                res += 1
            elif (
                parsed.identity == "1042" and BDS in self._gnss_filter
            ):  # Beidou Ephemerides
                self._format_rtcm1042(parsed)
                res += 1
            elif (
                parsed.identity == "1044" and QZS in self._gnss_filter
            ):  # QZSS Ephemerides
                self._format_rtcm1044(parsed)
                res += 1
            elif (
                parsed.identity == "1045" and GAL in self._gnss_filter
            ):  # Galileo F/NAV Ephemerides
                self._format_rtcm1045(parsed)
                res += 1
            elif (
                parsed.identity == "1046" and GAL in self._gnss_filter
            ):  # Galileo I/NAV Ephemerides
                self._format_rtcm1046(parsed)
                res += 1
        elif isinstance(parsed, NMEAMessage):
            if parsed.identity[2:] == "RMC":
                self._get_rmc_epoch(parsed)
        return res

    def _collate_rxmsfrbx(self, data: UBXMessage):
        """
        Collate raw NAV subframes from sequential UBX RXM-SFRBX
        messages using RawNav utility class.

        When all relevant subframes have been collated into a
        single frame, format NAV record.

        :param UBXMessage data: UBX RXM-SFRBX message
        :raises: RINEXProcessingError
        """

        try:

            rnr = RawNavReader()
            sfrdata = rnr.process_rxm_sfrbx(data)
            sfrmap = None  # dict
            formatter = None  # MethodType
            sfrstart = 1
            kwargs = {}
            gnss = sfrdata.get("gnss", "")
            sigid = sfrdata.get("sigid", "")

            # filter out any unwanted gnss or signal codes
            filtobs = self._obscode_filter != [""] and len(self._obscode_filter) > 0
            if gnss not in self._gnss_filter or (
                filtobs and sigid not in self._obscode_filter
            ):
                return

            if gnss == GPS:
                if sigid == "1C":
                    sfrmap = GPS_SUBFRAMEACQ_MAP[LNAV]
                    formatter = self._format_rawnav_gps_lnav
                elif sigid in ("2L", "2S", "5I", "5Q"):
                    sfrmap = GPS_SUBFRAMEACQ_MAP[CNAV]
                    sfrstart = 10
                    formatter = self._format_rawnav_gps_cnav
            elif gnss == GAL:
                if sigid == "5I":
                    sfrmap = GAL_SUBFRAMEACQ_MAP[FNAV]
                    formatter = self._format_rawnav_gal_fnav
                elif sigid in ("1B", "7I"):
                    sfrmap = GAL_SUBFRAMEACQ_MAP[INAV]
                    formatter = self._format_rawnav_gal_fnav
            elif gnss == BDS:
                if sigid in ("2I", "6I", "7I"):
                    if sfrdata.get("d1d2", 1) == 1:
                        sfrmap = BDS_SUBFRAMEACQ_MAP[D1]
                    else:
                        sfrmap = BDS_SUBFRAMEACQ_MAP[D2]
                    formatter = self._format_rawnav_bds_d1d2
                    kwargs = {"d1d2": sfrdata.get("d1d2", 0)}
            # elif other gnss/sigid, as and when I get to it TODO

            if sfrmap is None or formatter is None:
                return

            self._format_rxmsfrbx(sfrdata, sfrmap, formatter, sfrstart, **kwargs)

        except RINEXProcessingError as err:
            raise RINEXProcessingError("Error process UBX RXM-SFRBX data") from err

    def process_output_file(self):
        """
        Process RINEX navigation file.
        """

        self._format_header()
        self._format_nav_data(self._navdata)
        self.__app.output(format_fileend(), NAV)

    def _format_nav_data(
        self, navdata: dict[tuple[str, int], dict[str, Any]] | str = ""
    ):
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

        :param dict[tuple[str,int], dict[str, Any]] | str navdata: observation data dictionary
        """

        if navdata == "":
            navdata = {}

        # sort NAV records by epoch
        for (svcode, _), data in sorted(navdata.items(), key=lambda it: it[1][EPOCH]):
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
            if self._rinex_version >= RINEX4:
                self.__app.output(data.get(STO, ""), NAV)
                self.__app.output(data.get(ION, ""), NAV)
                self.__app.output(data.get(EOP, ""), NAV)

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
        # debug only vvv
        # hdr += format_timefirstlast(self.__app.get_start_epoch(NAV), "FIRST")
        # hdr += format_timefirstlast(self.__app.get_end_epoch(NAV), "LAST")
        # debug only ^^^
        hdr += format_headerend()
        self.__app.output(hdr, NAV)

    def _format_rtcm1005(self, data: RTCMMessage):
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

    def _format_rtcm1019(self, data: RTCMMessage):
        """
        Format GPS broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L361

        :param RTCMMessage data: parsed 1019 GPS Ephemerides message
        """

        svcode = get_svcode_rtcm(GPS, data.DF009)
        epoch, _ = get_epoch(wno=data.DF076, tow=data.DF081, gnss=GPS)
        self.__app.set_current_epoch(epoch, NAV)
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
        nvb[5][0] = gpsura2m(data.DF077)  # - SV accuracy (meters)
        nvb[5][1] = data.DF102  # - SV health
        nvb[5][2] = data.DF101  # - TGD (seconds)
        nvb[5][3] = data.DF085  # - IODC, clock
        # BROADCAST ORBIT - 7
        nvb[6][0] = tom * 4  # HOW tow (17 LSB) shifted to 19 bits
        nvb[6][1] = get_fithours(data.DF085, data.DF137, GPS)  # FIT hours
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

    def _format_rtcm1020(self, data: RTCMMessage):
        """
        Format GLONASS broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L394

        :param RTCMMessage data: parsed 1020 GLONASS Ephemerides message
        """

        svcode = get_svcode_rtcm(GLO, data.DF038)

        # TODO which GLONASS fields represent wno and toc?
        # epoch = get_epoch(wno=data.DF???, tow=data.DF???, gnss=GLO)
        # self.__app.set_current_epoch(epoch, NAV)
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

    def _format_rtcm1045(self, data: RTCMMessage):
        """
        Format Galileo 1045 F/NAV broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L868

        :param RTCMMessage data: parsed 1045 Galileo Ephemerides message
        """

        svcode = get_svcode_rtcm(GAL, data.DF252)
        epoch, _ = get_epoch(wno=data.DF289, tow=data.DF304, gnss=GAL)
        self.__app.set_current_epoch(epoch, NAV)
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

    def _format_rtcm1046(self, data: RTCMMessage):
        """
        Format Galileo 1046 I/NAV broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L899

        :param RTCMMessage data: parsed 1046 Galileo Ephemerides message
        """

        svcode = get_svcode_rtcm(GAL, data.DF252)
        epoch, _ = get_epoch(wno=data.DF289, tow=data.DF304, gnss=GAL)
        self.__app.set_current_epoch(epoch, NAV)
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

    def _format_rtcm1042(self, data: RTCMMessage):
        """
        Format Beidou broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L805

        :param RTCMMessage data: parsed 1042 Beidou Ephemerides message
        """

        svcode = get_svcode_rtcm(BDS, data.DF488)
        epoch, _ = get_epoch(wno=data.DF489, tow=data.DF493, gnss=BDS)
        self.__app.set_current_epoch(epoch, NAV)
        tom = data.DF505
        if epoch == EPOCHMIN:
            return
        iodc = data.DF497
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]

        nvd[EPOCH] = epoch
        nvd[RECTYPE] = EPHNAVTYPES[BDS, "B1C"]
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

    def _format_rtcm1044(self, data: RTCMMessage):
        """
        Format QZSS broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L836

        :param RTCMMessage data: parsed 1044 QZSS Ephemerides message
        """

        svcode = get_svcode_rtcm(QZS, data.DF429)
        epoch, _ = get_epoch(wno=data.DF452, tow=data.DF442, gnss=QZS)
        self.__app.set_current_epoch(epoch, NAV)
        tom = data.DF442
        if epoch == EPOCHMIN:
            return
        iodc = data.DF456
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]

        nvd[EPOCH] = epoch
        nvd[RECTYPE] = EPHNAVTYPES[QZS, "L1 C/A"]
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

    def _format_rtcm1041(self, data: RTCMMessage):
        """
        Format NavIC broadcast orbit blocks.

        https://github.com/semuconsulting/pyrtcm/blob/3c763bd0016698864ccccbb9988403d2b3a5ba7f/src/pyrtcm/rtcmtypes_get.py#L772

        :param RTCMMessage data: parsed 1041 NavIC Ephemerides message
        """

        svcode = get_svcode_rtcm(IRN, data.DF516)
        epoch, _ = get_epoch(wno=data.DF517, tow=data.DF522, gnss=IRN)
        self.__app.set_current_epoch(epoch, NAV)
        tom = data.DF537
        if epoch == EPOCHMIN:
            return
        iodc = data.DF525
        self._navdata[(svcode, iodc)] = {}
        nvd = self._navdata[(svcode, iodc)]

        nvd[EPOCH] = epoch
        nvd[RECTYPE] = EPHNAVTYPES[IRN, "L1"]
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

    def _format_rxmsfrbx(
        self,
        sfrdata: dict[str, str | int | float | None],
        sfrmap: dict[tuple[int, int] | str, tuple[dict, int] | int],
        formatter: MethodType,
        sfrstart: int,
        **kwargs,
    ):
        """
        Process UBX RXM-SFRBX record for given GNSS and Signal ID.

        :param dict[str, str | int | float | None] sfrdata: subframe metadata
        :param dict[tuple[int, int] | str, tuple[dict, int] | int] sfrmap: subframe \
            payload definition
        :param MethodType formatter: subframe formatting method
        :param int sfrstart: starting subframe id (normally 1)
        :param dict kwargs: keyword arguments
        :raises: RINEXProcessingError
        """

        gnss = sfrdata["gnss"]
        svid = sfrdata["svid"]
        sigid = sfrdata["sigid"]
        subframeid = sfrdata["subframeid"]
        subframepageid = sfrdata.get("subframepageid", 0)
        subframe = sfrdata["subframe"]
        sfrdict, sfracq = sfrmap.get((subframeid, subframepageid), (None, 0))
        target = sfrmap[TARGET]

        if subframeid == sfrstart:  # start at first subframe of frame
            self._navstart[(gnss, svid, sigid)] = True
        if not self._navstart.get((gnss, svid, sigid), False) or sfrdict is None:
            return

        self._navframes[(gnss, svid, sigid)] = self._navframes.get(
            (gnss, svid, sigid), RawNav(gnss, svid, sigid)
        )
        nav = self._navframes[(gnss, svid, sigid)]
        nav.parse(subframe, sfrdict, sfracq)
        # when all target subframes have been acquired, format NAV record from frame
        if nav.subframeacq & target == target:
            formatter(self._navframes.pop((gnss, svid, sigid)), **kwargs)
            self._navstart.pop((gnss, svid, sigid))

    def _format_rawnav_gps_lnav(self, data: RawNav, **kwargs):
        """
        Format RawNav GPS LNAV broadcast orbit blocks.

        :param RawNav data: RawNav object containing data \
            collated from UBX RXM-SFRBX messages or other \
            raw NAV subframe sources.
        """

        self._navdata[(data.svcode, data.iodc)] = {}
        nvd = self._navdata[(data.svcode, data.iodc)]

        epoch, _ = get_epoch(wno=data.wn, tow=data.tow, gnss=data.gnss)
        self.__app.set_current_epoch(epoch, NAV)
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
        nvb[5][0] = gpsura2m(data.ura)  # SV accuracy in meters
        nvb[5][1] = data.svhealth  # - SV health (FLOAT → INTEGER)
        nvb[5][2] = data.tgd  # - TGD (seconds)
        nvb[5][3] = data.iodc  # Issue of Data, Clock
        # BROADCAST ORBIT - 7
        nvb[6][0] = data.tow * 4  # HOW tow (17 LSB) shifted to 19 bits
        nvb[6][1] = get_fithours(data.iodc, data.fit, data.gnss)  # FIT hours
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

        if self._rinex_version < RINEX4:
            self._format_timecorr_3(data)
            self._format_ionocorr_3(data)
        else:  # RINEX 4.02
            nvd[STO] = self._format_timecorr_4(
                msgtype="LNAV",
                msgsubtype="",
                timecode="GPUT",
                utcid="UTC(USNO)",
                data=data,
            )
            nvd[ION] = self._format_ionocorr_4(
                msgtype="LNAV", msgsubtype="", model=KLOB, data=data
            )

    def _format_rawnav_gps_cnav(self, data: RawNav, **kwargs):
        """
        Format RawNav GPS CNAV broadcast orbit blocks.

        :param RawNav data: RawNav object containing data \
            collated from UBX RXM-SFRBX messages or other \
            raw NAV subframe sources.
        """

        self._navdata[(data.svcode, data.top)] = {}  # is top equivalent to iodc here?
        nvd = self._navdata[(data.svcode, data.top)]

        epoch, _ = get_epoch(wno=data.wn, tow=data.tow, gnss=data.gnss)
        self.__app.set_current_epoch(epoch, NAV)
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
        nvb[5][0] = data.uraed  # - SV Accuracy (metres)
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
        nvb[7][0] = data.tow  # time of transmission
        nvb[7][1] = data.wn  # continuous week number SFR10
        nvb[7][2] = data.integrity | (data.l2phase << 1) | (data.alert << 2)

        if self._rinex_version < RINEX4:
            self._format_timecorr_3(data)
            self._format_ionocorr_3(data)
        else:  # RINEX 4.02
            nvd[STO] = self._format_timecorr_4(
                msgtype="CNAV",
                msgsubtype="",
                timecode="GPUT",
                utcid="UTC(USNO)",
                data=data,
            )
            nvd[ION] = self._format_ionocorr_4(
                msgtype="CNAV", msgsubtype="", model=KLOB, data=data
            )
            try:
                nvd[EOP] = format_eop(
                    svcode=data.svcode,
                    msgtype="CNAV",
                    msgsubtype="",
                    epoch=data.epoch,
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
            except AttributeError:
                pass

    def _format_rawnav_gal_fnav(self, data: RawNav, **kwargs):
        """
        Format RawNav GAL FNAV & INAV broadcast orbit blocks.

        :param RawNav data: RawNav object containing data \
            collated from UBX RXM-SFRBX messages or other \
            raw NAV subframe sources.
        """

        self._navdata[(data.svcode, data.iodn)] = {}
        nvd = self._navdata[(data.svcode, data.iodn)]

        epoch, _ = get_epoch(wno=data.wn, tow=data.tow, gnss=data.gnss)
        self.__app.set_current_epoch(epoch, NAV)
        nvd[EPOCH] = epoch
        nvd[RECTYPE] = "FNAV" if data.sigid == "5I" else "INAV"
        nvd[CLKBIAS] = data.af0  # clock bias
        nvd[CLKDRIFT] = data.af1  # clock drift
        nvd[CLKRATE] = data.af2  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # Multiply by pi to convert semicircles to radians
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.iodn  # - Issue of Data, Ephemeris
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
        #  data.sigid 5I = E5a, 1B = E1B, 7I = E5b
        nvb[4][1] = (
            int(data.sigid == "1B")
            + (int(data.sigid == "5I") << 1)
            + (int(data.sigid == "7I") << 2)
            + (int(data.sigid == "5I") << 8)
            + (int(data.sigid == "7I") << 9)
        )  # data sources bitmask
        nvb[4][2] = data.wn  # - GAL week
        nvb[4][3] = ""
        # BROADCAST ORBIT - 6
        nvb[5][0] = data.sisa  # sisa
        nvb[5][1] = (
            getattr(data, "e1bdvs", 0)
            + (getattr(data, "e1bhs", 0) << 1)
            + (getattr(data, "e5advs", 0) << 3)
            + (getattr(data, "e5ahs", 0) << 4)
            + (getattr(data, "e5bdvs", 0) << 6)
            + (getattr(data, "e5bhs", 0) << 7)
        )  # sv health bitmask
        nvb[5][2] = getattr(data, "bgde5a", 0)  # BGD E5a
        nvb[5][3] = getattr(data, "bgde5b", 0)  # BGD E5b
        # BROADCAST ORBIT - 7
        nvb[6][0] = data.tow  # time of transmission
        nvb[6][1] = ""
        nvb[6][2] = ""
        nvb[6][3] = ""

        if self._rinex_version < RINEX4:
            self._format_timecorr_3(data)
            self._format_ionocorr_3(data)
        else:  # RINEX 4.02
            nvd[STO] = self._format_timecorr_4(
                msgtype="IFNV",
                msgsubtype="",
                timecode="GAUT",
                utcid="UTGAL",
                data=data,
            )
            nvd[ION] = self._format_ionocorr_4(
                msgtype="IFNV", msgsubtype="", model=NEQUICK, data=data
            )

    def _format_rawnav_bds_d1d2(self, data: RawNav, **kwargs):
        """
        Format RawNav BDS D1 & D2 (B1I, B2I, B3I) broadcast orbit blocks.

        :param RawNav data: RawNav object containing data \
            collated from UBX RXM-SFRBX messages or other \
            raw NAV subframe sources.
        :param int d1d2: 1 = D1, 2 = D2
        """

        d1d2 = kwargs.get("d1d2", 0)
        self._navdata[(data.svcode, data.aodc)] = {}
        nvd = self._navdata[(data.svcode, data.aodc)]

        epoch, _ = get_epoch(wno=data.wn, tow=data.tow, gnss=data.gnss)
        self.__app.set_current_epoch(epoch, NAV)
        nvd[EPOCH] = epoch
        nvd[RECTYPE] = "D2" if d1d2 == 2 else "D1"
        nvd[CLKBIAS] = data.af0  # clock bias
        nvd[CLKDRIFT] = data.af1  # clock drift
        nvd[CLKRATE] = data.af2  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # Multiply by pi to convert semicircles to radians
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.aode  # - Issue of Data, Ephemeris
        nvb[0][1] = data.crs  # - Crs (meters)
        nvb[0][2] = data.deltan * pi  # - Delta n (radians/sec)
        nvb[0][3] = data.m0 * pi  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.cuc  # - Cuc (radians)
        nvb[1][1] = data.e  # - e Eccentricity
        nvb[1][2] = data.cus  # - Cus (radians)
        nvb[1][3] = data.sqrta  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.toe  # - Time of Ephemeris
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
        nvb[4][1] = ""
        nvb[4][2] = data.wn  # - BDS week
        nvb[4][3] = ""
        # BROADCAST ORBIT - 6
        nvb[5][0] = data.urai  # sv accuracy
        nvb[5][1] = data.sath1  # sv health
        nvb[5][2] = data.tgd1  #
        nvb[5][3] = data.tgd2  #
        # BROADCAST ORBIT - 7
        nvb[6][0] = data.tow  # time of transmission
        nvb[6][1] = data.aodc  # age of data clock
        nvb[6][2] = ""
        nvb[6][3] = ""

        if self._rinex_version < RINEX4:
            self._format_timecorr_3(data)
            self._format_ionocorr_3(data)
        else:  # RINEX 4.02
            nvd[STO] = self._format_timecorr_4(
                msgtype="D2" if d1d2 == 2 else "D1",
                msgsubtype="",
                timecode="BDUT",
                utcid="UT(NTSC)",
                data=data,
            )
            nvd[ION] = self._format_ionocorr_4(
                msgtype="D2" if d1d2 == 2 else "D1",
                msgsubtype="",
                model=KLOB,
                data=data,
            )

    def _format_timecorr_3(self, data: RawNav):
        """
        Format RINEX 3 ime correction blocks.

        RINEX 3 places these as TIME SYSTEM CORR header lines.

        :param RawNav data: data containing time corrections
        """

        timecode = f"{RINEXGNSSR[data.gnss][0:2]}UT"
        self._timecorr[timecode] = format_time_corr(
            corrtype=timecode,
            svcode=data.svcode,
            source="0",
            timeref=data.toc,
            weekno=data.wn,
            a0=data.a0,
            a1=data.a1,
        )

    def _format_timecorr_4(
        self, msgtype: str, msgsubtype: str, timecode: str, utcid: str, data: RawNav
    ) -> str:
        """
        Format RINEX 4time correction blocks.

        RINEX 4 places these as STO Navigation record types.

        :param str msgtype: message type
        :param str msgsubtype: message subtype
        :param str timecode: timecode
        :param str utcid: UTC timesource name
        :param RawNav data: data containing time corrections
        :return: formatted string
        :rtype: str
        """

        epoch, _ = get_epoch(wno=data.wn, tow=data.tow, gnss=data.gnss)
        return format_sto(
            svcode=data.svcode,
            msgtype=msgtype,
            msgsubtype=msgsubtype,
            epoch=epoch,
            timecode=timecode,
            sbasid="",
            utcid=utcid,
            tot=data.toc,
            a0=data.a0,
            a1=data.a1,
            a2=getattr(data, "a2", 0),
        )

    def _format_ionocorr_3(self, data: RawNav):
        """
        Format RINEX 3 ionospheric correction blocks.

        RINEX 3 places these as IONOSPHERIC CORR header lines.

        :param RawNav data: data containing ionospheric corrections
        """

        ionocode = RINEXGNSSR[data.gnss][0:2]
        # timemark is tow converted to hour of day
        # and then to A-X character
        tm = chr(int((data.tow % 86400) / 3600) + 65)
        if data.gnss in (GPS, BDS, QZS, IRN):
            self._ionocorr[f"{ionocode}SA"] = format_iono_corr(
                corrtype=f"{ionocode}SA",
                svid=data.svid,
                timemark=tm,
                parm1=data.alpha0,
                parm2=data.alpha1,
                parm3=data.alpha2,
                parm4=data.alpha3,
            )
            self._ionocorr[f"{ionocode}SB"] = format_iono_corr(
                corrtype=f"{ionocode}SB",
                svid=data.svid,
                timemark=tm,
                model=KLOB,
                parm1=data.beta0,
                parm2=data.beta1,
                parm3=data.beta2,
                parm4=data.beta3,
            )
        elif data.gnss == GAL:
            self._ionocorr["GAL"] = format_iono_corr(
                corrtype="GAL",
                svid=data.svid,
                timemark=tm,
                parm1=data.ai0,
                parm2=data.ai1,
                parm3=data.ai2,
                parm4="",
            )

    def _format_ionocorr_4(
        self, msgtype: str, msgsubtype: str, model: str, data: RawNav
    ) -> str:
        """
        Format RINEX 4 ionospheric correction blocks.

        RINEX 4 places these as ION Navigation record types.

        :param str msgtype: message type
        :param str msgsubtype: message subtype
        :param str model: ionospheric model name
        :param RawNav data: data containing ionospheric corrections
        :return: formatted string
        :rtype: str
        """

        epoch, _ = get_epoch(wno=data.wn, tow=data.tow, gnss=data.gnss)
        if model == NEQUICK:
            return format_ion(
                svcode=data.svcode,
                msgtype=msgtype,
                msgsubtype=msgsubtype,
                epoch=epoch,
                model=model,
                a0=data.ai0,
                a1=data.ai1,
                a2=data.ai2,
                region=(data.idf1 << 4)
                | (data.idf2 << 3)
                | (data.idf3 << 2)
                | (data.idf4 << 1)
                | data.idf5,
            )
        return format_ion(
            svcode=data.svcode,
            msgtype=msgtype,
            msgsubtype=msgsubtype,
            epoch=epoch,
            model=model,
            a0=data.alpha0,
            a1=data.alpha1,
            a2=data.alpha2,
            a3=data.alpha3,
            b0=data.beta0,
            b1=data.beta1,
            b2=data.beta2,
            b3=data.beta3,
        )

    def _get_external_epoch(self, rt: str) -> datetime:
        """
        Get epoch from external source (e.g. other NAV
        message in same data stream).

        :param str rt: RINEX observation type (OBS/NAV)
        :return: GNSS epoch
        :rtype: datetime
        """

        return self.__app.get_current_epoch(rt)

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
