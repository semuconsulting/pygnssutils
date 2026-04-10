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
from typing import Any, Literal

from pynmeagps import NMEAMessage, utc2wnotow, wnotow2utc
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
    SBA,
)
from pygnssutils.rinex_helpers import (
    DRNX,
    format_fileend,
    format_headerend,
    format_interval,
    format_iono_corr,
    format_leapseconds,
    format_nav_epoch,
    format_time_corr,
    format_timefirstlast,
    get_svcode_rtcm,
)
from pygnssutils.rinex_subframes_gps import (
    GPS_LNAV_SUBFRAME_1,
    GPS_LNAV_SUBFRAME_2,
    GPS_LNAV_SUBFRAME_3,
    GPS_LNAV_SUBFRAME_4_P18,
)

CLKBIAS = "clkbias"
CLKDRIFT = "clkdrift"
CLKRATE = "clkrate"
BOD = "bod"
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
        self._navdata = {}
        self._navframes = {}  # holder for acquired partial NAV frames
        # TODO this is a fudge to get contiguous epoch dates from NTRIP RTCM3 data,
        # (epochs derived from individual message wno/tow are variable):
        self._useextepoch = self._datasource == "N"

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
        elif isinstance(parsed, RawNav):
            self._convert_rawnav(parsed)
            res += 1
        elif isinstance(parsed, RTCMMessage):
            if (
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
        self._format_navigations(self._navdata)
        self.__app.output(format_fileend(), NAV)

    def _format_navigations(self, navdata: dict[tuple, dict] | str = ""):
        """
        Format navigation data for each svcode from navdata dict.

        Format of navdata dict::

            navdata = {
                (svcode (str), epoch (datetime)): {
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

        for (svcode, timestamp), data in navdata.items():
            epoch = format_nav_epoch(timestamp)
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
            # just for testing vvvvvv
            # + format_interval(self.__app.get_interval(NAV))
            # + format_timefirstlast(self.__app.get_start_epoch(NAV), "FIRST")
            # + format_timefirstlast(self.__app.get_end_epoch(NAV), "LAST")
            # just for testing ^^^^^^^
            + format_iono_corr(self._ionocorr)
            + format_time_corr(self._timecorr)
            + format_leapseconds(
                self.__app.get_start_epoch(NAV),  # TODO check this is correct date
                self._gnss_filter,
            )
            + format_headerend()
        )
        self.__app.output(hdr, NAV)

    def _convert_rtcm1019(self, data: RTCMMessage):
        """
        Format GPS broadcast orbit blocks.

        :param RTCMMessage data: parsed 1019 GPS Ephemerides message
        """

        # "DF002": "Message Number",
        # "DF009": "GPS Satellite ID",
        # "DF076": "GPS Week Number",
        # "DF077": "GPS SV ACCURACY",
        # "DF078": "GPS CODE ON L2",
        # "DF079": "GPS IDOT Rate of Inclination Angle",
        # "DF071": "GPS IODE Issue of Data (Ephemeris)",
        # "DF081": "GPS toc Reference Time, Clock",
        # "DF082": "GPS af2 Clock correction drift rate",
        # "DF083": "GPS af1 Clock correction drift",
        # "DF084": "GPS af0 Clock correction bias",
        # "DF085": "GPS IODC Issue of Data (Clock)",
        # "DF086": "GPS Crs Amplitude of the Sine Harmonic Correction Term to the Orbit Radius",
        # "DF087": "GPS ∆n Mean Motion Difference from Computed Value",
        # "DF088": "GPS M0 Mean Anomaly at Reference Time",
        # "DF089": "GPS Cuc Amplitude of the Cosine Harmonic Correction Term to the Argument of Latitude",
        # "DF090": "GPS e Eccentricity",
        # "DF091": "GPS Cus Amplitude of the Sine Harmonic Correction Term to the Argument of Latitude",
        # "DF092": "GPS A½ Square Root of the Semi-Major Axis",
        # "DF093": "GPS toe Reference Time Ephemeris",
        # "DF094": "GPS Cic Amplitude of the Cosine Harmonic Correction Term to the Angle of Inclination",
        # "DF095": "GPS Ω0 Longitude of Ascending Node of Orbit Plane at Weekly Epoch",
        # "DF096": "GPS Cis Amplitude of the Sine Harmonic Correction Term to the Angle of Inclination",
        # "DF097": "GPS i0 Inclination Angle at Reference Time",
        # "DF098": "GPS Crc Amplitude of the Cosine Harmonic Correction Term to the Orbit Radius",
        # "DF099": "GPS ω Argument of Perigee",
        # "DF100": "GPS ΩDOT Rate of Right Ascension",
        # "DF101": "GPS tGD",
        # "DF102": "GPS SV HEALTH",
        # "DF103": "GPS L2 P data flag",
        # "DF137": "GPS Fit Interval",

        svcode = get_svcode_rtcm(GPS, data.DF009)
        # TODO how to derive epoch from NTRIP RTCM3 Ephemerides
        # stream? messages to not appear to have time-sequential
        # wno + toe or toc, or even use UTC, so wnotow2utc gives odd results
        if self._useextepoch:
            epoch = self._get_external_epoch(NAV)
            _, tom, _ = utc2wnotow(epoch, GPS)
            tom = int(tom / 1000)
        else:
            epoch = self._get_local_epoch(data.DF076, data.DF093, GPS)
            tom = data.DF093
        if epoch == EPOCHMIN:
            return
        self._navdata[(svcode, epoch)] = {}
        nvd = self._navdata[(svcode, epoch)]

        nvd[CLKBIAS] = data.DF084  # clock bias
        nvd[CLKDRIFT] = data.DF083  # clock drift
        nvd[CLKRATE] = data.DF082  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.DF071  # - IODnav Issue of Data of the nav batch
        nvb[0][1] = data.DF086  # - Crs (meters)
        nvb[0][2] = data.DF087  # - Delta n (radians/sec)
        nvb[0][3] = data.DF088  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF089  # - Cuc (radians)
        nvb[1][1] = data.DF090  # - e Eccentricity
        nvb[1][2] = data.DF091  # - Cus (radians)
        nvb[1][3] = data.DF092  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF093  # - Toe Time of Ephemeris (sec of GAL week)
        nvb[2][1] = data.DF094  # - Cic (radians)
        nvb[2][2] = data.DF095  # - OMEGA0 (radians)
        nvb[2][3] = data.DF096  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF097  # - i0 (radians)
        nvb[3][1] = data.DF098  # - Crc (meters)
        nvb[3][2] = data.DF099  # - omega (radians)
        nvb[3][3] = data.DF100  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF079  # - IDOT (radians/sec)
        nvb[4][1] = data.DF078  # - codes on L2 channel
        nvb[4][2] = data.DF076  # - GPS Week # (to go with TOE)
        nvb[4][3] = data.DF103  # - L2 P data flag
        # BROADCAST ORBIT - 6
        nvb[5][0] = data.DF077  # - SV accuracy (meters)
        nvb[5][1] = data.DF102  # - SV health
        nvb[5][2] = data.DF101  # - TGD (seconds)
        nvb[5][3] = data.DF085  # - IODC, clock
        # BROADCAST ORBIT - 7
        nvb[6][0] = tom
        nvb[6][1] = data.DF137  # - Fit Interval (0/1) TODO convert to hours?
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

    def _convert_rtcm1020(self, data: RTCMMessage):
        """
        Format GLONASS broadcast orbit blocks.

        :param RTCMMessage data: parsed 1020 GLONASS Ephemerides message
        """

        # "DF002": "Message Number",
        # "DF038": "GLONASS Satellite ID (Satellite Slot Number)",
        # "DF040": "GLONASS Satellite Frequency Channel Number",
        # "DF104": "GLONASS almanac health (Cn word)",
        # "DF105": "GLONASS almanac health availability indicator",
        # "DF106": "GLONASS P1",
        # "DF107": "GLONASS tk",
        # "DF108": "GLONASS MSB of Bn word",
        # "DF109": "GLONASS P2",
        # "DF110": "GLONASS tb",
        # "DF111": "GLONASS xn(tb), first derivative",
        # "DF112": "GLONASS xn(tb)",
        # "DF113": "GLONASS xn(tb), second derivative",
        # "DF114": "GLONASS yn(tb), first derivative",
        # "DF115": "GLONASS yn(tb)",
        # "DF116": "GLONASS yn(tb), second derivative",
        # "DF117": "GLONASS zn(tb), first derivative",
        # "DF118": "GLONASS zn(tb)",
        # "DF119": "GLONASS zn(tb), second derivative",
        # "DF120": "GLONASS P3",
        # "DF121": "GLONASS γn(tb)",
        # "DF122": "GLONASS-M P",
        # "DF123": "GLONASS-M ln (third string)",
        # "DF124": "GLONASS τn(tb)",
        # "DF125": "GLONASS-M Δτn" L1/L2 group delay,
        # "DF126": "GLONASS En Age of Data",
        # "DF127": "GLONASS-M P4",
        # "DF128": "GLONASS-M FT",
        # "DF129": "GLONASS-M NT",
        # "DF130": "GLONASS-M M",
        # "DF131": "GLONASS The Availability of Additional Data",
        # "DF132": "GLONASS NA calendar day number",
        # "DF133": "GLONASS τc",
        # "DF134": "GLONASS-M N4",
        # "DF135": "GLONASS-M τGPS",
        # "DF136": "GLONASS-M ln (fifth string)",
        # "DF001_7": "Reserved",

        svcode = get_svcode_rtcm(GLO, data.DF038)
        if self._useextepoch:
            epoch = self._get_external_epoch(NAV)
        else:  # TODO
            epoch = self._get_external_epoch(NAV)
        if epoch == EPOCHMIN:  # epoch not yet established
            return
        self._navdata[(svcode, epoch)] = {}
        nvd = self._navdata[(svcode, epoch)]

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

        :param RTCMMessage data: parsed 1045 Galileo Ephemerides message
        """

        # 1045 F/NAV:
        # "DF002": "Message Number",
        # "DF252": "Galileo Satellite ID",
        # "DF289": "Galileo Week Number",
        # "DF290": "Galileo IODnav",
        # "DF291": "Galileo SV SISA",
        # "DF292": "Galileo Rate of Inclination (IDOT)",
        # "DF293": "Galileo toc",
        # "DF294": "Galileo af2",
        # "DF295": "Galileo af1",
        # "DF296": "Galileo af0",
        # "DF297": "Galileo Crs",
        # "DF298": "Galileo ∆n",
        # "DF299": "Galileo M0",
        # "DF300": "Galileo Cuc",
        # "DF301": "Galileo Eccentricity (e)",
        # "DF302": "Galileo Cus",
        # "DF303": "Galileo A½",
        # "DF304": "Galileo toe",
        # "DF305": "Galileo Cic",
        # "DF306": "Galileo Ω0",
        # "DF307": "Galileo Cis",
        # "DF308": "Galileo i0",
        # "DF309": "Galileo Crc",
        # "DF310": "Galileo ω",
        # "DF311": "Galileo ΩDOT",
        # "DF312": "Galileo BGD (E1/E5a)",
        # "DF314": "Galileo E5a Signal Health Status (OSHS)",
        # "DF315": "Galileo E5a Data Validity Status (OSDVS)",
        # "DF001_7": "Reserved",

        svcode = get_svcode_rtcm(GAL, data.DF252)
        if self._useextepoch:
            epoch = self._get_external_epoch(NAV)
            _, tom, _ = utc2wnotow(epoch, GAL)
            tom = int(tom / 1000)
        else:
            epoch = self._get_local_epoch(data.DF289, data.DF304, GAL)
            tom = data.DF304
        if epoch == EPOCHMIN:
            return
        self._navdata[(svcode, epoch)] = {}
        nvd = self._navdata[(svcode, epoch)]

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
        nvb[0][2] = data.DF298  # - Delta n (radians/sec)
        nvb[0][3] = data.DF299  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF300  # - Cuc (radians)
        nvb[1][1] = data.DF301  # - e Eccentricity
        nvb[1][2] = data.DF302  # - Cus (radians)
        nvb[1][3] = data.DF303  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF304  # - Toe Time of Ephemeris (sec of GAL week)
        nvb[2][1] = data.DF305  # - Cic (radians)
        nvb[2][2] = data.DF306  # - OMEGA0 (radians)
        nvb[2][3] = data.DF307  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF308  # - i0 (radians)
        nvb[3][1] = data.DF309  # - Crc (meters)
        nvb[3][2] = data.DF310  # - omega (radians)
        nvb[3][3] = data.DF311  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF292  # - IDOT (radians/sec)
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

        :param RTCMMessage data: parsed 1046 Galileo Ephemerides message
        """

        # 1046 I/NAV:
        # "DF002": "Message Number",
        # "DF252": "Galileo Satellite ID",
        # "DF289": "Galileo Week Number",
        # "DF290": "Galileo IODnav",
        # "DF286": "Galileo SISA Index (E1,E5b)",
        # "DF292": "Galileo Rate of Inclination (IDOT)",
        # "DF293": "Galileo toc",
        # "DF294": "Galileo af2",
        # "DF295": "Galileo af1",
        # "DF296": "Galileo af0",
        # "DF297": "Galileo Crs",
        # "DF298": "Galileo ∆n",
        # "DF299": "Galileo M0",
        # "DF300": "Galileo Cuc",
        # "DF301": "Galileo Eccentricity (e)",
        # "DF302": "Galileo Cus",
        # "DF303": "Galileo A½",
        # "DF304": "Galileo toe",
        # "DF305": "Galileo Cic",
        # "DF306": "Galileo Ω0",
        # "DF307": "Galileo Cis",
        # "DF308": "Galileo i0",
        # "DF309": "Galileo Crc",
        # "DF310": "Galileo ω",
        # "DF311": "Galileo ΩDOT",
        # "DF312": "Galileo BGD (E1/E5a)",
        # "DF313": "Galileo BGD (E5b,E1)",
        # "DF316": "Galileo E5b Signal Health Status",
        # "DF317": "Galileo E5b Data Validity Status",
        # "DF287": "Galileo E1b Signal Health Status",
        # "DF288": "Galileo E1b Data Validity Status",
        # "DF001_2": "Reserved",

        svcode = get_svcode_rtcm(GAL, data.DF252)
        if self._useextepoch:
            epoch = self._get_external_epoch(NAV)
            _, tom, _ = utc2wnotow(epoch, GAL)
            tom = int(tom / 1000)
        else:
            epoch = self._get_local_epoch(data.DF289, data.DF304, GAL)
            tom = data.DF304
        if epoch == EPOCHMIN:
            return
        self._navdata[(svcode, epoch)] = {}
        nvd = self._navdata[(svcode, epoch)]

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
        nvb[0][2] = data.DF298  # - Delta n (radians/sec)
        nvb[0][3] = data.DF299  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF300  # - Cuc (radians)
        nvb[1][1] = data.DF301  # - e Eccentricity
        nvb[1][2] = data.DF302  # - Cus (radians)
        nvb[1][3] = data.DF303  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF304  # - Toe Time of Ephemeris (sec of GAL week)
        nvb[2][1] = data.DF305  # - Cic (radians)
        nvb[2][2] = data.DF306  # - OMEGA0 (radians)
        nvb[2][3] = data.DF307  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF308  # - i0 (radians)
        nvb[3][1] = data.DF309  # - Crc (meters)
        nvb[3][2] = data.DF310  # - omega (radians)
        nvb[3][3] = data.DF311  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF292  # - IDOT (radians/sec)
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

        :param RTCMMessage data: parsed 1042 Beidou Ephemerides message
        """

        # "DF002": "Message Number",
        # "DF488": "BDS Satellite ID",
        # "DF489": "BDS Week Number",
        # "DF490": "BDS URAI",
        # "DF491": "BDS IDOT",
        # "DF492": "BDS AODE",
        # "DF493": "BDS Toc",
        # "DF494": "BDS a2",
        # "DF495": "BDS a1",
        # "DF496": "BSD a0",
        # "DF497": "BDS AODC",
        # "DF498": "BDS Crs",
        # "DF499": "BDS ∆n",
        # "DF500": "BDS M0",
        # "DF501": "BDS Cuc",
        # "DF502": "BDS e",
        # "DF503": "BDS Cus",
        # "DF504": "BDS A½",
        # "DF505": "BDS Toe",
        # "DF506": "BDS Cic",
        # "DF507": "BDS Ω0",
        # "DF508": "BDS Cis",
        # "DF509": "BDS i0",
        # "DF510": "BDS Crc",
        # "DF511": "BDS ω",
        # "DF512": "BDS ΩDOT",
        # "DF513": "BDS TGD1",
        # "DF514": "BDS TGD2",
        # "DF515": "BSD SV Health SATH1",

        svcode = get_svcode_rtcm(BDS, data.DF488)
        if self._useextepoch:
            epoch = self._get_external_epoch(NAV)
            _, tom, _ = utc2wnotow(epoch, BDS)
            tom = int(tom / 1000)
        else:
            epoch = self._get_local_epoch(data.DF489, data.DF505, BDS)
            tom = data.DF505
        if epoch == EPOCHMIN:
            return
        self._navdata[(svcode, epoch)] = {}
        nvd = self._navdata[(svcode, epoch)]

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
        nvb[0][2] = data.DF499  # - Delta n (radians/sec)
        nvb[0][3] = data.DF500  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF501  # - Cuc (radians)
        nvb[1][1] = data.DF502  # - e Eccentricity
        nvb[1][2] = data.DF503  # - Cus (radians)
        nvb[1][3] = data.DF504  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF505  # - Toe Time of Ephemeris (sec of BDT week)
        nvb[2][1] = data.DF506  # - Cic (radians)
        nvb[2][2] = data.DF507  # - OMEGA0 (radians)
        nvb[2][3] = data.DF508  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF509  # - i0 (radians)
        nvb[3][1] = data.DF510  # - Crc (meters)
        nvb[3][2] = data.DF511  # - omega (radians)
        nvb[3][3] = data.DF512  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF491  # - IDOT (radians/sec)
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

        :param RTCMMessage data: parsed 1044 QZSS Ephemerides message
        """

        # "DF002": "Message Number",
        # "DF429": "QZSS Satellite ID",
        # "DF430": "QZSS toc",
        # "DF431": "QZSS af2",
        # "DF432": "QZSS af1",
        # "DF433": "QZSS af0",
        # "DF434": "QZSS IODE",
        # "DF435": "QZSS Crs",
        # "DF436": "QZSS ∆n",
        # "DF437": "QZSS M0",
        # "DF438": "QZSS Cuc",
        # "DF439": "QZSS e",
        # "DF440": "QZSS Cus",
        # "DF441": "QZSS A½",
        # "DF442": "QZSS toe",
        # "DF443": "QZSS Cic",
        # "DF444": "QZSS Ω0",
        # "DF445": "QZSS Cis",
        # "DF446": "QZSS i0",
        # "DF447": "QZSS Crc",
        # "DF448": "QZSS ω",
        # "DF449": "QZSS Ω0n DOT",
        # "DF450": "QZSS i0-DOT",
        # "DF451": "QZSS Codes on L2 Channel",
        # "DF452": "QZSS Week Number",
        # "DF453": "QZSS URA",
        # "DF454": "QZSS SV health",
        # "DF455": "QZSS TGD",
        # "DF456": "QZSS IODC",
        # "DF457": "QZSS Fit Interval",

        svcode = get_svcode_rtcm(QZS, data.DF429)
        if self._useextepoch:
            epoch = self._get_external_epoch(NAV)
            _, tom, _ = utc2wnotow(epoch, QZS)
            tom = int(tom / 1000)
        else:
            epoch = self._get_local_epoch(data.DF452, data.DF442, QZS)
            tom = data.DF442
        if epoch == EPOCHMIN:
            return
        self._navdata[(svcode, epoch)] = {}
        nvd = self._navdata[(svcode, epoch)]

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
        nvb[0][2] = data.DF436  # - Delta n (radians/sec)
        nvb[0][3] = data.DF437  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF438  # - Cuc (radians)
        nvb[1][1] = data.DF439  # - e Eccentricity
        nvb[1][2] = data.DF440  # - Cus (radians)
        nvb[1][3] = data.DF441  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF442  # - Toe Time of Ephemeris (sec of GAL week)
        nvb[2][1] = data.DF443  # - Cic (radians)
        nvb[2][2] = data.DF444  # - OMEGA0 (radians)
        nvb[2][3] = data.DF445  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF446  # - i0 (radians)
        nvb[3][1] = data.DF447  # - Crc (meters)
        nvb[3][2] = data.DF448  # - omega (radians)
        nvb[3][3] = data.DF449  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF450  # - IDOT (radians/sec)
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

    def _convert_navsource_sbas(self, data: RTCMMessage):
        """
        Format SBAS broadcast orbit blocks.

        :param RTCMMessage data: parsed SBAS Ephemerides message
        """

        svcode = get_svcode_rtcm(SBA, data.DF009)
        if self._useextepoch:
            epoch = self._get_external_epoch(NAV)
        else:
            epoch = self._get_local_epoch(data.wno, data.tow, SBA)
        if epoch == EPOCHMIN:
            return
        # self.__app.set_current_epoch(epoch, NAV)
        self._navdata[(svcode, epoch)] = {}
        nvd = self._navdata[(svcode, epoch)]

        nvd[CLKBIAS] = data.a0  # clock bias
        nvd[CLKDRIFT] = data.a1  # clock drift
        nvd[CLKRATE] = data.a2  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(3):  # broadcast orbit data blocks * 3
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.posX  # - Satellite position X (km)
        nvb[0][1] = data.velX  # - velocity X dot (km/sec)
        nvb[0][2] = data.accX  # - X acceleration (km/sec2)
        nvb[0][3] = data.svhealth  # - health (0=healthy, 1=unhealthy) (MSB of 3-bit Bn)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.posY  # - Satellite position Y (km)
        nvb[1][1] = data.velY  # - velocity Y dot (km/sec)
        nvb[1][2] = data.accY  # - Y acceleration (km/sec2)
        nvb[1][3] = data.ura  # - Accuracy code (URA, meters)
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.posZ  # - Satellite position Z (km)
        nvb[2][1] = data.velZ  # - velocity Z dot (km/sec)
        nvb[2][2] = data.accZ  # - Z acceleration (km/sec2)
        nvb[2][3] = data.iodn  # - IODN (Issue of Data Navigation

    def _convert_rtcm1041(self, data: RTCMMessage):
        """
        Format NavIC broadcast orbit blocks.

        :param RTCMMessage data: parsed 1041 NavIC Ephemerides message
        """

        # "DF002": "Message Number",
        # "DF516": "NavIC/IRNSS Satellide ID",
        # "DF517": "Week Number (WN)",
        # "DF518": "Clock bias (af0)",
        # "DF519": "Clock drift (af1",
        # "DF520": "Clock drift rate (af2)",
        # "DF521": "SV Accuracy (URA)",
        # "DF522": "Time of clock (toc)",
        # "DF523": "Total Group Delay (TGD)",
        # "DF524": "Mean Motion Difference (∆n)",
        # "DF525": "Issue of Data Ephemeris & Clock (IODEC)",
        # "DF526": "Reserved bits after IODEC",
        # "DF527": "L5 Flag",
        # "DF528": "S Flag",
        # "DF529": "Cuc",
        # "DF530": "Cus",
        # "DF531": "Cic",
        # "DF532": "Cis",
        # "DF533": "Crc",
        # "DF534": "Crs",
        # "DF535": "Rate of Inclination angle (IDOT)",
        # "DF536": "Mean Anomaly (M0)",
        # "DF537": "Time of ephemeris (tOE)",
        # "DF538": "Eccentricity (e)",
        # "DF539": "Square root of Semi major axis (√A)",
        # "DF540": "Long of Ascending Node (Ω0)",
        # "DF541": "Argument of perigee (ω)",
        # "DF542": "Rate of RAAN (ΩDOT)",
        # "DF543": "Inclination (i0)",
        # "DF544": "2 spare bits after IDOT",
        # "DF545": "2 spare bits after i0",

        svcode = get_svcode_rtcm(IRN, data.DF516)
        if self._useextepoch:
            epoch = self._get_external_epoch(NAV)
            _, tom, _ = utc2wnotow(epoch, IRN)
            tom = int(tom / 1000)
        else:
            epoch = self._get_local_epoch(data.DF517, data.DF537, IRN)
            tom = data.DF537
        if epoch == EPOCHMIN:
            return
        # self.__app.set_current_epoch(epoch, NAV)
        self._navdata[(svcode, epoch)] = {}
        nvd = self._navdata[(svcode, epoch)]

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
        nvb[0][2] = data.DF524  # - Delta n (radians/sec)
        nvb[0][3] = data.DF536  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.DF529  # - Cuc (radians)
        nvb[1][1] = data.DF538  # - e Eccentricity
        nvb[1][2] = data.DF530  # - Cus (radians)
        nvb[1][3] = data.DF539  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.DF537  # - Toe Time of Ephemeris (sec of NAVIC week)
        nvb[2][1] = data.DF531  # - Cic (radians)
        nvb[2][2] = data.DF540  # - OMEGA0 (radians)
        nvb[2][3] = data.DF532  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.DF543  # - i0 (radians)
        nvb[3][1] = data.DF533  # - Crc (meters)
        nvb[3][2] = data.DF541  # - omega (radians)
        nvb[3][3] = data.DF542  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.DF535  # - IDOT (radians/sec)
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

    def _convert_rxmsfrbx(self, data: UBXMessage):
        """
        Process UBX RXM-SFRBX raw NAV subframe messages
        using RawNav utility method.

        :param UBXMessage data: UBX RXM-SFRBX message
        """

        sfrdata = RawNav.process_rxm_sfrbx(data)
        if sfrdata.get("gnss", "") != GPS or sfrdata.get("sigid", "") not in ("1C",):
            return

        gnss = sfrdata["gnss"]
        svid = sfrdata["svid"]
        sigid = sfrdata["sigid"]
        subframeid = sfrdata["subframeid"]
        tow = sfrdata["tow"]
        svcode = sfrdata.get("svcode", 0)
        subframe = sfrdata["subframe"]

        try:
            nominal_epoch = RawNav.get_nominal_epoch(gnss, tow)
            self._navframes[(gnss, svid, sigid)] = self._navframes.get(
                (gnss, svid, sigid), RawNav(gnss, svid, sigid, nominal_epoch)
            )
            nav = self._navframes[(gnss, svid, sigid)]
            if subframeid == 1:  # clock parameters, sv health, etc.
                nav.parse(subframe, GPS_LNAV_SUBFRAME_1)
            elif subframeid == 2:  # ephemerides
                nav.parse(subframe, GPS_LNAV_SUBFRAME_2)
            elif subframeid == 3:  # ephemerides
                nav.parse(subframe, GPS_LNAV_SUBFRAME_3)
            elif subframeid == 4:
                if svcode == 56:  # page 18, ionospheric corrections
                    navit = RawNav(gnss, svid, sigid, nominal_epoch)
                    navit.parse(subframe, GPS_LNAV_SUBFRAME_4_P18)
                    self._convert_ionocorr(navit)
                    self._convert_timecorr(navit)
            if nav.sfracq == TARGET_SFR:
                self._convert_rawnav(self._navframes.pop((gnss, svid, sigid)))
        except RINEXProcessingError as err:
            raise RINEXProcessingError("Error process RXM-SFRBX data") from err

    def _convert_rawnav(self, data: RawNav):
        """
        Format RawNav broadcast orbit blocks.

        :param RawNav data: RawNav object containing data \
            collated from UBX RXM-SFRBX messages or other \
            raw NAV subframe sources.
        """

        svcode = get_svcode_rtcm(data.gnss, data.svid)
        epoch = data.epoch
        if epoch == EPOCHMIN:
            return
        self.__app.set_current_epoch(epoch, NAV)
        self._navdata[(svcode, epoch)] = {}
        nvd = self._navdata[(svcode, epoch)]

        nvd[CLKBIAS] = data.af0  # clock bias
        nvd[CLKDRIFT] = data.af1  # clock drift
        nvd[CLKRATE] = data.af2  # clock drift rate
        nvd[BOD] = []
        nvb = nvd[BOD]
        for _ in range(7):  # broadcast orbit data blocks * 7
            nvb.append(["", "", "", ""])  # 4X,4D19.12
        # BROADCAST ORBIT - 1
        nvb[0][0] = data.iode  # - Issue of Data, Ephemeris and Clock
        nvb[0][1] = data.crs  # - Crs (meters)
        nvb[0][2] = data.deltan  # - Delta n (radians/sec)
        nvb[0][3] = data.m0  # - M0 (radians)
        # BROADCAST ORBIT - 2
        nvb[1][0] = data.cuc  # - Cuc (radians)
        nvb[1][1] = data.e  # - e Eccentricity
        nvb[1][2] = data.cus  # - Cus (radians)
        nvb[1][3] = data.sqrta  # - sqrt(a) (sqrt(m))
        # BROADCAST ORBIT - 3
        nvb[2][0] = data.toe  # - Toe Time of Ephemeris (sec of NAVIC week)
        nvb[2][1] = data.cic  # - Cic (radians)
        nvb[2][2] = data.omega0  # - OMEGA0 (radians)
        nvb[2][3] = data.cis  # - Cis (radians)
        # BROADCAST ORBIT - 4
        nvb[3][0] = data.i0  # - i0 (radians)
        nvb[3][1] = data.crc  # - Crc (meters)
        nvb[3][2] = data.omega  # - omega (radians)
        nvb[3][3] = data.omegadot  # - OMEGA DOT (radians/sec)
        # BROADCAST ORBIT - 5
        nvb[4][0] = data.idot  # - IDOT (radians/sec)
        nvb[4][1] = ""  # Spare
        nvb[4][2] = data.wn  # - week number (to go with toe)
        nvb[4][3] = ""  # - Spare
        # BROADCAST ORBIT - 6
        nvb[5][0] = data.ura  # - User Range Accuracy (metres)
        nvb[5][1] = data.svhealth  # - SV health (FLOAT → INTEGER)
        nvb[5][2] = data.tgd  # - TGD (seconds)
        nvb[5][3] = ""  # - Spare
        # BROADCAST ORBIT - 7
        nvb[6][0] = data.tow
        nvb[6][1] = ""  # - Spare
        nvb[6][2] = ""  # - Spare
        nvb[6][3] = ""  # - Spare

    def _convert_ionocorr(self, data: Any):
        """
        Format ionospheric correction header blocks.

        :param Any data: data containing ionospheric corrections
        """

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

    def _convert_timecorr(self, data: Any):
        """
        Format time correction header blocks.

        :param Any data: data containing time corrections
        """

        self._timecorr["GPUT"] = {
            "a0": data.a0,
            "a1": data.a1,
            "timeref": data.tot,
            "weekno": data.wnt,
            "svcode": f"{data.gnss}{data.svcode:02d}",
            "source": 0,
        }

    def _get_external_epoch(self, rt: str) -> datetime:
        """
        Get epoch from external source (e.g. other NAV
        message in same data stream).

        :param str rt: RINEX observation type (OBS/NAV)
        :return: epoch
        :rtype: datetime
        """

        return self.__app.get_current_epoch(rt)

    def _get_local_epoch(
        self, wno: int, toe: int, gnss: Literal["G", "E", "C", "J", "I"]
    ) -> datetime:
        """
        Get epoch from message wno, toe.

        :param int wno: week number in GNSS time system
        :param int toe: time of week (ephemeris) in GNSS time system
        :param Literal["G","E","C","J","I"] gnss: GNSS time system to use
        :return: epoch
        :rtype: datetime
        """

        epoch = wnotow2utc(wno, int(toe * 1000), None, gnss)
        self.__app.set_current_epoch(epoch, NAV)
        self.logger.debug(f"{gnss} epoch: {epoch}")
        return epoch

    def _get_rmc_epoch(self, data: NMEAMessage):
        """
        Get current epoch from NMEA RMC navigation message
        in same data stream.

        :param NMEAMessage data: parsed NMEA message
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
        except (AttributeError, TypeError) as err:
            print(f"something went wrong {err}")
