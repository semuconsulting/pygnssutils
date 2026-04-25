"""
rinex_conv.py

RINEX Conversion Common class.

A preliminary implementation of a RINEX conversion utility for
observation, navigation and meteorological data.

Functionality will be extended in future versions - contributions welcome.

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

# pylint: disable=too-many-public-methods, unused-argument, too-many-positional-arguments, too-many-arguments

from datetime import datetime
from io import BufferedReader
from logging import getLogger
from pathlib import Path
from threading import Event
from types import FunctionType, MethodType, NoneType
from typing import Any, Literal

from pygnssutils.exceptions import RINEXProcessingError
from pygnssutils.gnssreader import (
    NMEA_PROTOCOL,
    RTCM3_PROTOCOL,
    UBX_PROTOCOL,
    GNSSReader,
)
from pygnssutils.rinex_conv_met import RinexConverterMeteorology
from pygnssutils.rinex_conv_nav import RinexConverterNavigation
from pygnssutils.rinex_conv_obs import RinexConverterObservation
from pygnssutils.rinex_globals import (
    ALLGNSS,
    ALLOBS,
    EPOCHMAX,
    EPOCHMIN,
    MET,
    NAV,
    OBS,
    RINEX_CANCELLED,
    RINEX_ERROR,
    RINEX_NORECS,
    RINEX_OK,
    RINEXVER_DEFAULT,
)
from pygnssutils.rinex_helpers import (
    format_comments,
    format_filename,
    format_runby,
    format_version,
)

RINEXHANDLERS = {
    OBS: RinexConverterObservation,
    NAV: RinexConverterNavigation,
    MET: RinexConverterMeteorology,
}

CUR = "cur"
FILENAME = "fnm"
FRQ = "frq"
HANDLER = "hnd"
PROC = "prc"
MAX = "max"
MIN = "min"
STREAM = "stm"
VERBOSITY_MEDIUM = 1


class RinexConverter:
    """
    Rinex Common Convertor Class.
    """

    def __init__(
        self,
        app,
        rinex_version: str,
        rinex_types: list[str],
        gnssfilter: list[str],
        obsfilter: list[str],
        datasource: list[str],
        minobs: int,
        marker: list[str],
        antenna: list[str],
        receiver: list[str],
        observer: str,
        comments: list[str],
        protfilter: int = NMEA_PROTOCOL | UBX_PROTOCOL | RTCM3_PROTOCOL,
        verbosity: Literal[-1, 0, 1, 2, 3] = VERBOSITY_MEDIUM,
        logtofile: str = "",
        **kwargs,
    ):
        """
        Constructor.

        :param object app: application from which this class is invoked (None)
        :param str rinex_version: RINEX protocol version (3.05)
        :param list[str] rinex_type: RINEX output type(s) e.g. ["O","N"]
        :param list[str] gnssfilter: List of GNSS codes to process \
            (or None for all) e.g. [GPS,GAL]
        :param list[str] obsfilter: List of observation codes to process \
            (or None for all) e.g. ["1C","2B"]
        :param list[str] datasource: List of datasources for each rinex \
            type e.g. ["R","R","R"]
        :param int minobs: Minimum observations per observation type (0)
        :param list[str] marker: marker details (name, number, type)
        :param list[str] antenna: antenna details (number, type)
        :param list[str] | receiver: receiver details (number, type, version)
        :param str observer: observer details
        :param list[str] comments: user comments
        :param int protfilter: input message protocol mask NMEA=1, UBX=2, \
            RTCM3=4. Can be OR'd (7)
        :param Literal[-1,0,1,2,3] verbosity: log message verbosity -1 = critical, 0 = error, \
            1 = warning, 2 = info, 3 = debug (1)
        :param str logtofile: fully qualified path to logfile ("" = no logfile)
        :param dict kwargs: user-defined keyword arguments to pass to conversion functions
        """

        self.logger = getLogger(__name__)
        self.__app = app  # pylint: disable=unused-private-member
        self._rinex_version = RINEXVER_DEFAULT if rinex_version == "" else rinex_version
        self._rinex_types = ALLOBS if rinex_types == [""] else rinex_types
        self._gnssfilter = ALLGNSS if gnssfilter == [""] else gnssfilter
        self._obsfilter = obsfilter
        while len(datasource) < 3:  # OBS, NAV, MET
            datasource.append("R")
        self._datasource = ["R", "R", "R"] if datasource == [""] else datasource
        self._minobs = minobs
        self._marker = marker
        self._antenna = antenna
        self._receiver = receiver
        self._observer = observer
        self._user_comments = comments
        self._protfilter = protfilter
        self._epochdata = {
            OBS: {MAX: EPOCHMIN, MIN: EPOCHMAX, CUR: EPOCHMIN, FRQ: 0},
            NAV: {MAX: EPOCHMIN, MIN: EPOCHMAX, CUR: EPOCHMIN, FRQ: 0},
            MET: {MAX: EPOCHMIN, MIN: EPOCHMAX, CUR: EPOCHMIN, FRQ: 0},
        }
        self.verbosity = int(verbosity)
        self.logtofile = logtofile

        self._outputs = {}
        self._tot = 0
        self._recs = {}
        self._msgcount = 0
        self._progress = 0
        self._prev_progress = 0

        # set up conversion handlers for OBS, NAV, MET as required
        for rt in self._rinex_types:
            self._outputs[rt] = {}
            self._outputs[rt][HANDLER] = RINEXHANDLERS[rt](
                self,
                rinex_version=self._rinex_version,
                gnssfilter=self._gnssfilter,
                obsfilter=self._obsfilter,
                datasource=self._datasource[{OBS: 0, NAV: 1, MET: 2}[rt]],
                minobs=self._minobs,
                marker=self._marker,
                antenna=self._antenna,
                receiver=self._receiver,
                observer=self._observer,
                **kwargs,
            )
            self._outputs[rt][PROC] = 0

    def process_input(
        self,
        infile: Path | str,
        stopevent: Event | NoneType = None,
        progcallback: FunctionType | MethodType | NoneType = None,
        **kwargs,
    ) -> int:
        """
        Process binary input file containing UBX, RTCM or NMEA GNSS messages.

        :param Path | str infile: input binary file path
        :param Event | NoneType stopevent: stop event for remote cancellation (None)
        :param FunctionType | MethodType | NoneType progcallback: progress update \
            callback function or method (None)
        :return: return code (0 = success, >0 = error)
        :rtype: int
        """

        if isinstance(infile, str):
            infile = Path(infile)

        outputpath = infile.parent

        # check total number of raw messages in file
        self._msgcount = 0
        with open(infile, "rb") as inputstream:
            gnr = GNSSReader(inputstream, parsing=False, protfilter=self._protfilter)
            for raw, _ in gnr:
                if raw is not None:
                    self._msgcount += 1
        if self._msgcount == 0:
            return RINEX_NORECS

        with open(infile, "rb") as inputstream:
            res = self.process_input_data(
                self._rinex_types,
                inputstream,
                outputpath,
                stopevent,
                progcallback,
                **kwargs,
            )
        return res

    def process_input_data(
        self,
        rinextypes: list[str],
        instream: BufferedReader,
        outputpath: Path,
        stopevent: Event | NoneType = None,
        progcallback: FunctionType | MethodType | NoneType = None,
        **kwargs,
    ) -> int:
        """
        Process binary data stream.

        :param list[str] rinextypes: RINEX conversion type (O, N, M)
        :param BufferedReader instream: input binary file stream
        :param TextIOWrapper outstream: output text file stream
        :param Event | NoneType stopevent: stop event for remote cancellation (None)
        :param FunctionType | MethodType | NoneType progcallback: progress update callback \
            function or method (None)
        :return: return code (0 = success, >0 = error)
        :rtype: int
        """

        # pylint: disable=consider-using-with

        self.logger.debug(
            (
                f"{self._rinex_version=} {rinextypes=} {self._gnssfilter=} "
                f"{self._obsfilter=} {self._protfilter=} {self._minobs=} "
                f"{instream=} {outputpath=} {kwargs=}"
            )
        )

        res = RINEX_ERROR

        try:
            # parse incoming data stream until complete or cancelled
            gnr = GNSSReader(instream, parsing=True, protfilter=self._protfilter)
            for raw, parsed in gnr:
                if stopevent is not None:
                    if stopevent.is_set():
                        raise RINEXProcessingError("Cancelled")
                if raw is not None:
                    self._tot += 1
                    self._progress = int(round(100 * self._tot / self._msgcount, 0))
                    self._do_progress_update(progcallback, self._progress)
                    self._recs[parsed.identity] = self._recs.get(parsed.identity, 0) + 1
                    for rt in rinextypes:
                        rc = self._outputs[rt][HANDLER].process_input_data(parsed)
                        self._outputs[rt][PROC] += rc

            # setup output file streams for OBS, NAV, MET as required
            for rt in rinextypes:
                fnm = format_filename(
                    rt,
                    self._gnssfilter,
                    self._epochdata[rt]["min"],
                    self._epochdata[rt]["max"],
                    self._epochdata[rt]["frq"],
                    outputpath,
                    self._datasource[{OBS: 0, NAV: 1, MET: 2}[rt]],
                )
                self._outputs[rt][FILENAME] = fnm
                self._outputs[rt][STREAM] = open(fnm, "w", encoding="utf-8")

            # process accumulated data
            self.process_output_data(rinextypes)
            res = RINEX_OK

        # except (TypeError, ValueError, AttributeError) as err:
        #     self.logger.error(err)
        #     res = RINEX_ERROR
        except (RINEXProcessingError, KeyboardInterrupt):
            self.logger.warning("Terminated by user")
            res = RINEX_CANCELLED

        finally:
            for rt in rinextypes:
                op = self._outputs.get(rt, None)
                if op is not None:
                    if op.get(STREAM, None) is not None:
                        op[STREAM].close()

        return res

    def process_output_data(self, rinextypes: list[str]):
        """
        Process any accumulated data for each RINEX category
        (OBS, NAV, MET).

        :param list[str] rinextypes: rinex type(s)
        """

        for rt in rinextypes:
            op = self._outputs[rt]
            if op[PROC] > 0:  # only process if at least 1 valid observation
                op[HANDLER].process_output_file()

    def format_header_common(self, rinextype: Literal["O", "N", "M"]) -> str:
        """
        Format common header lines.

        :param Literal["O","N","M"] rinextype: rinextype
        :return: formatted string
        :rtype: str
        """

        return (
            format_version(self._rinex_version, rinextype, self._gnssfilter)
            + format_runby()
            + format_comments(self._user_comments)
        )

    def output(self, data: str | Any | NoneType, rinextype: Literal["O", "N", "M"]):
        """
        Write formatted data to designated RINEX output file.

        :param str | Any | NoneType data: RINEX formatted string
        :param Literal["O", "N", "M"] rinextype: rinex output type
        """

        if data is None or data == "":
            return

        self._outputs[rinextype][STREAM].write(str(data))
        self._outputs[rinextype][STREAM].flush()

    def _do_progress_update(
        self, progcallback: FunctionType | MethodType | NoneType, progress: int
    ):
        """
        Invoke callback function or method to report % complete.

        :param FunctionType | MethodType | NoneType progcallback: callback
        :param int progress: % complete
        """

        try:
            if isinstance(progcallback, (FunctionType, MethodType)):
                if progress > self._prev_progress:
                    progcallback(progress)
                    self._prev_progress = progress
        except TypeError:
            pass

    def get_current_epoch(self, rt: str) -> datetime:
        """
        Getter for current epoch.

        :return: current epoch
        :rtype: datetime
        """

        return self._epochdata[rt][CUR]

    def set_current_epoch(self, epoch: datetime, rt: str):
        """
        Setter for current epoch.

        Sets observation frequency (interval) and first and last observation epochs.

        :param datetime epoch: current epoch
        """

        if epoch == self._epochdata[rt][CUR]:
            return

        self._epochdata[rt][FRQ] = (epoch - self._epochdata[rt][CUR]).total_seconds()
        self._epochdata[rt][CUR] = epoch
        self._epochdata[rt][MIN] = min(self._epochdata[rt][MIN], epoch)
        self._epochdata[rt][MAX] = max(self._epochdata[rt][MAX], epoch)

    def get_start_epoch(self, rt: str) -> datetime:
        """
        Getter for start epoch (first observation).

        :return: start epoch
        :rtype: datetime
        """

        return self._epochdata[rt][MIN]

    def get_end_epoch(self, rt: str) -> datetime:
        """
        Getter for end epoch (last observation).

        :return: end epoch
        :rtype: datetime
        """

        return self._epochdata[rt][MAX]

    def get_interval(self, rt: str) -> int | float:
        """
        Getter for observation interval (frequency).

        :return: observation interval in seconds
        :rtype: int | float
        """

        return self._epochdata[rt][FRQ]

    @property
    def outputs(self) -> dict[str, tuple[Path, int]]:
        """
        Getter for conversion outputs. For each rinex type:
        (filename, number of records processed)

        :return: outputs
        :rtype: dict[str, tuple[Path, int]]
        """

        outputs = {}
        for rt, values in self._outputs.items():
            outputs[rt] = (values[FILENAME], values[PROC])
        return outputs
