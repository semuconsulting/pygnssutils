"""
dummsocket.py

Dummy socket class for testing SocketWrapper methods.

Created on 21 Aug 2024

:author: semuadmin
:copyright: SEMU Consulting © 2020
:license: BSD 3-Clause
"""

DEFAULT_BUFSIZE = 4096


class DummySocket:
    """
    Dummy socket class for testing SocketWrapper.
    """

    def __init__(self, filename: str, bufsize: int = DEFAULT_BUFSIZE):
        """
        Constructor.
        """

        self._buffer = b""
        with open(filename, "rb") as infile:
            while len(self._buffer) < bufsize:
                b = infile.read(16)
                if b == b"":
                    break
                self._buffer += b

    def recv(self, n: int) -> bytes:
        """
        Read n bytes from dummy socket.
        """

        b = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return b

    def send(self, data) -> int:
        """
        Send data to socket
        """

        print(f"data sent: {data}")
        return len(data)

    def sendall(self, data):
        """
        Send data to socket
        """

        print(f"data sent: {data}")
        return None

    def close():
        """
        Close socket
        """

        print("socket closed")
