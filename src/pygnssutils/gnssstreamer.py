"""
pygnssutils - gnssstreamer.py

GNSS streaming application which supports bidirectional communication
with a GNSS datastream (e.g. an NMEA or UBX GNSS receiver serial port)
via designated input and output handlers.

Created on 27 Jul 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

from collections import defaultdict
from io import UnsupportedOperation
from logging import getLogger
from queue import Empty, Queue
from threading import Event, Thread
from time import time

from pynmeagps import NMEAMessage, NMEAParseError
from pyrtcm import RTCMMessage, RTCMParseError
from pyubx2 import (
    CARRSOLN,
    ERR_RAISE,
    FIXTYPE,
    GET,
    LASTCORRECTIONAGE,
    NMEA_PROTOCOL,
    RTCM3_PROTOCOL,
    UBX_PROTOCOL,
    VALCKSUM,
    UBXMessage,
    UBXParseError,
    UBXReader,
    hextable,
)
from serial import Serial

from pygnssutils.exceptions import ParameterError
from pygnssutils.globals import (
    CONNECTED,
    DISCONNECTED,
    FIXTYPE_GGA,
    FORMAT_BINARY,
    FORMAT_HEX,
    FORMAT_HEXTABLE,
    FORMAT_JSON,
    FORMAT_PARSED,
    FORMAT_PARSEDSTRING,
    VERBOSITY_MEDIUM,
)
from pygnssutils.helpers import format_json, set_logging


class GNSSStreamer:
    """
    Skeleton GNSS application class which supports bidirectional communication
    with a GNSS datastream (e.g. an NMEA or UBX GNSS receiver serial port) via
    designated input and output handlers.
     - user-defined output and input handlers (callbacks).
     - flexible protocol and message filtering options.
     - flexible output formatting options e.g. parsed, binary, hex, JSON.
     - supports external inputs to datastream, e.g. from RTK data source \
        (NTRIP or SPARTN) or a configuration file.

    The class implements public methods which can be used by other pygnssutils
    classes:
     - `get_coordinates()`, returns current GNSS status.
     - `status` property, returns current GNSS status.

    To utilise logging, invoke and configure `logging.getLogger("pygnssutils")`
    in the calling hierarchy.
    """

    def __init__(
        self,
        app: object,
        stream: object,
        validate: int = VALCKSUM,
        msgmode: int = GET,
        parsebitfield: bool = True,
        outformat: int = FORMAT_PARSED,
        quitonerror: int = ERR_RAISE,
        protfilter: int = NMEA_PROTOCOL | UBX_PROTOCOL | RTCM3_PROTOCOL,
        msgfilter: str = "",
        limit: int = 0,
        outqueue: Queue = None,
        inqueue: Queue = None,
        outputhandler: object = None,
        inputhandler: object = None,
        stopevent: object = None,
        verbosity: int = VERBOSITY_MEDIUM,
        logtofile: str = "",
        **kwargs,
    ):
        """
        Constructor.

        :param object app: name of any calling application
        :param object stream: GNSS datastream (e.g. Serial, File or Socket)
        :param bool validate: 1 = validate checksum, 0 = do not validate (1)
        :param int msgmode: 0 = GET, 1 = SET, 2 = POLL (0)
        :param bool parsebitfield: 1 = parse UBX 'X' attributes as bitfields, 0 = leave as bytes (1)
        :param int format: output format 1 = parsed, 2 = raw, 4 = hex, 8 = tabulated hex, \
            16 = parsed as string, 32 = JSON (can be OR'd) (1)
        :param int quitonerror: 0 = ignore errors,  1 = log errors and continue, \
            2 = (re)raise errors (1)
        :param int protfilter: 1 = NMEA, 2 = UBX, 4 = RTCM3 (can be OR'd) (7 - ALL)
        :param str msgfilter: comma-separated string of message identities to include in output \
            e.g. 'NAV-PVT,GNGSA'. A periodicity clause can be added e.g. NAV-SAT(10), signifying \
                the minimum period in seconds between successive messages of this type ("")
        :param int limit: maximum number of messages to read (0 = unlimited)
        :param Queue outqueue: queue for data from datastream (None)
        :param Queue inqueue: queue for data to datastream (None)
        :param object outputhandler: output callback function (`do_output()`)
        :param object inputhandler: input callback function (`do_input()`)
        :param Event stopevent: stopevent to terminate `run()` (internal `Event()`)
        :param int verbosity: log message verbosity -1 = critical, 0 = error, 1 = warning, \
            2 = info, 3 = debug (1)
        :param str logtofile: fully qualified path to logfile ("" = no logfile)
        :param dict kwargs: user-defined keyword arguments to pass to custom input/output handlers
        :raises ValueError: If invalid arguments
        """

        try:

            self.__app = app  # pylint: disable=unused-private-member
            self.verbosity = int(verbosity)
            self.logtofile = logtofile
            self.logger = getLogger(__name__)
            set_logging(getLogger("pyubx2"), self.verbosity, self.logtofile)

            if stream is None:
                raise ParameterError("stream argument is required")
            self._stream = stream
            self._validate = int(validate)
            self._msgmode = int(msgmode)
            self._parsebitfield = int(parsebitfield)
            self._outformat = int(outformat)
            if not 0 < self._outformat < 64:
                raise ParameterError(f"format {self._outformat} cannot exceed 63")
            self._quitonerror = int(quitonerror)
            self._protfilter = int(protfilter)
            self._limit = int(limit)
            self._protfilter = int(protfilter)
            self._outqueue = outqueue
            self._inqueue = inqueue
            if outputhandler is None:
                self._outputhandler = self.do_output
            else:
                self._outputhandler = outputhandler
            if inputhandler is None:
                self._inputhandler = self.do_input
            else:
                self._inputhandler = inputhandler
            self._msgfilter = self._init_msgfilter(msgfilter)
            if stopevent is None:
                self._stopevent = Event()
            else:
                self._stopevent = stopevent
            self._msgcount = 0
            self._incount = defaultdict(int)
            self._filtcount = defaultdict(int)
            self._outcount = defaultdict(int)
            self._errcount = 0
            self.connected = DISCONNECTED
            self._status = {
                "fix": "NO FIX",
                "lat": 0.0,
                "lon": 0.0,
                "alt": 0.0,
                "sep": 0.0,
                "sip": 0,
                "hacc": 0.0,
                "hDOP": 0.0,
                "diffage": 0,
            }
            self._read_thread = None
            self._kwargs = kwargs

        except ValueError as err:
            raise ParameterError(f"Invalid input parameters {err}") from err

    def _init_msgfilter(self, msgfilts: str) -> dict:
        """
        Initialise message filter dict.

        Msgfilter defines message identity and (optionally) minimum
        period between successive messages of this type.
        Format is {identity: (min period, last received time)}

        :param str msgfilt: message filter as string
        :return: msgfilter as dict, or None if empty
        :rtype: dict
        """

        if msgfilts in ("", None):
            return None
        msgfilter = {}
        mfparts = msgfilts.split(",")
        for msg in mfparts:
            filt = msg.strip(")").split("(")
            if len(filt) == 2:  # identity & period filter
                msgfilter[filt[0]] = (float(filt[1]), 0)
            else:  # identity filter
                msgfilter[filt[0]] = (0, 0)
        return msgfilter

    def __enter__(self):
        """
        Context manager enter routine.
        """

        self.run()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Context manager exit routine.

        Terminates app in an orderly fashion.
        """

        self.stop()

    def run(self):
        """
        Run GNSS reader/writer.
        """

        self.logger.info(f"Starting GNSS reader/writer using {self._stream}...")
        self.connected = CONNECTED
        self._stopevent.clear()

        self._read_thread = Thread(
            target=self._read_loop,
            args=(
                self._stream,
                self._stopevent,
                self._outqueue,
                self._inqueue,
                self._kwargs,
            ),
            daemon=True,
        )
        self._read_thread.start()

    def stop(self):
        """
        Stop GNSS reader/writer.
        """

        self._stopevent.set()
        self.connected = DISCONNECTED
        self.logger.info(
            f"\nMessages input:    {dict(sorted(self._incount.items()))}\n"
            f"Messages filtered: {dict(sorted(self._filtcount.items()))}\n"
            f"Messages output:   {dict(sorted(self._outcount.items()))}\n"
            f"Streaming terminated, {self._msgcount:,} messages "
            f"processed with {self._errcount:,} errors."
        )

    def _read_loop(
        self,
        stream: Serial,
        stopevent: Event,
        outqueue: Queue,
        inqueue: Queue,
        kwargs: dict,
    ):
        """
        THREADED
        Reads and parses incoming GNSS data from the receiver,
        and sends any queued output data to the receiver.

        :param Serial stream: serial stream
        :param Event stopevent: stop event
        :param Queue outqueue: queue for messages from receiver
        :param Queue inqueue: queue for messages to send to receiver
        :param dict kwargs: user-defined keyword arguments
        """

        ubr = UBXReader(
            stream,
            msgmode=self._msgmode,
            validate=self._validate,
            quitonerror=self._quitonerror,
            parsebitfield=self._parsebitfield,
        )
        while not stopevent.is_set():
            try:

                raw_data, parsed_data = ubr.read()
                if raw_data is None or parsed_data is None:
                    stopevent.set()
                    break  # EOF
                self._incount[parsed_data.identity] += 1
                self._get_status(parsed_data)
                # check if message passes filter
                if self._filtered(parsed_data):
                    self._filtcount[parsed_data.identity] += 1
                else:
                    # format data
                    formatted = self._formatted(raw_data, parsed_data, self._outformat)
                    # send filtered and formatted data to output handler
                    self._msgcount += 1
                    self._outcount[parsed_data.identity] += 1
                    self._outputhandler(
                        raw_data, formatted, outqueue, logger=self.logger, **kwargs
                    )
                if self._limit and self._msgcount >= self._limit:
                    self.logger.info(f"Message limit {self._limit} reached.")
                    stopevent.set()
                    break

                # send any data from input handler to receiver
                self._inputhandler(
                    ubr.datastream, inqueue, logger=self.logger, **kwargs
                )

            except ParameterError as err:
                raise ParameterError() from err
            except OSError:  # thread terminated while reading
                break
            except (NMEAParseError, UBXParseError, RTCMParseError) as err:
                self._errcount += 1
                self.logger.error(f"Error parsing data stream {err}")
                continue

    def _get_status(self, parsed_data: object):
        """
        Extract current navigation status data from NMEA or UBX message.

        :param object parsed_data: parsed NMEA or UBX navigation message
        """

        for attr in (
            "lat",
            "lon",
            "alt",
            "sep",
            "HDOP",
            "hDOP",
            "diffAge",
            "diffStation",
        ):
            if hasattr(parsed_data, attr):
                self._status[attr] = getattr(parsed_data, attr)
        if hasattr(parsed_data, "numSV"):
            self._status["sip"] = parsed_data.numSV
        if hasattr(parsed_data, "fixType"):
            self._status["fix"] = FIXTYPE.get(parsed_data.fixType, "NO FIX")
        if hasattr(parsed_data, "carrSoln"):
            if parsed_data.carrSoln != 0:  # NO RTK
                self._status["fix"] = (
                    f"{CARRSOLN.get(parsed_data.carrSoln, self._status['fix'])}"
                )
        if hasattr(parsed_data, "quality"):
            self._status["fix"] = FIXTYPE_GGA.get(parsed_data.quality, "NO FIX")
        if hasattr(parsed_data, "lastCorrectionAge"):
            self._status["diffage"] = LASTCORRECTIONAGE.get(
                parsed_data.lastCorrectionAge, 0
            )
        if hasattr(parsed_data, "hMSL"):  # UBX hMSL is in mm
            self._status["alt"] = parsed_data.hMSL / 1000
        if hasattr(parsed_data, "hMSL") and hasattr(parsed_data, "height"):
            self._status["sep"] = (parsed_data.height - parsed_data.hMSL) / 1000
        if hasattr(parsed_data, "hAcc"):  # UBX hAcc is in mm
            unit = 1 if parsed_data.identity == "PUBX00" else 1000
            self._status["hacc"] = parsed_data.hAcc / unit

    def _filtered(self, parsed_data: object) -> bool:
        """
        Check if this message type is filtered out.
        If per = 0, filter is based on identity.
        If per > 0, filter is based on identity & last output time.

        :param object parsed_datap: parsed message
        :return: True (excluded) or False (included)
        :rtype: bool
        """

        ident = parsed_data.identity
        if isinstance(parsed_data, UBXMessage):
            protocol = UBX_PROTOCOL
        elif isinstance(parsed_data, NMEAMessage):
            protocol = NMEA_PROTOCOL
        elif isinstance(parsed_data, RTCMMessage):
            protocol = RTCM3_PROTOCOL
        else:
            return True

        if self._protfilter & protocol:
            if self._msgfilter is None:
                return False

            if ident in self._msgfilter:
                per, tic = self._msgfilter[ident]
                if per == 0:  # no period filter
                    return False
                toc = time()
                elapsed = toc - tic
                # check if at least 95% of filter period has elapsed
                if elapsed >= 0.95 * per:
                    self._msgfilter[ident] = (per, toc)
                    return False

        return True

    def _formatted(self, raw_data: bytes, parsed_data: object, outformat: int) -> list:
        """
        Format output data.

        :param bytes raw_data: raw data
        :param object parsed_data: parsed data
        :param int outformat: OR'd format options
        :return: list of data objects in selected formats
        :rtype: list
        """

        formatted = []
        if outformat & FORMAT_PARSED:
            formatted.append(parsed_data)
        if outformat & FORMAT_BINARY:
            formatted.append(raw_data)
        if outformat & FORMAT_HEX:
            formatted.append(raw_data.hex())
        if outformat & FORMAT_HEXTABLE:
            formatted.append(hextable(raw_data))
        if outformat & FORMAT_PARSEDSTRING:
            formatted.append(str(parsed_data))
        if outformat & FORMAT_JSON:
            formatted.append(format_json(parsed_data))
        return formatted

    def get_coordinates(self) -> dict:
        """
        DEPRECATED - use status property instead.
        Return current GNSS status.
        (method used by certain pygnssutils classes)

        :return: dict of GNSS status attributes
        :rtype: dict
        """

        return self._status

    @property
    def status(self) -> dict:
        """
        Return current GNSS status.

        :return: dict of GNSS status attributes
        :rtype: dict
        """

        return self._status

    @property
    def stream(self) -> object:
        """
        Return GNSS datastream.

        :return: GNSS datastream
        :rtype: object
        """

        return self._stream

    @staticmethod
    def do_output(raw_data: bytes, formatted_data: list, outqueue: Queue, **kwargs):
        """
        Default output handler callback.
         - logs output data type
         - sends output to out queue (if defined)

        :param bytes raw_data: raw data
        :param list formatted_data: list formatted data e.g. [NMEAMessage]
        :param Queue outqueue: queue containing output from GNSS datastream
        """

        ld = len(formatted_data)
        logger = kwargs.get("logger", None)
        if logger is not None:
            for i, data in enumerate(formatted_data):
                logger.info(f"Formatted data output ({i+1} of {ld}):\n{data}")
        if outqueue is not None:
            if ld == 1:  # if only one format, de-list
                formatted_data = formatted_data[0]
            outqueue.put((raw_data, formatted_data))

    @staticmethod
    def do_input(datastream: object, inqueue: Queue, **kwargs):
        """
        Default input handler callback.
         - receives data from in queue (if defined) and sends to datastream
         - logs received data type

        :param object datastream: bidirectional GNSS datastream
        :param Queue inqueue: queue containing data to be sent to GNSS datastream
        :raises ParameterError
        """

        logger = kwargs.get("logger", None)
        if inqueue is not None:
            try:
                while not inqueue.empty():
                    data = inqueue.get(False)
                    if isinstance(data, tuple):  # (raw, parsed)
                        raw, _ = data
                    else:  # just raw
                        raw = data
                    if logger is not None:
                        logger.info(f"Data input: {data}")
                    datastream.write(raw)
                    inqueue.task_done()
            except Empty:
                pass
            except UnsupportedOperation as err:
                msg = f"Datastream does not support write operations {datastream} {err}"
                if logger is not None:
                    logger.critical(msg)
                raise ParameterError(msg) from err
