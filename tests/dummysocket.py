"""
dummsocket.py

Dummy socket class for testing SocketWrapper methods.

Created on 21 Aug 2024

:author: semuadmin
:copyright: SEMU Consulting © 2020
:license: BSD 3-Clause
"""


class DummySocket:
    """
    Dummy socket class for testing SocketWrapper.
    """

    def __init__(
        self,
        filename: str,
        bufsize: int = 4096,
        timeout: bool = False,
    ):
        """
        Constructor.

        Reads binary data from a file into a working buffer,
        representing the socket stream.

        :param str filename: filename
        :param int bufsize: size of buffer
        :param bool timeout: simulate TimeoutError?
        """

        self._buffer = b""
        self._timeout = timeout
        with open(filename, "rb") as infile:
            while len(self._buffer) < bufsize:
                b = infile.read(16)
                if b == b"":
                    break
                self._buffer += b

    def recv(self, n: int) -> bytes:
        """
        Receive n bytes from dummy socket.

        :param int n: number of bytes to read
        :return: bytes read
        :rtype: bytes
        """

        if self._timeout:
            raise TimeoutError("simulated TimeoutError")
        b = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return b

    def send(self, data: bytes) -> int:
        """
        Send data to socket.

        :param bytes data: data to send
        :return: number of bytes sent
        :rtype: int
        """

        print(f"data sent: {data}")
        return len(data)

    def sendall(self, data):
        """
        Sendall data to socket.
        """

        print(f"data sent: {data}")

    def close(self):
        """
        Close socket
        """

        print("socket closed")
