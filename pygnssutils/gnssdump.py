"""
Command line utility, installed with PyPi library pygnssutils,
to stream the parsed UBX, NMEA or RTCM3 output of a GNSS device
to stdout or a designated output handler.

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
from pyubx2 import (
    UBXReader,
    VALCKSUM,
    GET,
    UBX_PROTOCOL,
    NMEA_PROTOCOL,
    RTCM3_PROTOCOL,
    ERR_LOG,
    ERR_RAISE,
    hextable,
    protocol,
)
import pynmeagps.exceptions as nme
import pyubx2.exceptions as ube
import pyrtcm.exceptions as rte
from pygnssutils._version import __version__ as VERSION
from pygnssutils.exceptions import ParameterError
from pygnssutils.globals import (
    FORMAT_PARSED,
    FORMAT_BINARY,
    FORMAT_HEX,
    FORMAT_HEXTABLE,
    FORMAT_PARSEDSTRING,
    FORMAT_JSON,
    VERBOSITY_MEDIUM,
    LOGLIMIT,
)
from pygnssutils.helpers import format_json
from pygnssutils.helpstrings import GNSSDUMP_HELP


class GNSSStreamer:
    """
    GNSS Streamer Class.

    Streams and parses UBX, NMEA or RTCM3 GNSS messages from any data stream (e.g. Serial, Socket or File)
    to stdout (e.g. terminal), outfile file or to a custom output handler. The custom output
    handler can either be a writeable output medium (serial, file, socket or Queue) or an evaluable
    Python expression e.g. lambda function.

    Ensure the custom handler is consistent with the output format e.g. don't try writing binary data to
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

        :param object app: application from which this class is invoked (None)
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
        :param str outfile: (kwarg) fully qualified path to output file (None)
        :param int logtofile: (kwarg) 0 = log to stdout, 1 = log to file '/logpath/gnssdump-timestamp.log' (0)
        :param str logpath: {kwarg} fully qualified path to logfile folder (".")
        :param object outputhandler: (kwarg) either writeable output medium or evaluable expression (None)
        :param object errorhandler: (kwarg) either writeable output medium or evaluable expression (None)
        :raises: ParameterError
        """
        # pylint: disable=raise-missing-from

        # self.__app = app  # Reference to calling application class (if applicable)

        self._reader = None
        self.ctx_mgr = False
        self._datastream = kwargs.get("datastream", None)
        self._port = kwargs.get("port", None)
        self._socket = kwargs.get("socket", None)
        self._outfile = kwargs.get("outfile", None)
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
            self._output = None
            self._stopevent = False
            self._outputhandler = None
            self._errorhandler = None

            # flag to signify beginning of JSON array
            self._jsontop = True

            self._setup_output_handlers(**kwargs)

        except (ParameterError, ValueError, TypeError) as err:
            raise ParameterError(
                f"Invalid input arguments {kwargs}\n{err}\nType gnssdump -h for help."
            )

    def _setup_output_handlers(self, **kwargs):
        """
        Set up output handlers.

        Output handlers can either be writeable output media
        (Serial, File, socket or Queue) or an evaluable expression.

        'allhandler' applies to all protocols and overrides
        individual output handlers.
        """

        htypes = (Serial, TextIOWrapper, BufferedWriter, Queue, socket)

        if "errorhandler" in kwargs:
            erh = kwargs["errorhandler"]
            if isinstance(erh, htypes):
                self._errorhandler = erh
            else:
                self._errorhandler = eval(erh)

        if "outputhandler" in kwargs:
            oph = kwargs["outputhandler"]
            if isinstance(oph, htypes):
                self._outputhandler = oph
            else:
                self._outputhandler = eval(oph)
            return

    def __enter__(self):
        """
        Context manager enter routine.
        """

        self.ctx_mgr = True
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

        if self._outfile is not None:
            ftyp = "wb" if self._format == FORMAT_BINARY else "w"
            self._output = open(self._outfile, ftyp)

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

        if self._output is not None:
            self._output.close()

    def _start_reader(self):
        """Create UBXReader instance."""

        self._reader = UBXReader(
            self._stream,
            quitonerror=self._quitonerror,
            protfilter=self._protfilter,
            validate=self._validate,
            msgmode=self._msgmode,
            parsebitfield=self._parsebitfield,
        )
        self._do_log(f"Parsing GNSS data stream from: {self._stream}...\n")

        # if outputting json, add opening tag
        if self._format == FORMAT_JSON:
            self._cap_json(1)

        self._do_parse()

    def _do_parse(self):
        """
        Read the data stream and direct to the appropriate
        UBX, NMEA or RTCM3 parser.

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
                handler = self._outputhandler
                # establish the appropriate handler and identity for this protocol
                if msgprot == UBX_PROTOCOL:
                    msgidentity = parsed_data.identity
                elif msgprot == NMEA_PROTOCOL:
                    msgidentity = parsed_data.talker + parsed_data.msgID
                elif msgprot == RTCM3_PROTOCOL:
                    msgidentity = parsed_data.identity
                # does it pass the protocol filter?
                if self._protfilter & msgprot:
                    # does it pass the message identity filter if there is one?
                    if self._msgfilter is not None:
                        if msgidentity not in self._msgfilter:
                            continue
                    # if it passes, send to designated output
                    self._do_output(raw_data, parsed_data, handler)

                if self._limit and self._msgcount >= self._limit:
                    raise EOFError

        except EOFError:  # end of stream
            if not self.ctx_mgr:
                self.stop()
            # self._do_log("End of file or limit reached", VERBOSITY_LOW)
        except Exception as err:  # pylint: disable=broad-except
            self._quitonerror = ERR_RAISE  # don't ignore irrecoverable errors
            self._do_error(err)

    def _do_output(self, raw: bytes, parsed: object, handler: object):
        """
        Output message to terminal in specified format(s) OR pass
        to external output handler if one is specified.

        :param bytes raw: raw (binary) message
        :param object parsed: parsed message
        :param object handler: output handler
        """

        self._msgcount += 1

        # stdout (can output multiple formats)
        if handler is None:
            if self._format & FORMAT_PARSED:
                self._do_print(parsed)
            if self._format & FORMAT_BINARY:
                self._do_print(raw)
            if self._format & FORMAT_HEX:
                self._do_print(raw.hex())
            if self._format & FORMAT_HEXTABLE:
                self._do_print(hextable(raw))
            if self._format & FORMAT_PARSEDSTRING:
                self._do_print(str(parsed))
            if self._format & FORMAT_JSON:
                self._do_print(self._do_json(parsed))
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
            output = self._do_json(parsed)
        else:
            output = raw
        if isinstance(handler, (Serial, TextIOWrapper, BufferedWriter)):
            handler.write(output)
        elif isinstance(handler, Queue):
            handler.put(output)
        elif isinstance(handler, socket):
            handler.sendall(output)
        # treated as evaluable expression
        else:
            handler(output)

    def _do_print(self, data: object):
        """
        Print data to outfile or stdout.

        :param object data: data to print
        """

        if self._outfile is None:
            print(data)
        else:
            if (self._format == FORMAT_BINARY and not isinstance(data, bytes)) or (
                self._format != FORMAT_BINARY and not isinstance(data, str)
            ):
                data = f"{data}\n"
            self._output.write(data)

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
            self._errorhandler.sendall(err)
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

    def _do_json(self, parsed: object) -> str:
        """
        If outputting JSON for this protocol, each message
        in array is terminated by comma except the last
        [{msg1},{msg2},...,[lastmsg]]

        :param object parsed: parsed GNSS message
        :returns: output
        :rtype: str
        """

        if self._jsontop:
            output = format_json(parsed)
            self._jsontop = False
        else:
            output = "," + format_json(parsed)
        return output

    def _cap_json(self, start: int):
        """
        Caps JSON file for each protocol handler.

        :param int start: 1 = start, 0 = end
        """

        if start:
            cap = '{"GNSS_Messages": ['
        else:
            cap = "]}"

        oph = self._outputhandler
        if oph is None:
            print(cap)
        elif isinstance(oph, (Serial, TextIOWrapper, BufferedWriter)):
            oph.write(cap)
        elif isinstance(oph, Queue):
            oph.put(cap)
        elif isinstance(oph, socket):
            oph.sendall(cap)

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
        if sys.argv[1] in {"-v", "--v", "-V", "--V", "version", "-version"}:
            print(VERSION)
            sys.exit()

    try:

        with GNSSStreamer(**dict(arg.split("=") for arg in sys.argv[1:])) as gns:
            gns.run()

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":

    main()
