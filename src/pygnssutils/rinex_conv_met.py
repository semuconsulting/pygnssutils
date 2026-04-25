"""
rinex_conv_met.py

RINEX Conversion Meterology class.

A preliminary implementation of a RINEX meteorology conversion utility.

Converts NMEA MWD and XDR messages to RINEX Meteorology text format.

Meteorology data comprises meteorological sensor readings such as temperature,
pressure, wind speed and direction, rain levels, etc.

Functionality may be extended in future versions - contributions welcome.

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

from datetime import datetime, timezone
from logging import getLogger
from typing import Any, Literal

from pynmeagps import NMEAMessage
from pyrtcm import RTCMMessage
from pyubx2 import UBXMessage

from pygnssutils.globals import VERBOSITY_MEDIUM
from pygnssutils.rinex_globals import BDS, COLWIDTH, EPOCHMIN, MET
from pygnssutils.rinex_helpers import (
    FRNX,
    format_fileend,
    format_headerend,
    format_marker,
    format_met_obstypes,
    format_met_sensorpos,
    format_met_sensortype,
    format_nav_epoch,
)


class RinexConverterMeteorology:
    """
    Rinex Meteorology Converter Class.
    """

    def __init__(
        self,
        app: Any,
        rinex_version: str,
        gnssfilter: list[str],
        obsfilter: list[str],
        datasource: Literal["R", "S", "N", "U"],
        minobs: int,
        marker: list[str],
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
        :param Literal["R","S","N","U"] source: data source (R)
        :param int minobs: Minimum observations per observation type (10)
        :param list[str] | str marker: marker details (name, number, type)
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
        self.verbosity = int(verbosity)
        self.logtofile = logtofile
        self._marker_name = marker[0] if len(marker) > 0 else ""
        self._marker_num = marker[1] if len(marker) > 1 else ""
        self._marker_type = marker[2] if len(marker) > 2 else ""
        self._sensorpos = ""
        self._obstype = ""
        self._rinex_version = rinex_version

        self.logger = getLogger(__name__)
        self._sensortypes = {}
        self._metdata = {}

    def process_input_data(
        self,
        parsed: UBXMessage | RTCMMessage | NMEAMessage,
    ) -> int:
        """
        Process parsed GNSS message(s) containing relevant meteorology data.

        :param UBXMessage | RTCMMessage | NMEAMessage parsed: parsed message
        :return: number of messages processed
        :rtype: int
        """

        ret = 0
        if isinstance(parsed, NMEAMessage):
            if parsed.identity[2:] in ("RMC"):
                self.get_nmea_epoch(parsed)
            if parsed.identity[2:] in ("MWD"):  # NMEA Wind Speed and Direction
                self.convert_nmea_mwd(parsed)
                ret += 1
            if parsed.identity[2:] in ("XDR"):  # NMEA Transducer (Temp & Pressure)
                self.convert_nmea_xdr(parsed)
                ret += 1
        # ADD ADDITIONAL PARSED DATA SOURCES HERE...
        return ret

    def process_output_file(self):
        """
        Process RINEX meteorology file.
        """

        self._format_header()
        self._format_meteorology(self._metdata)
        self.__app.output(format_fileend(), MET)

    def _format_meteorology(self, metdata: dict[datetime, dict] | str = ""):
        """
        Format meteorology data for each epoch from metdata dict.

        Format of metdata dict::

            metdata = {
                epoch (datetime): {
                    obscode1 (str) : sensorval1 (float), # in same order as self._sensortypes
                    obscode2 (str) : sensorval2 (float)
                    obscode3 (str) : sensorval3 (float)
                    ...
                },
                ...
            }

        :param dict[datetime, dict] | str metdata: met sensor data dictionary
        """

        if metdata == "":
            metdata = {}

        # 1X,I4.4, 5(1X,I2), mF7.1 4X,10F7.1
        for epoch, sensors in metdata.items():
            numobs = len(sensors)
            epochf = format_nav_epoch(epoch)
            ps = f" {epochf}"
            for i, obscode in enumerate(self._sensortypes):
                sensorval = sensors.get(obscode, "")
                #     obs += f"{ob:>16}"  # F14.3 + I1 + I1
                # for i, sensorval in enumerate(sensors):
                ps += f"{FRNX(sensorval,7,1)}"
                if len(ps) > COLWIDTH - 7 or i == numobs - 1:
                    self.__app.output(f"{ps}\n", MET)
                    ps = f"{'':<4}"

    def _format_header(self):
        """
        Format meteorology header lines.

        Format of sensortypes dict::

            sensortypes = {
                obstype (str): {
                    "senstyp" : sensor type (str)
                    "sensmod" : sensor model (str)
                    "accuracy" : sensor accuracy (float)
                    "count": number of observations for this type (int)
                },
                ...
            }
        """

        hdr = (
            self.__app.format_header_common(MET)
            + format_marker(self._marker_name, self._marker_num, self._marker_type)
            + format_met_obstypes(self._sensortypes)
            + format_met_sensortype(self._sensortypes)
        )
        if "PR" in self._sensortypes:  # only output for pressure observations
            hdr += format_met_sensorpos(self._sensorpos, self._obstype)
        hdr += format_headerend()
        self.__app.output(hdr, MET)

    def convert_nmea_mwd(self, data: NMEAMessage):
        """
        Extract relevant information from NMEA MDW GNSS message.

        See RINEX_METOBS for list of supported met observation types.

        :param NMEAMessage data: parsed NMEA MWD message
        """

        try:
            # NB: NMEA MWD sentence has no timestamp, so epoch must be
            # obtained from another NMEA RMC message in the same data stream
            epoch = self.__app.current_epoch
            if epoch == EPOCHMIN:  # epoch not yet established
                return
            winddir = data.dirM
            windspd = data.speedM
            self._metdata[epoch] = self._metdata.get(epoch, {})
            self._metdata[epoch]["WD"] = winddir
            self._metdata[epoch]["WS"] = windspd
            for obscode in ("WD", "WS"):
                self._sensortypes[obscode] = self._sensortypes.get(obscode, {})
                self._sensortypes[obscode]["sensmod"] = self._sensortypes[obscode].get(
                    "senmod", "N/A"
                )
                self._sensortypes[obscode]["senstyp"] = self._sensortypes[obscode].get(
                    "sentyp", "NMEA MWD"
                )
                self._sensortypes[obscode]["accuracy"] = self._sensortypes[obscode].get(
                    "accuracy", "0"
                )
                self._sensortypes[obscode]["count"] = (
                    self._sensortypes[obscode].get("count", 0) + 1
                )
        except (AttributeError, TypeError) as err:
            print(f"something went wrong {err}")

    def convert_nmea_xdr(self, data: NMEAMessage):
        """
        Extract relevant information from NMEA XDR GNSS message.

        See RINEX_METOBS for list of supported met observation types.

        (NB: some proprietary XDR implementations use non-standard unit
        of measurement codes which are not in the public domain)

        :param NMEAMessage data: parsed NMEA XDR message
        """

        def geta(att: str, i: int):
            return getattr(data, f"{att}_{i+1:02d}")

        try:
            # NB: NMEA XDR sentence has no timestamp, so epoch must be
            # obtained from another NMEA RMC message in the same data stream
            epoch = self.__app.current_epoch
            if epoch == EPOCHMIN:  # epoch not yet established
                return
            self._metdata[epoch] = self._metdata.get(epoch, {})
            i = 0
            while True:
                try:
                    tdrtype = geta("tdrtype", i)
                    tdrunit = geta("dataunit", i)
                    tdrdata = geta("data", i)
                    tdrid = geta("tdrid", i)
                    obscode = ""
                    if tdrunit == "B":  # Bar
                        obscode = "PR"  # pressure
                        self._metdata[epoch][obscode] = float(tdrdata) * 1000  # mBar
                    elif tdrunit == "P":  # Pascal
                        obscode = "PR"  # pressure
                        self._metdata[epoch][obscode] = float(tdrdata) / 100  # mBar
                    elif tdrunit == BDS:  # Degrees Celcius
                        obscode = "TD"  # temperature
                        self._metdata[epoch][obscode] = float(tdrdata)
                    if obscode != "":
                        self._sensortypes[obscode] = {}
                        self._sensortypes[obscode]["senstyp"] = tdrtype
                        self._sensortypes[obscode]["sensmod"] = tdrid
                        self._sensortypes[obscode]["accuracy"] = 0
                        self._sensortypes[obscode]["count"] = (
                            self._sensortypes[obscode].get("count", 0) + 1
                        )
                    i += 1
                except AttributeError:
                    break

        except (AttributeError, TypeError) as err:
            print(f"something went wrong {err}")

    def get_nmea_epoch(self, data: NMEAMessage):
        """
        Get current epoch from NMEA RMC navigation message.

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
            self.__app.set_current_epoch(epoch, MET)
        except (AttributeError, TypeError) as err:
            print(f"something went wrong {err}")
