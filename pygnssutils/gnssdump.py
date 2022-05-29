"""
Command line utility, installed with PyPi library pygnssutils,
to stream the parsed UBX, NMEA or RTCM3 output of a GNSS device
to stdout or a designated protocol handler.

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""
# pylint: disable=line-too-long eval-used

import sys
import os
from socket import socket
from queue import Queue
from datetime import datetime
from io import TextIOWrapper, BufferedWriter
from serial import Serial
import pynmeagps.exceptions as nme
import pyubx2.exceptions as ube
import pyrtcm.exceptions as rte
from pygnssutils.gnssreader import GNSSReader
from pygnssutils.exceptions import ParameterError
from pygnssutils.globals import (
    VALCKSUM,
    GET,
    ALL_PROTOCOL,
    UBX_PROTOCOL,
    NMEA_PROTOCOL,
    RTCM3_PROTOCOL,
    ERR_LOG,
    ERR_RAISE,
    FORMAT_PARSED,
    FORMAT_BINARY,
    FORMAT_HEX,
    FORMAT_HEXTABLE,
    FORMAT_PARSEDSTRING,
    FORMAT_JSON,
    VERBOSITY_LOW,
    VERBOSITY_MEDIUM,
    LOGLIMIT,
)
from pygnssutils.helpers import hextable, protocol, format_json
from pygnssutils.helpstrings import GNSSDUMP_HELP


class GNSSStreamer:
    """
    GNSS Streamer Class.

    Streams and parses UBX, NMEA or RTCM3 GNSS messages from any data stream (e.g. Serial, Socket or File)
    to stdout (e.g. terminal) or to designated NMEA, UBX or RTCM protocol handler(s). The protocol
    handler can either be a writeable output medium (Serial, File, socket or Queue) or an evaluable
    expression.

    Ensure the output media type is consistent with the format e.g. don't try writing binary data to
    a text file.

    Input stream is defined via keyword arguments. One of either stream, socket, port or filename MUST be
    specified. The remaining arguments are all optional with defaults.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, **kwargs):
        """
        Context manager constructor.

        Example of usage with external protocol handler:

        gnssdump port=COM3 msgfilter=NAV-PVT ubxhandler="lambda msg: print(f'lat: {msg.lat}, lon: {msg.lon}')"

        :param object stream: (kwarg) stream object (must implement read(n) -> bytes method)
        :param str port: (kwarg) serial port name
        :param str filename: (kwarg) input file FQN
        :param str socket: (kwarg) input socket host:port
        :param int baudrate: (kwarg) serial baud rate (9600)
        :param int timeout: (kwarg) serial timeout in seconds (3)
        :param int validate: (kwarg) 1 = validate checksums, 0 = do not validate (1)
        :param int msgmode: (kwarg) 0 = GET, 1 = SET, 2 = POLL (0)
        :param int parsebitfield: (kwarg) 1 = parse UBX 'X' attributes as bitfields, 0 = leave as bytes (1)
        :param int format: (kwarg) output format 1 = parsed, 2 = raw, 4 = hex, 8 = tabulated hex, 16 = parsed as string, 32 = JSON (1) (can be OR'd)
        :param int quitonerror: (kwarg) 0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors (1)
        :param int protfilter: (kwarg) 1 = NMEA, 2 = UBX, 4 = RTCM3 (7 - ALL)
        :param str msgfilter: (kwarg) comma-separated string of message identities e.g. 'NAV-PVT,GNGSA' (None)
        :param int limit: (kwarg) maximum number of messages to read (0 = unlimited)
        :param int verbosity: (kwarg) log message verbosity 0 = low, 1 = medium, 3 = high (1)
        :param int logtofile: (kwarg) 0 = log to stdout, 1 = log to file '/logpath/gnssdump-timestamp.log' (0)
        :param int logpath: {kwarg} fully qualified path to logfile folder (".")
        :param object allhandler: (kwarg) either writeable output medium or evaluable expression (None)
        :param object nmeahandler: (kwarg) either writeable output medium or evaluable expression (None)
        :param object ubxhandler: (kwarg) either writeable output medium or evaluable expression (None)
        :param object rtcmhandler: (kwarg) either writeable output medium or evaluable expression (None)
        :param object errorhandler: (kwarg) either writeable output medium or evaluable expression (None)
        :raises: ParameterError
        """
        # pylint: disable=raise-missing-from

        self._reader = None
        self._datastream = kwargs.get("datastream", None)
        self._port = kwargs.get("port", None)
        self._socket = kwargs.get("socket", None)
        if self._socket is not None:
            sock = self._socket.split(":")
            if len(sock) != 2:
                raise ParameterError(
                    "socket keyword must be in the format host:port.\nType gnssdump -h for help."
                )
            self._socket_host = sock[0]
            self._socket_port = int(sock[1])
        self._filename = kwargs.get("filename", None)
        if (
            self._datastream is None
            and self._port is None
            and self._socket is None
            and self._filename is None
        ):
            raise ParameterError(
                "Either stream, port, socket or filename keyword argument must be provided.\nType gnssdump -h for help.",
            )

        try:

            self._baudrate = int(kwargs.get("baudrate", 9600))
            self._timeout = int(kwargs.get("timeout", 3))
            self._validate = int(kwargs.get("validate", VALCKSUM))
            self._msgmode = int(kwargs.get("msgmode", GET))
            self._parsebitfield = int(kwargs.get("parsebitfield", 1))
            self._format = int(kwargs.get("format", FORMAT_PARSED))
            self._quitonerror = int(kwargs.get("quitonerror", ERR_LOG))
            self._protfilter = int(
                kwargs.get("protfilter", NMEA_PROTOCOL | UBX_PROTOCOL | RTCM3_PROTOCOL)
            )
            self._msgfilter = kwargs.get("msgfilter", None)
            self._verbosity = int(kwargs.get("verbosity", VERBOSITY_MEDIUM))
            self._logtofile = int(kwargs.get("logtofile", 0))
            self._logpath = kwargs.get("logpath", ".")
            self._limit = int(kwargs.get("limit", 0))
            self._parsing = False
            self._stream = None
            self._msgcount = 0
            self._errcount = 0
            self._validargs = True
            self._loglines = 0
            self._stopevent = False
            self._allhandler = None
            self._errorhandler = None
            self._nmeahandler = None
            self._ubxhandler = None
            self._rtcmhandler = None

            # following is to keep tabs on where we are
            # in any JSON array for each protocol handler
            self._jsontop = {
                ALL_PROTOCOL: True,
                NMEA_PROTOCOL: True,
                UBX_PROTOCOL: True,
                RTCM3_PROTOCOL: True,
            }

            self._setup_protocol_handlers(**kwargs)

        except (ParameterError, ValueError, TypeError) as err:
            self._do_log(
                f"Invalid input arguments {kwargs}\n{err}\n{GNSSDUMP_HELP}",
                VERBOSITY_LOW,
            )
            self._validargs = False

    def _setup_protocol_handlers(self, **kwargs):
        """
        Set up protocol handlers.

        protocol handlers can either be writeable output media
        (Serial, File, socket or Queue) or an evaluable expression.

        'allhandler' applies to all protocols and overrides
        individual protocol handlers.
        """

        htypes = (Serial, TextIOWrapper, BufferedWriter, Queue, socket)

        if "errorhandler" in kwargs:
            erh = kwargs["errorhandler"]
            if isinstance(erh, htypes):
                self._errorhandler = erh
            else:
                self._errorhandler = eval(erh)

        if "allhandler" in kwargs:
            allh = kwargs["allhandler"]
            if isinstance(allh, htypes):
                self._allhandler = allh
            else:
                self._allhandler = eval(allh)
            return

        if "nmeahandler" in kwargs:
            nmh = kwargs["nmeahandler"]
            if isinstance(nmh, htypes):
                self._nmeahandler = nmh
            else:
                self._nmeahandler = eval(nmh)

        if "ubxhandler" in kwargs:
            ubh = kwargs["ubxhandler"]
            if isinstance(ubh, htypes):
                self._ubxhandler = ubh
            else:
                self._ubxhandler = eval(ubh)

        if "rtcmhandler" in kwargs:
            rth = kwargs["rtcmhandler"]
            if isinstance(rth, htypes):
                self._rtcmhandler = rth
            else:
                self._rtcmhandler = eval(rth)

    def __enter__(self):
        """
        Context manager enter routine.
        """

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Context manager exit routine.
        """

        self.stop()

    def run(self, **kwargs) -> int:
        """
        Read from provided data stream (serial, file or other stream type).
        The data stream must support a read(n) -> bytes method.

        :param int limit: (kwarg) maximum number of messages to read (0 = unlimited)
        :return: rc 0 = fail, 1 = ok
        :rtype: int
        :raises: ParameterError if socket is not in form host:port
        """

        if not self._validargs:
            return 0

        # if outputting json, add opening tag
        if self._format == FORMAT_JSON:
            self._cap_json(1)

        self._limit = int(kwargs.get("limit", self._limit))

        # open the specified input stream
        if self._datastream is not None:  # generic stream
            with self._datastream as self._stream:
                self._start_reader()
        elif self._port is not None:  # serial
            with Serial(
                self._port, self._baudrate, timeout=self._timeout
            ) as self._stream:
                self._start_reader()
        elif self._socket is not None:  # socket
            with socket() as self._stream:
                self._stream.connect((self._socket_host, self._socket_port))
                self._start_reader()
        elif self._filename is not None:  # binary file
            with open(self._filename, "rb") as self._stream:
                self._start_reader()

        return 1

    def stop(self):
        """
        Shutdown streamer.
        """

        # if outputting json, add closing tag
        if self._format == FORMAT_JSON:
            self._cap_json(0)

        self._stopevent = True
        mss = "" if self._msgcount == 1 else "s"
        ers = "" if self._errcount == 1 else "s"
        msg = f"Streaming terminated, {self._msgcount:,} message{mss} processed with {self._errcount:,} error{ers}.\n"
        self._do_log(msg, VERBOSITY_MEDIUM)

    def _start_reader(self):
        """Create GNSSReader instance."""

        self._reader = GNSSReader(
            self._stream,
            quitonerror=self._quitonerror,
            protfilter=self._protfilter,
            validate=self._validate,
            msgmode=self._msgmode,
            parsebitfield=self._parsebitfield,
        )
        self._do_log(f"Parsing GNSS data stream from: {self._stream}...\n")
        self._do_parse()

    def _do_parse(self):
        """
        Read the data stream and direct to the appropriate
        UBX or NMEA parser.

        :raises: EOFError if stream ends prematurely or message limit reached
        :raises: KeyboardInterrupt if user presses Ctrl-C
        :raises: Exception for any other uncaptured Exception
        """

        try:

            while (
                not self._stopevent
            ):  # loop until EOF, stream timeout or user hits Ctrl-C

                try:
                    (raw_data, parsed_data) = self._reader.read()
                except (
                    ube.UBXMessageError,
                    ube.UBXParseError,
                    ube.UBXStreamError,
                    ube.UBXTypeError,
                    nme.NMEAMessageError,
                    nme.NMEAParseError,
                    nme.NMEAStreamError,
                    nme.NMEATypeError,
                    rte.RTCMMessageError,
                    rte.RTCMParseError,
                    rte.RTCMStreamError,
                    rte.RTCMTypeError,
                ) as err:
                    self._do_error(err)
                    continue

                if raw_data is None:  # EOF or timeout
                    raise EOFError

                # get the message protocol (NMEA or UBX)
                msgprot = protocol(raw_data)
                handler = None
                # establish the appropriate handler and identity for this protocol
                if msgprot == UBX_PROTOCOL:
                    msgidentity = parsed_data.identity
                    handler = self._ubxhandler
                elif msgprot == NMEA_PROTOCOL:
                    msgidentity = parsed_data.talker + parsed_data.msgID
                    handler = self._nmeahandler
                elif msgprot == RTCM3_PROTOCOL:
                    msgidentity = parsed_data.identity
                    handler = self._rtcmhandler
                if self._allhandler is not None:
                    handler = self._allhandler
                # does it pass the protocol filter?
                if self._protfilter & msgprot:
                    # does it pass the message identity filter if there is one?
                    if self._msgfilter is not None:
                        if msgidentity not in self._msgfilter:
                            continue
                    # if it passes, send to designated output
                    self._do_output(msgprot, raw_data, parsed_data, handler)

                if self._limit and self._msgcount >= self._limit:
                    raise EOFError

        except EOFError:  # end of stream
            self._do_log("End of file or limit reached", VERBOSITY_LOW)
            self.stop()
        except Exception as err:  # pylint: disable=broad-except
            self._quitonerror = ERR_RAISE  # don't ignore irrecoverable errors
            self._do_error(err)

    def _do_output(self, msgprot: int, raw: bytes, parsed: object, handler: object):
        """
        Output message to terminal in specified format(s) OR pass
        to external protocol handler if one is specified.

        :param int msgprot: protocol 0 = ALL, 1 = NMEA, 2 = UBX, 4 = RTCM
        :param bytes raw: raw (binary) message
        :param object parsed: parsed message
        :param object handler: Queue, socket or protocol handler (NMEA, UBX or RTCM3)
        """

        self._msgcount += 1

        # stdout (can output multiple formats)
        if handler is None:
            if self._format & FORMAT_PARSED:
                print(parsed)
            if self._format & FORMAT_BINARY:
                print(raw)
            if self._format & FORMAT_HEX:
                print(raw.hex())
            if self._format & FORMAT_HEXTABLE:
                print(hextable(raw))
            if self._format & FORMAT_PARSEDSTRING:
                print(str(parsed))
            if self._format & FORMAT_JSON:
                print(format_json(parsed))
            return

        # writeable output media (can output one format)
        if self._format == FORMAT_PARSED:
            output = parsed
        elif self._format == FORMAT_PARSEDSTRING:
            output = f"{parsed}\n"
        elif self._format == FORMAT_HEX:
            output = str(raw.hex())
        elif self._format == FORMAT_HEXTABLE:
            output = str(hextable(raw))
        elif self._format == FORMAT_JSON:
            # if outputting JSON for this protocol, ensure array
            # of messages is correctly formatted without trailing
            # comma at end [{msg1},{msg2},...,[lastmsg]]
            msgprot = msgprot if self._allhandler is None else 0
            if self._jsontop[msgprot]:
                output = format_json(parsed)
                self._jsontop[msgprot] = False
            else:
                output = "," + format_json(parsed)
        else:
            output = raw
        if isinstance(handler, (Serial, TextIOWrapper, BufferedWriter)):
            handler.write(output)
        elif isinstance(handler, Queue):
            handler.put(output)
        elif isinstance(handler, socket):
            handler.wfile.write(output)
            handler.wfile.flush()
        # treated as evaluable expression
        else:
            handler(output)

    def _do_error(self, err: Exception):
        """
        Handle error according to quitonerror flag;
        either ignore, log, (re)raise or pass to
        external error handler if one is specified.

        :param err Exception: error
        """

        if self._errorhandler is None:
            if self._quitonerror == ERR_RAISE:
                raise err
            if self._quitonerror == ERR_LOG:
                print(err)
        elif isinstance(self._errorhandler, (Serial, BufferedWriter)):
            self._errorhandler.write(err)
        elif isinstance(self._errorhandler, TextIOWrapper):
            self._errorhandler.write(str(err))
        elif isinstance(self._errorhandler, Queue):
            self._errorhandler.put(err)
        elif isinstance(self._errorhandler, socket):
            self._errorhandler.wfile.write(err)
            self._errorhandler.wfile.flush()
        else:
            self._errorhandler(err)
        self._errcount += 1

    def _do_log(
        self,
        message: str,
        loglevel: int = VERBOSITY_MEDIUM,
    ):
        """
        Write timestamped log message according to verbosity and logfile settings.

        :param str message: message to log
        :param int loglevel: log level for this message (0,1,2)
        """

        msg = f"{datetime.now()}: {message}"
        if self._verbosity >= loglevel:
            if self._logtofile:
                self._cycle_log()
                with open(self._logpath, "a", encoding="UTF-8") as log:
                    log.write(msg + "\n")
                    self._loglines += 1
            else:
                print(msg)

    def _cycle_log(self):
        """
        Generate new timestamped logfile path.
        """

        if not self._loglines % LOGLIMIT:
            tim = datetime.now().strftime("%Y%m%d%H%M%S")
            self._logpath = os.path.join(self._logpath, f"gnssdump-{tim}.log")
            self._loglines = 0

    def _cap_json(self, start: int):
        """
        Caps JSON file for each protocol handler.

        :param int start: 1 = start, 0 = end
        """

        for handler in (
            self._allhandler,
            self._nmeahandler,
            self._ubxhandler,
            self._rtcmhandler,
        ):
            if handler is not None:
                if start:
                    handler.write('{"GNSS_Messages": [')
                else:
                    handler.write("]}")

    @property
    def datastream(self) -> object:
        """
        Getter for stream.

        :return: data stream
        :rtype: object
        """

        return self._stream


def main():
    """
    CLI Entry point.

    :param: as per GNSSStreamer constructor.
    :raises: ParameterError if parameters are invalid
    """
    # pylint: disable=raise-missing-from

    if len(sys.argv) > 1:
        if sys.argv[1] in {"-h", "--h", "help", "-help", "--help", "-H"}:
            print(GNSSDUMP_HELP)
            sys.exit()

    try:

        with GNSSStreamer(**dict(arg.split("=") for arg in sys.argv[1:])) as gns:
            gns.run()

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":

    main()
