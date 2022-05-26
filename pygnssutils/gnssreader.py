"""
GNSSReader class.

Reads and parses individual UBX, NMEA or RTCM3 messages from any stream
which supports a read(n) -> bytes method.

Returns both the raw binary data (as bytes) and the parsed data
(as a UBXMessage, NMEAMessage or RTCMMessage object).

'protfilter' governs which protocols (NMEA, UBX or RTCM3) are processed
'quitonerror' governs how errors are handled

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""
# pylint: disable=line-too-long

from socket import socket
from pynmeagps import NMEAReader
import pynmeagps.exceptions as nme
from pyubx2 import UBXReader
import pyubx2.exceptions as ube
from pyrtcm import RTCMReader
import pyrtcm.exceptions as rte
from pygnssutils.socket_stream import SocketStream
from pygnssutils.globals import (
    NMEA_HDR,
    UBX_HDR,
    NMEA_PROTOCOL,
    UBX_PROTOCOL,
    RTCM3_PROTOCOL,
    ERR_LOG,
    ERR_RAISE,
    VALCKSUM,
)
from pygnssutils.exceptions import GNSSStreamError, ParameterError


class GNSSReader:
    """
    GNSSReader class - reads NMEA, UBX and RTCM3 data from an input stream.
    """

    def __init__(self, datastream, **kwargs):
        """Constructor.

        :param datastream stream: input data stream
        :param int quitonerror: (kwarg) 0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors (1)
        :param int protfilter: (kwarg) protocol filter 1 = NMEA, 2 = UBX, 4 = RTCM3 (3)
        :param int validate: (kwarg) 0 = ignore invalid checksum, 1 = validate checksum (1)
        :param int msgmode: (kwarg) 0=GET, 1=SET, 2=POLL (0)
        :param bool parsebitfield: (kwarg) 1 = parse UBX bitfields, 0 = leave as bytes (1)
        :param bool scaling: (kwarg) 1 = apply scale factors, 0 = do not apply (1)
        :param int bufsize: (kwarg) socket recv buffer size (1024)
        :raises: UBXStreamError (if mode is invalid)

        """

        bufsize = int(kwargs.get("bufsize", 4096))
        if isinstance(datastream, socket):
            self._stream = SocketStream(datastream, bufsize=bufsize)
        else:
            self._stream = datastream
        self._protfilter = int(
            kwargs.get("protfilter", NMEA_PROTOCOL | UBX_PROTOCOL | RTCM3_PROTOCOL)
        )
        self._quitonerror = int(kwargs.get("quitonerror", ERR_LOG))
        self._validate = int(kwargs.get("validate", VALCKSUM))
        self._parsebf = int(kwargs.get("parsebitfield", True))
        self._scaling = int(kwargs.get("scaling", True))
        self._msgmode = int(kwargs.get("msgmode", 0))

        if self._msgmode not in (0, 1, 2):
            raise ParameterError(
                f"Invalid stream mode {self._msgmode} - must be 0, 1 or 2"
            )

    def __iter__(self):
        """Iterator."""

        return self

    def __next__(self) -> tuple:
        """
        Return next item in iteration.

        :return: tuple of (raw_data as bytes, parsed_data as object)
        :rtype: tuple
        :raises: StopIteration

        """

        (raw_data, parsed_data) = self.read()
        if raw_data is not None:
            return (raw_data, parsed_data)
        raise StopIteration

    def read(self) -> tuple:
        """
        Read a single NMEA, UBX or RTCM3 message from the stream buffer
        and return both raw and parsed data.

        'protfilter' determines which protocols are parsed.
        'quitonerror' determines whether to raise, log or ignore parsing errors.

        :return: tuple of (raw_data as bytes, parsed_data as object)
        :rtype: tuple
        :raises: GNSSStreamError (if unrecognised protocol in data stream)
        """

        parsing = True

        try:
            while parsing:  # loop until end of valid message or EOF
                raw_data = None
                parsed_data = None
                byte1 = self._read_bytes(1)  # read the first byte
                # if not UBX, NMEA or RTCM3, discard and continue
                if byte1 not in (b"\xb5", b"\x24", b"\xd3"):
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
                # if it's an NMEA message ('$G' or '$P')
                elif bytehdr in NMEA_HDR:
                    (raw_data, parsed_data) = self._parse_nmea(bytehdr)
                    # if protocol filter passes NMEA, return message,
                    # otherwise discard and continue
                    if self._protfilter & NMEA_PROTOCOL:
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
                    if self._quitonerror == ERR_RAISE:
                        raise GNSSStreamError(f"Unknown protocol {bytehdr}.")
                    if self._quitonerror == ERR_LOG:
                        return (bytehdr, f"<UNKNOWN PROTOCOL(header={bytehdr})>")
                    continue

        except EOFError:
            return (None, None)

        return (raw_data, parsed_data)

    def _parse_ubx(self, hdr: bytes) -> tuple:
        """
        Parse remainder of UBX message (using pyubx2 library).

        :param bytes hdr: UBX header (b'\xb5\x62')
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
        if self._protfilter & UBX_PROTOCOL:
            parsed_data = UBXReader.parse(
                raw_data,
                validate=self._validate,
                msgmode=self._msgmode,
                parsebitfield=self._parsebf,
                scaling=self._scaling,
            )
        else:
            parsed_data = None
        return (raw_data, parsed_data)

    def _parse_nmea(self, hdr: bytes) -> tuple:
        """
        Parse remainder of NMEA message (using pynmeagps library).

        :param bytes hdr: NMEA header ($G or $P)
        :return: tuple of (raw_data as bytes, parsed_data as NMEAMessage or None)
        :rtype: tuple
        """

        # read the rest of the NMEA message from the buffer
        byten = self._stream.readline()  # NMEA protocol is CRLF-terminated
        if byten[-2:] != b"\x0d\x0a":
            raise EOFError()
        raw_data = hdr + byten
        # only parse if we need to (filter passes NMEA)
        if self._protfilter & NMEA_PROTOCOL:
            # invoke pynmeagps parser
            parsed_data = NMEAReader.parse(
                raw_data,
                validate=self._validate,
                msgmode=self._msgmode,
            )
        else:
            parsed_data = None
        return (raw_data, parsed_data)

    def _parse_rtcm3(self, hdr: bytes, **kwargs) -> tuple:
        """
        Parse any RTCM3 data in the stream (using pyrtcm library).

        :param bytes hdr: first 2 bytes of RTCM3 header
        :param bool validate: (kwarg) validate crc Y/N
        :return: tuple of (raw_data as bytes, parsed_stub as RTCMMessage)
        :rtype: tuple
        """

        hdr3 = self._read_bytes(1)
        size = hdr3[0] | (hdr[1] << 8)
        payload = self._read_bytes(size)
        crc = self._read_bytes(3)
        raw_data = hdr + hdr3 + payload + crc
        # only parse if we need to (filter passes RTCM)
        if self._protfilter & RTCM3_PROTOCOL:
            # invoke pyrtcm parser
            parsed_data = RTCMReader.parse(
                raw_data,
                validate=self._validate,
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
        :raises: EOFError if stream ends prematurely
        """

        data = self._stream.read(size)
        if len(data) < size:  # EOF
            raise EOFError()
        return data

    def iterate(self, **kwargs) -> tuple:
        """
        Invoke the iterator within an exception handling framework.

        :param int quitonerror: (kwarg) 0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors (1)
        :param object errorhandler: (kwarg) Optional error handler (None)
        :return: tuple of (raw_data as bytes, parsed_data as UBXMessage or NMEAMessage)
        :rtype: tuple
        :raises: UBX/NMEA...Error (if quitonerror is set and stream is invalid)

        """

        quitonerror = kwargs.get("quitonerror", self._quitonerror)
        errorhandler = kwargs.get("errorhandler", None)

        while True:
            try:
                yield next(self)  # invoke the iterator
            except StopIteration:
                break
            except (
                ube.UBXMessageError,
                ube.UBXTypeError,
                ube.UBXParseError,
                ube.UBXStreamError,
                nme.NMEAMessageError,
                nme.NMEATypeError,
                nme.NMEAParseError,
                nme.NMEAStreamError,
                rte.RTCMMessageError,
                rte.RTCMParseError,
                rte.RTCMStreamError,
                rte.RTCMTypeError,
            ) as err:
                # raise, log or ignore any error depending
                # on the quitonerror setting
                if quitonerror == ERR_RAISE:
                    raise err
                if quitonerror == ERR_LOG:
                    # pass to error handler if there is one
                    if errorhandler is None:
                        print(err)
                    else:
                        errorhandler(err)
                # continue

    @property
    def datastream(self) -> object:
        """
        Getter for stream.

        :return: data stream
        :rtype: object
        """

        return self._stream
