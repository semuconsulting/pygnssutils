"""
socket_stream class.

A skeleton socket wrapper which provides basic stream-like
read(num), readuntil(separator) and readline() methods.

NB: this will read from a socket indefinitely. It is the
responsibility of the calling application to monitor
data returned and implement appropriate socket error,
timeout or inactivity procedures.

Created on 4 Apr 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

from socket import socket

LF = b"\x0a"
CRLF = b"\x0d\x0a"


class SocketStream:
    """
    socket stream class.
    """

    def __init__(self, sock: socket, **kwargs):
        """
        Constructor.

        :param sock socket: socket object
        :param int bufsize: (kwarg) internal buffer size (4096)
        :param int itersize: (kwarg) num of bytes to read in iterator (0 = readuntil)
        :param int iterseparator: (kwarg) separator to use in iterator ("\\\\n", 0x0a)
        """

        self._socket = sock
        self._bufsize = kwargs.get("bufsize", 4096)
        self._itersize = kwargs.get("itersize", 0)
        self._iterseparator = kwargs.get("iterseparator", LF)
        self._buffer = bytearray()
        self._recv()  # populate initial buffer

    def _recv(self) -> bool:
        """
        Read bytes from socket into internal buffer.

        :return: return code (0 = failure, 1 = success)
        :rtype: bool
        """

        try:
            data = self._socket.recv(self._bufsize)
            self._buffer += data
        except (OSError, TimeoutError):
            return False
        return True

    @property
    def buffer(self) -> bytearray:
        """
        Getter for buffer.

        :return: buffer
        :rtype: bytearray
        """

        return self._buffer

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

    def readuntil(self, separator: bytes) -> bytes:
        """
        Read bytes from buffer until separator reached.
        NB: always check that return data terminator is as specifed.

        :param bytes separator: separator
        :return: bytes
        :rtype: bytes
        """

        line = b""
        lns = len(separator)
        while True:
            data = self.read(1)
            if len(data) == 1:
                line += data
                if line[-lns:] == separator:
                    break
            else:
                break

        return line

    def readline(self) -> bytes:
        """
        Read bytes from buffer until LF reached.
        NB: always check that return data terminator is LF.

        :return: bytes
        :rtype: bytes
        """

        return self.readuntil(LF)

    def __iter__(self):
        """Iterator."""

        return self

    def __next__(self) -> bytes:
        """
        Return next item in iteration.

        If kwarg itersize > 0, will return fixed number of bytes.
        If kwarg itersize = 0, will use readline(iterseparator).

        :return: data
        :rtype: bytes
        :raises: StopIteration

        """

        if self._itersize == 0:
            lns = len(self._iterseparator)
            data = self.readline()
            if data[-lns:] == self._iterseparator:
                return data
        else:
            data = self.read(self._itersize)
            if len(data) == self._itersize:
                return data
        raise StopIteration
