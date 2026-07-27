"""
gnssreader.py

Generic GNSS reader / parser class.

Reads and parses individual UBX, SBF, QGC, UNI, NMEA or RTCM3 messages from any viable
GNSS data stream which supports a read(n) -> bytes method.

It is essentially an amalgamation of the Reader classes in the separate pyubx2, pynmeagps,
pyrtcm, pysbf2, pyqgc and pyunigps packages.

Returns both the raw binary data (as bytes) and the parsed data.

- 'protfilter' governs which protocols (NMEA, UBX, SBF, QGC, UNI or RTCM3) are processed.
- 'msgfilter' governs which individual message types are processed.
- `parsing` governs whether payloads are fully or partially parsed.
- 'quitonerror' governs how errors are handled.
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
from types import FunctionType, NoneType
from typing import Any, Literal

from pynmeagps import (
    NMEA_HDR,
    NMEAMessage,
    NMEAMessageError,
    NMEAParseError,
    NMEAReader,
    NMEAStreamError,
    NMEATypeError,
    SocketWrapper,
)
from pyqgc import (
    QGC_HDR,
    QGCMessage,
    QGCMessageError,
    QGCParseError,
    QGCReader,
    QGCStreamError,
    QGCTypeError,
)
from pyrtcm import (
    RTCMMessage,
    RTCMMessageError,
    RTCMParseError,
    RTCMReader,
    RTCMStreamError,
    RTCMTypeError,
)
from pysbf2 import (
    SBF_HDR,
    SBFMessage,
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
    UBXMessage,
    UBXMessageError,
    UBXParseError,
    UBXReader,
    UBXStreamError,
    UBXTypeError,
    escapeall,
)
from pyunigps import (
    UNI_HDR,
    UNIMessage,
    UNIMessageError,
    UNIParseError,
    UNIReader,
    UNIStreamError,
    UNITypeError,
)

from pygnssutils.exceptions import GNSSStreamError
from pygnssutils.globals import DEFAULT_BUFSIZE

NMEA_PROTOCOL = 1
"""NMEA Protocol"""
UBX_PROTOCOL = 2
"""UBX Protocol (u-blox)"""
RTCM3_PROTOCOL = 4
"""RTCM3 Protocol"""
SBF_PROTOCOL = 8
"""RTCM3 Protocol (Septentrio)"""
QGC_PROTOCOL = 16
"""QGC Protocol (Quectel)"""
UNI_PROTOCOL = 32
"""UNI Protocol (Unicore)"""
PARSE_NONE = 0
"""No Parsing, raw output only"""
PARSE_FULL = 1
"""Full parsing of all attributes"""
PARSE_META = 2
"""Parse protocol and message Id only"""

PROTOCOLS = {
    NMEA_PROTOCOL: "NMEA",
    UBX_PROTOCOL: "UBX",
    RTCM3_PROTOCOL: "RTCM",
    SBF_PROTOCOL: "SBF",
    QGC_PROTOCOL: "QGC",
    UNI_PROTOCOL: "UNI",
}


class GNSSMessage:
    """
    Generic GNSSMessage class.

    Holds partially parsed GNSS binary messages (`parsing=2`).
    """

    def __init__(self, protocol: int, msgid: int | str, data: bytes):
        """
        Constructor

        :param int protocol: GNSS protocol e.g. 2 (=UBX)
        :param int | str msgid: GNSS message id e.g. 0x0215 or "GNGSA"
        :param bytes data: raw data from original message
        """

        self._protocol = protocol
        self._identity = msgid
        self._data = data

    def __str__(self) -> str:
        """
        Human readable representation.

        :return: human readable representation
        :rtype: str
        """

        prot = PROTOCOLS.get(self._protocol, "UNKNOWN")
        ident = (
            f"0x{self._identity:04x}"
            if self._protocol in (UBX_PROTOCOL, QGC_PROTOCOL)
            else self._identity
        )
        return f"<{prot}({ident}, length={self.length}, data={escapeall(self._data)})>"

    def __repr__(self) -> str:
        """
        Machine readable representation.

        eval(repr(obj)) = obj

        :return: machine readable representation
        :rtype: str

        """

        ident = (
            f"'{self._identity}'"
            if isinstance(self._identity, str)
            else f"{self._identity}"
        )
        return f"GNSSMessage({self._protocol}, {ident}, {self._data})"

    @property
    def protocol(self) -> int:
        """
        Getter for protocol.
        """

        return self._protocol

    @property
    def identity(self) -> int | str:
        """
        Getter for identity.
        """

        return self._identity

    @property
    def data(self) -> bytes:
        """
        Getter for raw data.
        """

        return self._data

    @property
    def length(self) -> int:
        """
        Getter for length of original raw data.
        """

        return len(self._data)


class GNSSReader:
    """
    GNSSReader class.
    """

    def __init__(
        self,
        datastream,
        msgmode: Literal[0, 1, 2] = GET,
        validate: int = VALCKSUM,
        protfilter: int = NMEA_PROTOCOL
        | UBX_PROTOCOL
        | RTCM3_PROTOCOL
        | SBF_PROTOCOL
        | QGC_PROTOCOL
        | UNI_PROTOCOL,
        quitonerror: Literal[0, 1, 2] = ERR_LOG,
        parsebitfield: bool = True,
        labelmsm: Literal[0, 1] = 1,
        bufsize: int = DEFAULT_BUFSIZE,
        parsing: Literal[0, 1, 2] = PARSE_FULL,
        msgfilter: tuple | int | str = "",
        errorhandler: FunctionType | NoneType = None,
    ):
        """Constructor.

        :param datastream stream: input data stream
        :param Literal[0,1,2]  msgmode: 0=GET, 1=SET, 2=POLL, 3=SETPOLL (0)
        :param int validate: VALCKSUM (1) = Validate checksum,
            VALNONE (0) = ignore invalid checksum (1)
        :param int protfilter: NMEA_PROTOCOL (1), UBX_PROTOCOL (2), RTCM3_PROTOCOL (4),
            SBF_PROTOCOL (8), QGC_PROTOCOL (16), UNI_PROTOCOL (32). Can be OR'd (63)
        :param Literal[0,1,2]  quitonerror: ERR_IGNORE (0) = ignore errors, \
            ERR_LOG (1) = log continue, ERR_RAISE (2) = (re)raise (1)
        :param bool parsebitfield: 1 = parse bitfields, 0 = leave as bytes (1)
        :param Literal[0,1] labelmsm: RTCM3 MSM label type 1 = RINEX, 2 = BAND (1)
        :param int bufsize: socket recv buffer size (4096)
        :param Literal[0,1,2] parsing: PARSE_NONE (0) = no parsing (raw only), \
            PARSE_FULL (1) = full parsing, PARSE_META (2) = parse metadata only (1)
        :param tuple | int | str msgfilter: parsed message filter ("" = ALL)
        :param FunctionType | NoneType errorhandler: error handling object or function (None)
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
        self._msgfilter = (
            (msgfilter,) if not isinstance(msgfilter, tuple) else msgfilter
        )
        self._filtermsg = self._msgfilter not in ((), ("",))
        self._logger = getLogger(__name__)

        if self._msgmode not in (GET, SET, POLL, SETPOLL):
            raise ValueError(
                f"Invalid stream mode {self._msgmode} - must be 0, 1, 2 or 3"
            )

    def __iter__(self):
        """Iterator."""

        return self

    def __next__(self) -> tuple[bytes | NoneType, Any]:
        """
        Return next item in iteration.

        :return: tuple of (raw_data as bytes, parsed_data as UBXMessage)
        :rtype: tuple[bytes | NoneType, Any]
        :raises: StopIteration

        """

        raw_data, parsed_data = self.read()
        if raw_data is None and parsed_data is None:
            raise StopIteration
        return raw_data, parsed_data

    def read(self) -> tuple[bytes | NoneType, Any]:
        """
        Read a single NMEA, UBX, SBF, QGC, UNI or RTCM3 message from the stream buffer
        and return both raw and parsed data.

        'protfilter' determines which protocols are parsed.
        'quitonerror' determines whether to raise, log or ignore parsing errors.

        :return: tuple of (raw_data as bytes, parsed_data as NMEAMessage, UBXMessage,
            SBFMessage, QGCMessage, UNIMessage, RTCMMessage or (if `parsing=2`) GNSSMessage)
        :rtype: tuple[bytes | NoneType, Any]
        :raises: Exception (if invalid or unrecognised protocol in data stream)
        """

        raw_data = None
        parsed_data = None
        parsing = True
        while parsing:  # loop until end of valid message or EOF
            try:

                raw_data = None
                parsed_data = None
                byte1 = self._read_bytes(1)  # read the first byte
                # if not UBX, SBF, QGC, UNI, NMEA or RTCM3, discard and continue
                if byte1 not in (b"\xb5", b"\x24", b"\x51", b"\xd3", b"\xaa"):
                    continue
                byte2 = self._read_bytes(1)
                bytehdr = byte1 + byte2
                # if it's a UBX message (b'\xb5\x62')
                if bytehdr == UBX_HDR:
                    raw_data, parsed_data = self._parse_ubx(bytehdr)
                    # if protocol filter passes UBX, return message,
                    # otherwise discard and continue
                    if self._protfilter & UBX_PROTOCOL:
                        parsing = False
                    else:
                        continue
                # if it's an NMEA message (b'\x24\x..)
                elif bytehdr in NMEA_HDR:
                    raw_data, parsed_data = self._parse_nmea(bytehdr)
                    # if protocol filter passes NMEA, return message,
                    # otherwise discard and continue
                    if self._protfilter & NMEA_PROTOCOL:
                        parsing = False
                    else:
                        continue
                # if it's an SBF message (b'\x24\x40')
                elif bytehdr in SBF_HDR:
                    raw_data, parsed_data = self._parse_sbf(bytehdr)
                    # if protocol filter passes SBF, return message,
                    # otherwise discard and continue
                    if self._protfilter & SBF_PROTOCOL:
                        parsing = False
                    else:
                        continue
                # if it's an QGCmessage (b'\x51\x47')
                elif bytehdr in QGC_HDR:
                    raw_data, parsed_data = self._parse_qgc(bytehdr)
                    # if protocol filter passes QGC, return message,
                    # otherwise discard and continue
                    if self._protfilter & QGC_PROTOCOL:
                        parsing = False
                    else:
                        continue
                # if it's an UNImessage (b'\xaa\x44\xb5')
                elif bytehdr in UNI_HDR[:2]:
                    byte3 = self._read_bytes(1)
                    bytehdr += byte3
                    if bytehdr != UNI_HDR:
                        continue
                    raw_data, parsed_data = self._parse_uni(bytehdr)
                    # if protocol filter passes UNI, return message,
                    # otherwise discard and continue
                    if self._protfilter & UNI_PROTOCOL:
                        parsing = False
                    else:
                        continue
                # if it's a RTCM3 message
                # (byte1 = 0xd3; byte2 = 0b000000**)
                elif byte1 == b"\xd3" and (byte2[0] & ~0x03) == 0:
                    raw_data, parsed_data = self._parse_rtcm3(bytehdr)
                    # if protocol filter passes RTCM, return message,
                    # otherwise discard and continue
                    if self._protfilter & RTCM3_PROTOCOL:
                        parsing = False
                    else:
                        continue
                else:
                    raise GNSSStreamError(f"Unknown protocol header {bytehdr}.")

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
                UNIMessageError,
                UNIParseError,
                UNIStreamError,
                UNITypeError,
                GNSSStreamError,
            ) as err:
                if self._quitonerror:
                    self._do_error(err)
                continue

        return raw_data, parsed_data

    def _parse_ubx(
        self, hdr: bytes
    ) -> tuple[bytes, UBXMessage | GNSSMessage | NoneType]:
        """
        Parse UBX message (using pyubx2).

        :param bytes hdr: UBX header (b'\\xb5\\x62')
        :return: tuple of (raw_data as bytes, parsed_data as UBXMessage or None)
        :rtype: tuple[bytes, UBXMessage | GNSSMessage | NoneType]
        """

        # read the rest of the UBX message from the buffer
        byten = self._read_bytes(4)
        msgid = byten[0:2]
        msgidi = int.from_bytes(msgid, "big")  # UBX msgids are documented in big endian
        lenb = byten[2:4]
        leni = int.from_bytes(lenb, "little", signed=False)
        paycrc = self._read_bytes(leni + 2)
        raw_data = hdr + msgid + lenb + paycrc
        # only parse if we need to (filter passes UBX)
        parsed_data = None
        if self._protfilter & UBX_PROTOCOL and (
            not self._filtermsg or msgidi in self._msgfilter
        ):
            if self._parsing == PARSE_FULL:
                parsed_data = UBXReader.parse(
                    raw_data,
                    validate=self._validate,
                    msgmode=self._msgmode,
                    parsebitfield=self._parsebf,
                )
            elif self._parsing == PARSE_META:
                parsed_data = GNSSMessage(UBX_PROTOCOL, msgidi, raw_data)
        return raw_data, parsed_data

    def _parse_sbf(
        self, hdr: bytes
    ) -> tuple[bytes, SBFMessage | GNSSMessage | NoneType]:
        """
        Parse SBF message (using pysbf2).

        :param bytes hdr: SBF header (b'\\x24\\x40')
        :return: tuple of (raw_data as bytes, parsed_data as SBFMessage or None)
        :rtype: tuple[bytes, SBFMessage | GNSSMessage | NoneType]
        """

        # read the rest of the SBF message from the buffer
        byten = self._read_bytes(6)
        crc = byten[0:2]
        msgid = byten[2:4]
        msgidi = int.from_bytes(msgid, "little") & 0x1FFF
        lenb = byten[4:6]
        # lenb includes 8 byte header
        leni = int.from_bytes(lenb, "little", signed=False) - 8
        plb = self._read_bytes(leni)
        raw_data = hdr + crc + msgid + lenb + plb
        # only parse if we need to (filter passes SBF)
        parsed_data = None
        if self._protfilter & SBF_PROTOCOL and (
            not self._filtermsg or msgidi in self._msgfilter
        ):
            if self._parsing == PARSE_FULL:
                parsed_data = SBFReader.parse(
                    raw_data,
                    validate=self._validate,
                    parsebitfield=self._parsebf,
                )
            elif self._parsing == PARSE_META:
                parsed_data = GNSSMessage(SBF_PROTOCOL, msgidi, raw_data)
        return raw_data, parsed_data

    def _parse_uni(
        self, hdr: bytes
    ) -> tuple[bytes, UNIMessage | GNSSMessage | NoneType]:
        """
        Parse binary UNI message.

        :param bytes hdr: UNI header (b'\\xaa\\x44\\xb5')
        :return: tuple of (raw_data as bytes, parsed_data as UNIMessage or None)
        :rtype: tuple[bytes, UNIMessage | GNSSMessage | NoneType]
        """

        header = self._read_bytes(21)
        leni = int.from_bytes(header[3:5], "little")
        payload = self._read_bytes(leni + 4)
        msgidi = int.from_bytes(header[1:3], "little")
        raw_data = hdr + header + payload
        # only parse if we need to (filter passes UNI)
        parsed_data = None
        if self._protfilter & UNI_PROTOCOL and (
            not self._filtermsg or msgidi in self._msgfilter
        ):
            if self._parsing == PARSE_FULL:
                parsed_data = UNIReader.parse(
                    raw_data,
                    validate=self._validate,
                    msgmode=self._msgmode,
                    parsebitfield=self._parsebf,
                )
            elif self._parsing == PARSE_META:
                parsed_data = GNSSMessage(UNI_PROTOCOL, msgidi, raw_data)
        return raw_data, parsed_data

    def _parse_qgc(
        self, hdr: bytes
    ) -> tuple[bytes, QGCMessage | GNSSMessage | NoneType]:
        """
        Parse QGC message (using pyqgc).

        :param bytes hdr: QGC header (b'\\x51\\x47')
        :return: tuple of (raw_data as bytes, parsed_data as QGCMessage or None)
        :rtype: tuple[bytes, QGCMessage | GNSSMessage | NoneType]
        """

        # read the rest of the QGC message from the buffer
        byten = self._read_bytes(4)
        msgid = byten[0:2]
        msgidi = int.from_bytes(msgid, "big")  # QCG msgids are documented in big endian
        lenb = byten[2:4]
        leni = int.from_bytes(lenb, "little", signed=False)
        paycrc = self._read_bytes(leni + 2)
        raw_data = hdr + msgid + lenb + paycrc
        # only parse if we need to (filter passes QGC)
        parsed_data = None
        if self._protfilter & QGC_PROTOCOL and (
            not self._filtermsg or msgidi in self._msgfilter
        ):
            if self._parsing == PARSE_FULL:
                parsed_data = QGCReader.parse(
                    raw_data,
                    validate=self._validate,
                    msgmode=self._msgmode,
                    parsebitfield=self._parsebf,
                )
            elif self._parsing == PARSE_META:
                parsed_data = GNSSMessage(QGC_PROTOCOL, msgidi, raw_data)
        return raw_data, parsed_data

    def _parse_nmea(
        self, hdr: bytes
    ) -> tuple[bytes, NMEAMessage | GNSSMessage | NoneType]:
        """
        Parse NMEA message (using pynmeagps).

        :param bytes hdr: NMEA header (b'\\x24\\x..')
        :return: tuple of (raw_data as bytes, parsed_data as NMEAMessage or None)
        :rtype: tuple[bytes, NMEAMessage | GNSSMessage | NoneType]
        """

        # read the rest of the NMEA message from the buffer
        byten = self._read_line()  # NMEA protocol is CRLF-terminated
        raw_data = hdr + byten
        msgids = (
            raw_data[1:].decode("utf-8", errors="backslashreplace").split(",", 1)[0]
        )
        # only parse if we need to (filter passes NMEA)
        parsed_data = None
        if self._protfilter & NMEA_PROTOCOL and (
            not self._filtermsg or msgids in self._msgfilter
        ):
            if self._parsing == PARSE_FULL:
                parsed_data = NMEAReader.parse(
                    raw_data,
                    validate=self._validate,
                    msgmode=self._msgmode,
                )
            elif self._parsing == PARSE_META:
                parsed_data = GNSSMessage(NMEA_PROTOCOL, msgids, raw_data)
        return raw_data, parsed_data

    def _parse_rtcm3(
        self, hdr: bytes
    ) -> tuple[bytes, RTCMMessage | GNSSMessage | NoneType]:
        """
        Parse RTCM3 message (using pyrtcm).

        :param bytes hdr: first 2 bytes of RTCM3 header
        :return: tuple of (raw_data as bytes, parsed_stub as RTCMMessage)
        :rtype: tuple[bytes, RTCMMessage | GNSSMessage | NoneType]
        """

        hdr3 = self._read_bytes(1)
        size = hdr3[0] | (hdr[1] << 8)
        payload = self._read_bytes(size)
        msgidi = ((int.from_bytes(payload[0:2], "big")) >> 4) & 0xFFF
        crc = self._read_bytes(3)
        raw_data = hdr + hdr3 + payload + crc
        # only parse if we need to (filter passes RTCM)
        parsed_data = None
        if self._protfilter & RTCM3_PROTOCOL and (
            not self._filtermsg or msgidi in self._msgfilter
        ):
            if self._parsing == PARSE_FULL:
                parsed_data = RTCMReader.parse(
                    raw_data,
                    validate=self._validate,
                    labelmsm=self._labelmsm,
                )
            elif self._parsing == PARSE_META:
                parsed_data = GNSSMessage(RTCM3_PROTOCOL, msgidi, raw_data)
        return raw_data, parsed_data

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
            raise GNSSStreamError(
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
            raise GNSSStreamError(
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
