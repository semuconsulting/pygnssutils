"""
socketwrapper.py

Socket stream wrapper providing read(n) and readline() methods.

Supports chunked and compressed transfer-encoded datastreams.

Created on 12 Feb 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

import socket
from io import BytesIO
from logging import getLogger
from zlib import MAX_WBITS, decompress
from zlib import error as zlibError

from pygnssutils.globals import (
    DEFAULT_BUFSIZE,
    ENCODE_CHUNKED,
    ENCODE_COMPRESS,
    ENCODE_DEFLATE,
    ENCODE_GZIP,
    ENCODE_NONE,
)


class SocketWrapper:
    """
    Socket stream wrapper providing read(n) and readline() methods.

    Supports chunked transfer-encoded datastreams.
    """

    def __init__(self, sock: socket, encoding=ENCODE_NONE, bufsize=DEFAULT_BUFSIZE):
        """
        Constructor.

        :param sock socket: socket object
        :param int encoding: OR'd transfer-encoding values \
            - 0 = none, 1 = chunk, 2 = gzip, 4 = compress, 8 = deflate
        :param int bufsize: internal buffer size
        """

        # configure logger with name "pygnssutils" in calling module
        self.logger = getLogger(__name__)
        self._socket = sock
        self._bufsize = bufsize
        self._encoding = encoding
        self._buffer = bytearray()
        self._partial = b""  # partial chunk
        self._recv()  # populate initial buffer

    def _recv(self) -> bool:
        """
        Read bytes from socket into internal buffer.

        :return: return code (0 = failure, 1 = success)
        :rtype: bool
        """

        try:
            data = self._socket.recv(self._bufsize)
            if len(data) == 0:
                return False
            if self._encoding & ENCODE_CHUNKED:
                data = self._partial + data
                chunks, self._partial = self.dechunk(data)
                self._buffer += chunks
            else:
                self._buffer += data
        except (OSError, TimeoutError):
            return False
        return True

    def read(self, num: int) -> bytes:
        """
        Read specified number of bytes from buffer.
        NB: always check length of return data.

        :param int num: number of bytes to read
        :return: bytes read (which may be less than num)
        :rtype: bytes
        """

        # if at end of internal buffer, top it up from socket
        while len(self._buffer) < num:
            if not self._recv():
                return b""
        data = self._buffer[:num]
        self._buffer = self._buffer[num:]
        return bytes(data)

    def readline(self) -> bytes:
        """
        Read bytes from buffer until CRLF reached.
        NB: always check that return data terminator is CRLF.

        :return: bytes
        :rtype: bytes
        """

        line = b""
        while True:
            data = self.read(1)
            if len(data) == 1:
                line += data
                if line[-2:] == b"\r\n":
                    break
            else:
                break

        return line

    def write(self, data: bytes, **kwargs):
        """
        Write bytes to socket.

        :param bytes data: data
        :param dict kwargs: kwargs
        """

        return self._socket.send(data, **kwargs)

    def in_waiting(self) -> int:
        """
        Return number of bytes in buffer.

        :return: length of buffer
        :rtype: int
        """

        return len(self._buffer)

    def dechunk(self, segment: bytes) -> tuple:
        """
        Parse segment of chunked transfer-encoded byte stream.

        Returns complete chunks in this segment and any partial
        chunk, which should be prepended to next segment read.

        :param segment: segment of byte stream
        :return: tuple of (chunks, partial)
        :rtype: tuple
        """

        instream = BytesIO(segment)
        chunks = b""
        partial = b""

        while True:
            length_bytes = instream.readline()
            if length_bytes[-2:] != b"\r\n":
                # premature end of length bytes
                partial = length_bytes
                break
            try:
                chunk_length = int(length_bytes.strip(), 16)
            except ValueError:
                # residual bytes at beginning of stream
                break
            if chunk_length != 0:
                chunk = instream.read(chunk_length)
                if len(chunk) != chunk_length:
                    # premature end of chunk bytes
                    partial = length_bytes + chunk
                    break
                try:
                    if self._encoding & ENCODE_GZIP:
                        chunk = decompress(chunk, wbits=MAX_WBITS | 16)
                    if self._encoding & ENCODE_COMPRESS:
                        chunk = decompress(chunk, wbits=MAX_WBITS)
                    if self._encoding & ENCODE_DEFLATE:
                        chunk = decompress(chunk, wbits=-MAX_WBITS)
                except zlibError as err:  # pragma: no cover
                    self.logger.error(f"Error decompressing data: {err}")
                    # parser will discard data
                chunks += chunk

            instream.readline()
            if chunk_length == 0:
                # final chunk
                break

        return chunks, partial
