"""
gnssreader.py

Generic GNSS class.

Reads and parses individual UBX, SBF, QGC, NMEA or RTCM3 messages from any viable
data stream which supports a read(n) -> bytes method.

It is essentially an amalgamation of the Reader classes in the separate pyubx2, pynmeagps,
pyrtcm, pysbf2 and pyqgc packages.

Returns both the raw binary data (as bytes) and the parsed data.

- 'protfilter' governs which protocols (NMEA, UBX, SBF, QGC or RTCM3) are processed
- 'quitonerror' governs how errors are handled
- 'msgmode' indicates the type of UBX datastream (output GET, input SET, query POLL).
  If msgmode is set to SETPOLL, input/query mode will be automatically detected by parser.

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2020
:license: BSD 3-Clause
"""

# pylint: disable=too-many-positional-arguments

from logging import getLogger
from socket import socket

from pynmeagps import (
    NMEA_HDR,
    NMEAMessageError,
    NMEAParseError,
    NMEAReader,
    NMEAStreamError,
    NMEATypeError,
    SocketWrapper,
)
from pyqgc import (
    QGC_HDR,
    QGCMessageError,
    QGCParseError,
    QGCReader,
    QGCStreamError,
    QGCTypeError,
)
from pyrtcm import (
    RTCMMessageError,
    RTCMParseError,
    RTCMReader,
    RTCMStreamError,
    RTCMTypeError,
)
from pysbf2 import (
    SBF_HDR,
    SBFMessageError,
    SBFParseError,
    SBFReader,
    SBFStreamError,
    SBFTypeError,
)
from pyubx2 import (
    ERR_LOG,
    ERR_RAISE,
    GET,
    POLL,
    SET,
    SETPOLL,
    UBX_HDR,
    VALCKSUM,
    UBXMessageError,
    UBXParseError,
    UBXReader,
    UBXStreamError,
    UBXTypeError,
)

NMEA_PROTOCOL = 1
"""NMEA Protocol"""
UBX_PROTOCOL = 2
"""UBX Protocol"""
RTCM3_PROTOCOL = 4
"""RTCM3 Protocol"""
SBF_PROTOCOL = 8
"""RTCM3 Protocol"""
QGC_PROTOCOL = 16
"""RTCM3 Protocol"""


class StreamError(Exception):
    """Stream Error Class."""


