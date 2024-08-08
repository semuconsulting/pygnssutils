"""
gnssstreamer.py

GNSSStreamer class - essentially a wrapper around the pyubx2.ubxreader class
to stream the parsed UBX, NMEA or RTCM3 output of a GNSS device to stdout or
a designated output handler.

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

# pylint: disable=line-too-long eval-used

from collections import defaultdict
from io import BufferedWriter, TextIOWrapper
from logging import getLogger
from queue import Queue
from socket import AF_INET6, SOCK_STREAM, socket
from time import time

import pynmeagps.exceptions as nme
import pyrtcm.exceptions as rte
import pyubx2.exceptions as ube
from pynmeagps import NMEAMessage
from pyrtcm import RTCMMessage
from pyubx2 import (
    ERR_LOG,
    ERR_RAISE,
    GET,
    NMEA_PROTOCOL,
    RTCM3_PROTOCOL,
    UBX_PROTOCOL,
    VALCKSUM,
    UBXMessage,
    UBXReader,
    hextable,
)
from serial import Serial

from pygnssutils.exceptions import ParameterError
from pygnssutils.globals import (
    FORMAT_BINARY,
    FORMAT_HEX,
    FORMAT_HEXTABLE,
    FORMAT_JSON,
    FORMAT_PARSED,
    FORMAT_PARSEDSTRING,
)
from pygnssutils.helpers import format_conn, format_json, ipprot2int


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

    def __init__(self, app=None, **kwargs):
        """
        Context manager constructor.

        Example of usage with external protocol handler:

        gnssdump port=COM3 msgfilter=NAV-PVT ubxhandler="lambda msg: print(f'lat: {msg.lat}, lon: {msg.lon}')"

        :param object app: application from which this class is invoked (None)
        :param object stream: (kwarg) stream object (must implement read(n) -> bytes method)
        :param str port: (kwarg) serial port name
        :param str filename: (kwarg) input file FQN
        :param str socket: (kwarg) input socket "host:port" - IPv6 addresses must be in format "[host]:port"
        :param str ipprot: (kwarg) IP protocol IPv4 / IPv6
        :param int baudrate: (kwarg) serial baud rate (9600)
        :param int timeout: (kwarg) serial timeout in seconds (3)
        :param int validate: (kwarg) 1 = validate checksums, 0 = do not validate (1)
        :param int msgmode: (kwarg) 0 = GET, 1 = SET, 2 = POLL, 3 = SETPOLL (0)
        :param int parsebitfield: (kwarg) 1 = parse UBX 'X' attributes as bitfields, 0 = leave as bytes (1)
        :param int format: (kwarg) output format 1 = parsed, 2 = raw, 4 = hex, 8 = tabulated hex, 16 = parsed as string, 32 = JSON (1) (can be OR'd)
        :param int quitonerror: (kwarg) 0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors (1)
        :param int protfilter: (kwarg) 1 = NMEA, 2 = UBX, 4 = RTCM3 (7 - ALL)
        :param str msgfilter: (kwarg) comma-separated string of message identities e.g. 'NAV-PVT,GNGSA' (None)
        :param int limit: (kwarg) maximum number of messages to read (0 = unlimited)
        :param object output: (kwarg) either writeable output medium or callback function (None)
        :raises: ParameterError
        """
        # pylint: disable=raise-missing-from

        # Reference to calling application class (if applicable)
        self.__app = app  # pylint: disable=unused-private-member
        # configure logger with name "pygnssutils" in calling module
        self.logger = getLogger(__name__)
        self._reader = None
        self.ctx_mgr = False
        self._datastream = kwargs.get("datastream", None)
        self._port = kwargs.get("port", None)
        self._socket = kwargs.get("socket", None)
        self._ipprot = ipprot2int(kwargs.get("ipprot", "IPv4"))
        self._output = kwargs.get("output", None)

        if self._socket is not None:
            if self._ipprot == AF_INET6:  # IPv6 host ip must be enclosed in []
                sock = self._socket.replace("[", "").split("]")
                if len(sock) != 2:
                    raise ParameterError(
                        "IPv6 socket keyword must be in the format [host]:port"
                    )
                self._socket_host = sock[0]
                self._socket_port = int(sock[1].replace(":", ""))
            else:  # AF_INET
                sock = self._socket.split(":")
                if len(sock) != 2:
                    raise ParameterError(
                        "IPv4 socket keyword must be in the format host:port"
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
            msgfilter = kwargs.get("msgfilter", None)
            self._msgfilter = {}
            if msgfilter is None:
                self._msgfilter = None
            else:
                msgfilter = msgfilter.split(",")
                for msg in msgfilter:
                    filt = msg.strip(")").split("(")
                    if len(filt) == 2:  # identity & period filter
                        self._msgfilter[filt[0]] = (float(filt[1]), 0)
                    else:  # identity filter
                        self._msgfilter[filt[0]] = (0, 0)
            self._limit = int(kwargs.get("limit", 0))
            self._parsing = False
            self._stream = None
            self._msgcount = 0
            self._incount = defaultdict(int)
            self._filtcount = defaultdict(int)
            self._outcount = defaultdict(int)
            self._errcount = 0
            self._validargs = True
            self._stopevent = False

            # flag to signify beginning of JSON array
            self._jsontop = True

        except (ParameterError, ValueError, TypeError) as err:
            raise ParameterError(
                f"Invalid input arguments {kwargs}\n{err}\nType gnssdump -h for help."
            )

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
        # pylint: disable=consider-using-with

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
            with socket(self._ipprot, SOCK_STREAM) as self._stream:
                self._stream.connect(
                    format_conn(self._ipprot, self._socket_host, self._socket_port)
                )
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

        msgs = [
            f"Messages input:    {dict(sorted(self._incount.items()))}",
            f"Messages filtered: {dict(sorted(self._filtcount.items()))}",
            f"Messages output:   {dict(sorted(self._outcount.items()))}",
        ]
        for msg in msgs:
            self.logger.info(msg)

        msg = (
            f"Streaming terminated, {self._msgcount:,} message{mss} "
            f"processed with {self._errcount:,} error{ers}."
        )
        self.logger.info(msg)

    def _start_reader(self):
        """Create UBXReader instance."""

        self._reader = UBXReader(
            self._stream,
            quitonerror=self._quitonerror,
            protfilter=UBX_PROTOCOL | NMEA_PROTOCOL | RTCM3_PROTOCOL,
            validate=self._validate,
            msgmode=self._msgmode,
            parsebitfield=self._parsebitfield,
        )
        self.logger.info(f"Parsing GNSS data stream from: {self._stream}...")

        # if outputting json, add opening tag
        if self._format == FORMAT_JSON:
            self._cap_json(1)

        self._do_parse()

    def _do_parse(self):
        """
        Read the data stream, apply any protocol or msg filters and direct
        to output.

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
                handler = self._output
                msgprot = 0
                # establish the appropriate handler and identity for this protocol
                if isinstance(parsed_data, UBXMessage):
                    msgidentity = parsed_data.identity
                    msgprot = UBX_PROTOCOL
                elif isinstance(parsed_data, NMEAMessage):
                    msgidentity = parsed_data.identity
                    msgprot = NMEA_PROTOCOL
                elif isinstance(parsed_data, RTCMMessage):
                    msgidentity = parsed_data.identity
                    msgprot = RTCM3_PROTOCOL
                else:
                    continue
                self._incount[msgidentity] += 1
                # does it pass the protocol & message identity filter?
                if self._filtered(msgprot, msgidentity):
                    self._filtcount[msgidentity] += 1
                    continue
                self._outcount[msgidentity] += 1
                self._do_output(raw_data, parsed_data, handler)

                if self._limit and self._msgcount >= self._limit:
                    raise EOFError

        except EOFError:  # end of stream
            if not self.ctx_mgr:
                self.stop()

        except Exception as err:  # pylint: disable=broad-except
            self._quitonerror = ERR_RAISE  # don't ignore irrecoverable errors
            self._do_error(err)

    def _filtered(self, protocol: int, identity: str) -> bool:
        """
        Check if this message type is filtered out.
        If per = 0, filter is based on identity.
        If per > 0, filter is based on identity & last output time.

        :param int protocol: msg protocol
        :param str identity: msg identity
        :return: true (excluded) or false (included)
        :rtype: bool
        """

        if self._protfilter & protocol:
            if self._msgfilter is None:
                return False

            if identity in self._msgfilter:
                per, tic = self._msgfilter[identity]
                if per == 0:  # no period filter
                    return False
                toc = time()
                elapsed = toc - tic
                self.logger.debug(
                    f"Time since last {identity} message was sent: {elapsed}"
                )
                # check if at least 95% of filter period has elapsed
                if elapsed >= 0.95 * per:
                    self._msgfilter[identity] = (per, toc)
                    return False

        return True

    def _do_output(self, raw: bytes, parsed: object, handler: object):
        """
        Output message to stdout in specified format(s) OR pass
        to writeable output media / callback function if specified.

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
        # callback function
        else:
            handler(output)

    def _do_print(self, data: object):
        """
        Print data to stdout.

        :param object data: data to print
        """

        print(data)

    def _do_error(self, err: Exception):
        """
        Handle error according to quitonerror flag;
        either ignore, log, or (re)raise.

        :param err Exception: error
        """

        if self._quitonerror == ERR_RAISE:
            raise err
        if self._quitonerror == ERR_LOG:
            self.logger.critical(err)

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

        oph = self._output
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
