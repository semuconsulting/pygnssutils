"""
rinex_conv_obs.py

RINEX Conversion Observation class.

A preliminary implementation of a RINEX observation conversion utility.

Converts UBX RXM-RAWX messages to RINEX Observation text format.

Observation data comprises pseudorange, (carrier) phaserange, Doppler
shift and signal strength.

Functionality will be extended in future versions - contributions welcome.

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

# pylint: disable=fixme

from datetime import datetime
from logging import getLogger
from typing import Any, Literal

from pynmeagps import NMEAMessage, llh2ecef, wnotow2utc
from pyrtcm import RTCMMessage
from pyubx2 import UBXMessage

from pygnssutils.globals import VERBOSITY_MEDIUM
from pygnssutils.rinex_globals import (
    COLWIDTH,
    CONT,
    EVENT_TYPE,
    GLO,
    GPS,
    OBS,
    UBXRINEXGNSS,
)
from pygnssutils.rinex_helpers import (
    FRNX,
    format_antennabsight,
    format_antennadeltahen,
    format_antennadeltaxyz,
    format_antennatype,
    format_antennazerodirazi,
    format_antennazerodirxyz,
    format_approxpos,
    format_centermass,
    format_clockoffset,
    format_cnrunit,
    format_comments,
    format_fileend,
    format_glonassfrq,
    format_glonassphasebias,
    format_headerend,
    format_interval,
    format_leapseconds,
    format_marker,
    format_numsats,
    format_observer,
    format_obstypes,
    format_rcvrtype,
    format_sys_antennaphasecentre,
    format_sys_dcbsapplied,
    format_sys_pcvsapplied,
    format_sys_phaseshift,
    format_sys_scalefactor,
    format_timefirstlast,
    get_obscode,
    get_svcode_ubx,
)


class RinexConverterObservation:
    """
    Rinex Observation Converter Class.
    """

    def __init__(
        self,
        app: Any,
        rinex_version: str,
        gnssfilter: list[str],
        obsfilter: list[str],
        minobs: int,
        datasource: Literal["R", "S", "N", "U"],
        marker: list[str],
        antenna: list[str],
        receiver: list[str],
        observer: str = "",
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
        :param list[str] marker: marker details (name, number, type)
        :param list[str] antenna: antenna details (number, type)
        :param list[str] receiver: receiver details (number, type, version)
        :param str observer: observer details
        :param Literal[-1,0,1,2,3] verbosity: log message verbosity -1 = critical, 0 = error,
            1 = warning, 2 = info, 3 = debug (1)
        :param str logtofile: fully qualified path to logfile ("" = no logfile)
        :param dict kwargs: user-defined keyword arguments to pass to conversion functions
        """

        self.__app = app  # pylint: disable=unused-private-member
        self._gnss_filter = gnssfilter
        self._obscode_filter = obsfilter
        self._datasource = "R" if datasource == "" else datasource
        self._minobs = minobs
        self._marker_name = marker[0] if len(marker) > 0 else ""
        self._marker_num = marker[1] if len(marker) > 1 else ""
        self._marker_type = marker[2] if len(marker) > 2 else ""
        self._antenna_num = antenna[0] if len(antenna) > 0 else ""
        self._antenna_type = antenna[1] if len(antenna) > 1 else ""
        self._rcvr_num = receiver[0] if len(receiver) > 0 else ""
        self._rcvr_type = receiver[1] if len(receiver) > 1 else ""
        self._rcvr_ver = receiver[2] if len(receiver) > 2 else ""
        self._observer = observer
        self.verbosity = int(verbosity)
        self.logtofile = logtofile
        approxpos = kwargs.get("approxpos", "")
        self._approxpos = "" if approxpos == "" else approxpos.split(",")

        # TODO work out any automated or parameterized derivation of variables below...
        self._ant_bsight = ""
        self._ant_deltaen = ""
        self._ant_deltaheight = ""
        self._ant_deltaxyz = ""
        self._ant_phasecentre = ""
        self._ant_zeroazi = ""
        self._ant_zeroxyz = ""
        self._antphasecentres = {}
        centermass = ""
        self._centermass = "" if centermass == "" else centermass.split(",")
        self._clockoffset = ""
        self._dcbs_applied = {}
        self._glonass_ltfrq = {}
        self._numsats = {}
        self._pcvs_applied = {}
        self._phase_shifts = {}
        self._rinex_version = rinex_version
        self._scale_factors = {}
        self._glonass_pb = {"C1C": 0, "C1P": 0, "C2C": 0, "C2P": 0}
        # TODO work out any automated or parameterized derivation of variables above...
        self.logger = getLogger(__name__)
        self._obstypes = {}
        self._obsdata = {}

    def process_input_data(
        self,
        parsed: UBXMessage | RTCMMessage | NMEAMessage,
    ) -> int:
        """
        Process parsed GNSS message(s) containing relevant observation data.

        :param UBXMessage | RTCMMessage | NMEAMessage parsed: parsed message
        :return: number of messages processed
        :rtype: int
        """

        ret = 0
        if isinstance(parsed, UBXMessage):
            if parsed.identity in ("RXM-RAWX", "RXM-RAW"):
                self.convert_ubx_rxmrawx(parsed)
                ret += 1
            if parsed.identity in (
                "NAV-PVT",
                "NAV-POSECEF",
                "NAV-HPPOSECEF",
                "NAV-POSLLH",
                "NAV-HPPOSLLH",
            ):
                self.get_ubx_pos(parsed)
        elif isinstance(parsed, NMEAMessage):
            if parsed.identity[2:] in ("GGA", "GNS"):
                self.get_nmea_pos(parsed)
        return ret

    def process_output_file(self):
        """
        Process RINEX observation file.
        """

        self._format_header()
        self._format_observations(self._obsdata)
        self.__app.output(format_fileend(), OBS)

    def _trim_obstypes(self):
        """
        Remove observation types with less than the minimum required
        number of observations.
        """

        for gnssr, obstypes in self._obstypes.items():
            for obstype, numobs in list(obstypes.items()):
                if numobs < self._minobs:
                    self.logger.debug(
                        f"{gnssr} {obstype} omitted - {numobs} < {self._minobs}"
                    )
                    obstypes.pop(obstype)

    def _format_observation_epoch(
        self,
        epoch: datetime | str,
        numobs: int | str,
        epochflag: int | str = "0",
        clkoffset: float | str = "",
    ) -> str:
        """
        Format observation epoch.

        :param datetime | str epoch: observation epoch or blank if event
        :param int | str numobs: number of observations in this epoch
        :param int | str epochflag: epoch flag
        :param float | str clkoffset: clock offset
        :return: formatted string
        :rtype: str
        """

        nummeas = f"{str(numobs):<2}"
        if clkoffset == 0.0:
            clkoffset = ""
        if epoch == "":  # event
            return f">{'':>39}{epochflag:>3}{numobs:>3}{'':>21}\n"  # A1 ... 2X,I1 I3
        # epoch
        return (
            f">{epoch.year:>5}{epoch.month:>3}{epoch.day:>3}"
            f"{epoch.hour:>3}{epoch.minute:>3}"
            f"{FRNX(epoch.second + epoch.microsecond/1000000,11,7)}"
            f"{epochflag:>3}{nummeas:>3}{'':>6}{FRNX(clkoffset,15,12)}\n"
        )  # A1 1X,I4 4(1X,I2.2) F11.7 2X,I1 I3 6X F15.12

    def _format_observations(self, obsdata: dict[datetime, dict] | str = ""):
        """
        Format observations for each epoch and prn from obsdata dict.

        Format of obsdata dict::

            obsdata = {
                epoch (datetime) : {
                    "epochflag": epochflag (int),
                    "clkoffset": clkoffset (float),
                    "obs": {
                        gnssr+prn (str): {
                            obscode (str): (obs, lli, ssi),
                            obscode (str): (obs, lli, ssi),
                        },
                        ...,
                    },
                },
                ...,
            }

        :param dict[datetime,dict] | str obsdata: observation data dictionary
        """

        if obsdata == "":
            obsdata = {}

        for epoch, data in obsdata.items():
            epoch_flag = data.get("epochflag", 0)
            epoch_clkoffset = data.get("clkoffset", 0.0)
            epoch_obs = data.get("obs", {})
            if epoch_flag in (0, 1, 6):  # observation or (6) cycle slip
                self.__app.output(
                    self._format_observation_epoch(
                        epoch, len(epoch_obs), epoch_flag, epoch_clkoffset
                    ),
                    OBS,
                )
                for svcode, observations in epoch_obs.items():
                    gnssr = svcode[0:1]
                    prn = svcode[1:3]
                    obs = f"{gnssr}{prn:<2}"  # A1 + I2.2
                    for obscode in self._obstypes[gnssr]:
                        ob, lli, ssi = observations.get(obscode, ("", "", ""))
                        obs += f"{FRNX(ob,14,3)}{lli:>1}{ssi:>1}"  # F14.3 + I1 + I1
                    # first observation line
                    self.__app.output(obs[0:COLWIDTH] + "\n", OBS)
                    obs = obs[COLWIDTH:]
                    # any continuation observation lines
                    while len(obs) > 0:
                        wid = COLWIDTH - len(CONT)
                        self.__app.output(CONT + obs[0:wid] + "\n", OBS)
                        obs = obs[wid:]
            elif epoch_flag in (2, 3, 4, 5):  # antenna, site move & external events
                numevents = 0
                self.__app.output(
                    self._format_observation_epoch("", "", epoch_flag, numevents), OBS
                )  # epoch line
                for i in range(numevents):
                    self.__app.output(
                        format_comments(
                            f"{str(i+1):>3} {EVENT_TYPE[epoch_flag].upper()}"
                        ),
                        OBS,
                    )  # TODO work out automated derivation of event markers?

    def _format_header(self):
        """
        Format observation header lines.
        """

        self.logger.debug(f"{self._obstypes=}")

        # redact obstypes with less than the required number of observations
        if self._minobs > 0:
            self._trim_obstypes()

        hdr = (
            self.__app.format_header_common(OBS)
            + format_marker(self._marker_name, self._marker_num, self._marker_type)
            + format_observer(self._observer)
            + format_rcvrtype(self._rcvr_num, self._rcvr_type, self._rcvr_ver)
            + format_antennatype(self._antenna_num, self._antenna_type)
            + format_approxpos(self._approxpos)
            + format_antennadeltahen(self._ant_deltaheight, self._ant_deltaen)
            + format_antennadeltaxyz(self._ant_deltaxyz)
            + format_sys_antennaphasecentre(self._ant_phasecentre)
            + format_antennabsight(self._ant_bsight)
            + format_antennazerodirazi(self._ant_zeroazi)
            + format_antennazerodirxyz(self._ant_zeroxyz)
            + format_centermass(self._centermass)
            + format_obstypes(self._obstypes)
            + format_cnrunit("dbHz")
            + format_interval(self.__app.get_interval(OBS))
            + format_timefirstlast(self.__app.get_start_epoch(OBS), "FIRST")
            + format_timefirstlast(self.__app.get_end_epoch(OBS), "LAST")
            + format_clockoffset(self._clockoffset)
            + format_sys_dcbsapplied(self._dcbs_applied)
            + format_sys_pcvsapplied(self._pcvs_applied)
            + format_sys_scalefactor(self._scale_factors)
            + format_sys_phaseshift(self._phase_shifts)
            + format_glonassfrq(self._glonass_ltfrq)
            + format_glonassphasebias(self._glonass_pb)
            + format_leapseconds(
                self.__app.get_start_epoch(OBS),  # TODO check this is correct date
                self._gnss_filter,
            )
            + format_numsats(len(self._numsats))
            + format_headerend()
        )
        self.__app.output(hdr, OBS)

    def get_ubx_pos(self, data: UBXMessage):
        """
        Get approx marker position from UBX navigation message.

        :param UBXMessage data: parsed UBX message
        """

        try:
            if (
                hasattr(data, "ecefX")
                and hasattr(data, "ecefY")
                and hasattr(data, "ecefZ")
            ):
                # e.g. UBX NAV-POSECEF
                x, y, z = data.ecefX, data.ecefY, data.ecefZ
            else:
                # e.g. UBX NAV-PVT
                lat = data.lat
                lon = data.lon
                hae = 0
                if hasattr(data, "hae"):
                    hae = data.hae
                elif hasattr(data, "height"):
                    hae = data.height
                if lat == "" or lon == "" or hae == "" or (lat == 0 and lon == 0):
                    return
                x, y, z = llh2ecef(lat, lon, hae)
            self._approxpos = [x, y, z]
        except (AttributeError, TypeError) as err:
            raise (err) from err
            # print(f"something went wrong {err}")

    def get_nmea_pos(self, data: NMEAMessage):
        """
        Get approx marker position from NMEA navigation message.

        :param NMEAMessage data: parsed NMEA message
        """

        try:
            lat = data.lat
            lon = data.lon
            alt = data.alt  # hMSL
            sep = data.sep
            if (
                lat == ""
                or lon == ""
                or alt == ""
                or sep == ""
                or (lat == 0 and lon == 0)
            ):
                return
            x, y, z = llh2ecef(lat, lon, alt + sep)
            self._approxpos = [x, y, z]
        except (AttributeError, TypeError) as err:
            raise (err) from err
            # print(f"something went wrong {err}")

    def convert_ubx_rxmrawx(self, data: UBXMessage):
        """
        Extract relevant information from individual GNSS message
        and add to obsdata dictionary, which will be used in the
        _format_observations function to populate the RINEX observation
        output file.

        :param UBXMessage data: parsed UBX RXM-RAWX message
        """

        def geta(att: str, i: int):
            return getattr(data, f"{att}_{i+1:02d}")

        epoch = wnotow2utc(
            wno=data.week, tow=int(data.rcvTow * 1000), ls=None, gnss=GPS, autoroll=True
        )
        if epoch != self.__app.get_current_epoch(OBS):
            self.__app.set_current_epoch(epoch, OBS)
            self._obsdata[epoch] = {}
            self._obsdata[epoch]["epochflag"] = 0
            self._obsdata[epoch]["clkoffset"] = 0.0
            self._obsdata[epoch]["obs"] = {}

        obs = self._obsdata[epoch]["obs"]
        for i in range(data.numMeas):
            gnss = geta("gnssId", i)
            gnssr = UBXRINEXGNSS[gnss]
            if self._obstypes.get(gnssr, None) is None:
                self._obstypes[gnssr] = {}
            sigid = geta("sigId", i)
            svid = geta("svId", i)
            pr = geta("prMes", i)
            cp = geta("cpMes", i)
            do = geta("doMes", i)
            cno = geta("cno", i)
            svcode = get_svcode_ubx(gnss, svid)
            obscode = get_obscode(gnss, sigid)

            # ignore any filtered out gnss
            if self._gnss_filter != [""]:
                if gnssr not in self._gnss_filter:
                    continue

            # ignore any unwanted observation codes
            if self._obscode_filter != [""]:
                if obscode not in self._obscode_filter:
                    continue

            obs[svcode] = obs.get(svcode, {})
            # ssi = get_ssi(cno) # deprecated in 3.05
            lli = 0
            freqid = 0
            if data.identity == "RXM-RAW":
                freqid = 0
                lli = geta("lli", i)
            elif data.identity == "RXM-RAWX":
                freqid = geta("freqId", i) - 7
                # TODO check lli derivation...?
                lli = int(not geta("cpValid", i))

            if gnssr == GLO:  # GLONASS only
                self._glonass_ltfrq[svcode] = freqid

            obs[svcode][f"C{obscode}"] = (pr, "", "")
            obs[svcode][f"L{obscode}"] = (cp, lli, "")
            obs[svcode][f"D{obscode}"] = (do, "", "")
            obs[svcode][f"S{obscode}"] = (cno, "", "")

            self._obstypes[gnssr][f"C{obscode}"] = (
                self._obstypes[gnssr].get(f"C{obscode}", 0) + 1
            )
            self._obstypes[gnssr][f"L{obscode}"] = (
                self._obstypes[gnssr].get(f"L{obscode}", 0) + 1
            )
            self._obstypes[gnssr][f"D{obscode}"] = (
                self._obstypes[gnssr].get(f"D{obscode}", 0) + 1
            )
            self._obstypes[gnssr][f"S{obscode}"] = (
                self._obstypes[gnssr].get(f"S{obscode}", 0) + 1
            )

            self._numsats[svcode] = self._numsats.get(svcode, 0) + 1