class GNSSReader:
    """
    GNSSReader class.
    """

    def __init__(
        self,
        datastream,
        msgmode: int = GET,
        validate: int = VALCKSUM,
        protfilter: int = NMEA_PROTOCOL
        | UBX_PROTOCOL
        | RTCM3_PROTOCOL
        | SBF_PROTOCOL
        | QGC_PROTOCOL,
        quitonerror: int = ERR_LOG,
        parsebitfield: bool = True,
        labelmsm: int = 1,
        bufsize: int = 4096,
        parsing: bool = True,
        errorhandler: object = None,
    ):
        """Constructor.

        :param datastream stream: input data stream
        :param int msgmode: 0=GET, 1=SET, 2=POLL, 3=SETPOLL (0)
        :param int validate: VALCKSUM (1) = Validate checksum,
            VALNONE (0) = ignore invalid checksum (1)
        :param int protfilter: NMEA_PROTOCOL (1), UBX_PROTOCOL (2), RTCM3_PROTOCOL (4),
            SBF_PROTOCOL (8), QGC_PROTOCOL (16), Can be OR'd (7)
        :param int quitonerror: ERR_IGNORE (0) = ignore errors,  ERR_LOG (1) = log continue,
            ERR_RAISE (2) = (re)raise (1)
        :param bool parsebitfield: 1 = parse bitfields, 0 = leave as bytes (1)
        :param int labelmsm: RTCM3 MSM label type 1 = RINEX, 2 = BAND (1)
        :param int bufsize: socket recv buffer size (4096)
        :param bool parsing: True = parse data, False = don't parse data (output raw only) (True)
        :param object errorhandler: error handling object or function (None)
        :raises: UBXStreamError (if mode is invalid)
        """
        # pylint: disable=too-many-arguments

        if isinstance(datastream, socket):
            self._stream = SocketWrapper(datastream, bufsize=bufsize)
        else:
            self._stream = datastream
        self._protfilter = protfilter
        self._quitonerror = quitonerror
        self._errorhandler = errorhandler
        self._validate = validate
        self._parsebf = parsebitfield
        self._labelmsm = labelmsm
        self._msgmode = msgmode
        self._parsing = parsing
        self._logger = getLogger(__name__)

        if self._msgmode not in (GET, SET, POLL, SETPOLL):
            raise ValueError(
                f"Invalid stream mode {self._msgmode} - must be 0, 1, 2 or 3"
            )

    def __iter__(self):
        """Iterator."""

        return self

    def __next__(self) -> tuple:
        """
        Return next item in iteration.

        :return: tuple of (raw_data as bytes, parsed_data as UBXMessage)
        :rtype: tuple
        :raises: StopIteration

        """

        (raw_data, parsed_data) = self.read()
        if raw_data is None and parsed_data is None:
            raise StopIteration
        return (raw_data, parsed_data)

    def read(self) -> tuple:
        """
        Read a single NMEA, UBX or RTCM3 message from the stream buffer
        and return both raw and parsed data.

        'protfilter' determines which protocols are parsed.
        'quitonerror' determines whether to raise, log or ignore parsing errors.

        :return: tuple of (raw_data as bytes, parsed_data as UBXMessage, NMEAMessage or RTCMMessage)
        :rtype: tuple
        :raises: Exception (if invalid or unrecognised protocol in data stream)
        """

        parsing = True
        while parsing:  # loop until end of valid message or EOF
            try:

                raw_data = None
                parsed_data = None
                byte1 = self._read_bytes(1)  # read the first byte
                # if not UBX, SBF, QGC, NMEA or RTCM3, discard and continue
                if byte1 not in (b"\xb5", b"\x24", b"\x51", b"\xd3"):
                    continue
                byte2 = self._read_bytes(1)
                bytehdr = byte1 + byte2
                # if it's a UBX message (b'\xb5\x62')
                if bytehdr == UBX_HDR:
                    (raw_data, parsed_data) = self._parse_ubx(bytehdr)
                    # if protocol filter passes UBX, return message,
                    # otherwise discard and continue
                    if self._protfilter & UBX_PROTOCOL:
                        parsing = False
                    else:
                        continue
                # if it's an NMEA message (b'\x24\x..)
                elif bytehdr in NMEA_HDR:
                    (raw_data, parsed_data) = self._parse_nmea(bytehdr)
                    # if protocol filter passes NMEA, return message,
                    # otherwise discard and continue
                    if self._protfilter & NMEA_PROTOCOL:
                        parsing = False
                    else:
                        continue
                # if it's an SBF message (b'\x24\x40')
                elif bytehdr in SBF_HDR:
                    (raw_data, parsed_data) = self._parse_sbf(bytehdr)
                    # if protocol filter passes SBF, return message,
                    # otherwise discard and continue
                    if self._protfilter & SBF_PROTOCOL:
                        parsing = False
                    else:
                        continue
                # if it's an QGCmessage (b'\x51\x47')
                elif bytehdr in QGC_HDR:
                    (raw_data, parsed_data) = self._parse_qgc(bytehdr)
                    # if protocol filter passes QGC, return message,
                    # otherwise discard and continue
                    if self._protfilter & QGC_PROTOCOL:
                        parsing = False
                    else:
                        continue
                # if it's a RTCM3 message
                # (byte1 = 0xd3; byte2 = 0b000000**)
                elif byte1 == b"\xd3" and (byte2[0] & ~0x03) == 0:
                    (raw_data, parsed_data) = self._parse_rtcm3(bytehdr)
                    # if protocol filter passes RTCM, return message,
                    # otherwise discard and continue
                    if self._protfilter & RTCM3_PROTOCOL:
                        parsing = False
                    else:
                        continue
                # unrecognised protocol header
                else:
                    raise ValueError(f"Unknown protocol header {bytehdr}.")

            except EOFError:
                return (None, None)
            except (
                UBXMessageError,
                UBXTypeError,
                UBXParseError,
                UBXStreamError,
                NMEAMessageError,
                NMEATypeError,
                NMEAParseError,
                NMEAStreamError,
                RTCMMessageError,
                RTCMParseError,
                RTCMStreamError,
                RTCMTypeError,
                SBFMessageError,
                SBFParseError,
                SBFStreamError,
                SBFTypeError,
                QGCMessageError,
                QGCParseError,
                QGCStreamError,
                QGCTypeError,
                StreamError,
            ) as err:
                if self._quitonerror:
                    self._do_error(err)
                continue

        return (raw_data, parsed_data)

    def _parse_ubx(self, hdr: bytes) -> tuple:
        """
        Parse remainder of UBX message.

        :param bytes hdr: UBX header (b'\\xb5\\x62')
        :return: tuple of (raw_data as bytes, parsed_data as UBXMessage or None)
        :rtype: tuple
        """

        # read the rest of the UBX message from the buffer
        byten = self._read_bytes(4)
        clsid = byten[0:1]
        msgid = byten[1:2]
        lenb = byten[2:4]
        leni = int.from_bytes(lenb, "little", signed=False)
        byten = self._read_bytes(leni + 2)
        plb = byten[0:leni]
        cksum = byten[leni : leni + 2]
        raw_data = hdr + clsid + msgid + lenb + plb + cksum
        # only parse if we need to (filter passes UBX)
        if (self._protfilter & UBX_PROTOCOL) and self._parsing:
            parsed_data = UBXReader.parse(
                raw_data,
                validate=self._validate,
                msgmode=self._msgmode,
                parsebitfield=self._parsebf,
            )
        else:
            parsed_data = None
        return (raw_data, parsed_data)

    def _parse_sbf(self, hdr: bytes) -> tuple:
        """
        Parse remainder of SBF message.

        :param bytes hdr: SBF header (b'\\x24\\x40')
        :return: tuple of (raw_data as bytes, parsed_data as SBFMessage or None)
        :rtype: tuple
        """

        # read the rest of the SBF message from the buffer
        byten = self._read_bytes(6)
        crc = byten[0:2]
        msgid = byten[2:4]
        lenb = byten[4:6]
        # lenb includes 8 byte header
        leni = int.from_bytes(lenb, "little", signed=False) - 8
        plb = self._read_bytes(leni)
        raw_data = hdr + crc + msgid + lenb + plb
        # only parse if we need to (filter passes SBF)
        if (self._protfilter & SBF_PROTOCOL) and self._parsing:
            parsed_data = SBFReader.parse(
                raw_data,
                validate=self._validate,
                parsebitfield=self._parsebf,
            )
        else:
            parsed_data = None
        return (raw_data, parsed_data)

    def _parse_qgc(self, hdr: bytes) -> tuple:
        """
        Parse remainder of QGC message.

        :param bytes hdr: QGC header (b'\\x51\\x47')
        :return: tuple of (raw_data as bytes, parsed_data as QGCMessage or None)
        :rtype: tuple
        """

        # read the rest of the QGC message from the buffer
        byten = self._read_bytes(4)
        msggrp = byten[0:1]
        msgid = byten[1:2]
        lenb = byten[2:4]
        leni = int.from_bytes(lenb, "little", signed=False)
        byten = self._read_bytes(leni + 2)
        plb = byten[0:leni]
        cksum = byten[leni : leni + 2]
        raw_data = hdr + msggrp + msgid + lenb + plb + cksum
        # only parse if we need to (filter passes QGC)
        if (self._protfilter & QGC_PROTOCOL) and self._parsing:
            parsed_data = QGCReader.parse(
                raw_data,
                msgmode=self._msgmode,
                validate=self._validate,
                parsebitfield=self._parsebf,
            )
        else:
            parsed_data = None
        return (raw_data, parsed_data)

    def _parse_nmea(self, hdr: bytes) -> tuple:
        """
        Parse remainder of NMEA message (using pynmeagps library).

        :param bytes hdr: NMEA header (b'\\x24\\x..')
        :return: tuple of (raw_data as bytes, parsed_data as NMEAMessage or None)
        :rtype: tuple
        """

        # read the rest of the NMEA message from the buffer
        byten = self._read_line()  # NMEA protocol is CRLF-terminated
        raw_data = hdr + byten
        # only parse if we need to (filter passes NMEA)
        if (self._protfilter & NMEA_PROTOCOL) and self._parsing:
            # invoke pynmeagps parser
            parsed_data = NMEAReader.parse(
                raw_data,
                validate=self._validate,
                msgmode=self._msgmode,
            )
        else:
            parsed_data = None
        return (raw_data, parsed_data)

    def _parse_rtcm3(self, hdr: bytes) -> tuple:
        """
        Parse any RTCM3 data in the stream (using pyrtcm library).

        :param bytes hdr: first 2 bytes of RTCM3 header
        :return: tuple of (raw_data as bytes, parsed_stub as RTCMMessage)
        :rtype: tuple
        """

        hdr3 = self._read_bytes(1)
        size = hdr3[0] | (hdr[1] << 8)
        payload = self._read_bytes(size)
        crc = self._read_bytes(3)
        raw_data = hdr + hdr3 + payload + crc
        # only parse if we need to (filter passes RTCM)
        if (self._protfilter & RTCM3_PROTOCOL) and self._parsing:
            # invoke pyrtcm parser
            parsed_data = RTCMReader.parse(
                raw_data,
                validate=self._validate,
                labelmsm=self._labelmsm,
            )
        else:
            parsed_data = None
        return (raw_data, parsed_data)

    def _read_bytes(self, size: int) -> bytes:
        """
        Read a specified number of bytes from stream.

        :param int size: number of bytes to read
        :return: bytes
        :rtype: bytes
        :raises: UBXStreamError if stream ends prematurely
        """

        data = self._stream.read(size)
        if len(data) == 0:  # EOF
            raise EOFError()
        if 0 < len(data) < size:  # truncated stream
            raise StreamError(
                "Serial stream terminated unexpectedly. "
                f"{size} bytes requested, {len(data)} bytes returned."
            )
        return data

    def _read_line(self) -> bytes:
        """
        Read bytes until LF (0x0a) terminator.

        :return: bytes
        :rtype: bytes
        :raises: UBXStreamError if stream ends prematurely
        """

        data = self._stream.readline()  # NMEA protocol is CRLF-terminated
        if len(data) == 0:
            raise EOFError()  # pragma: no cover
        if data[-1:] != b"\x0a":  # truncated stream
            raise StreamError(
                "Serial stream terminated unexpectedly. "
                f"Line requested, {len(data)} bytes returned."
            )
        return data

    def _do_error(self, err: Exception):
        """
        Handle error.

        :param Exception err: error
        :raises: Exception if quitonerror = ERR_RAISE (2)
        """

        if self._quitonerror == ERR_RAISE:
            raise err from err
        if self._quitonerror == ERR_LOG:
            # pass to error handler if there is one
            # else just log
            if self._errorhandler is None:
                self._logger.error(err)
            else:
                self._errorhandler(err)

    @property
    def datastream(self) -> object:
        """
        Getter for stream.

        :return: data stream
        :rtype: object
        """

        return self._stream
