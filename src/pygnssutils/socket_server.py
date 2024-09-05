"""
TCP socket server for PyGPSClient application.

(could also be used independently of a tkinter app framework)

Reads raw data from GNSS receiver message queue and
outputs this to multiple TCP socket clients.

Operates in two modes according to ntripmode setting:

0 - open socket mode - will stream GNSS data to any connected client
    without authentication.
1 - NTRIP caster mode - implements NTRIP server protocol and will
    respond to NTRIP client authentication, sourcetable and RTCM3 data
    stream requests.
    NB: THIS ASSUMES THE CONNECTED GNSS RECEIVER IS OPERATING IN BASE
    STATION (SURVEY-IN OR FIXED) MODE AND OUTPUTTING THE RELEVANT RTCM3 MESSAGES.

For NTRIP caster mode, authorization credentials can be supplied via keyword
arguments or set as environment variables:
export PYGPSCLIENT_USER="user"
export PYGPSCLIENT_PASSWORD="password"

NB: This utility is used by PyGPSClient - do not change footprint of
any public methods without first checking impact on PyGPSClient -
https://github.com/semuconsulting/PyGPSClient.

Created on 16 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

from base64 import b64encode
from datetime import datetime, timezone
from logging import getLogger
from os import getenv
from queue import Queue
from socketserver import StreamRequestHandler, ThreadingTCPServer
from threading import Event, Thread

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import CLIAPP, CONNECTED, DISCONNECTED, MAXCONNECTION
from pygnssutils.helpers import ipprot2int

# from pygpsclient import version as PYGPSVERSION

RTCM = b"rtcm"
SRT = b"srt"
BAD = b"bad"
BUFSIZE = 1024
PYGPSMP = "pygnssutils"


class SocketServer(ThreadingTCPServer):
    """
    Socket server class.

    This instantiates a daemon ClientHandler thread for each
    connected client.
    """

    def __init__(
        self, app, ntripmode: int, maxclients: int, msgqueue: Queue, *args, **kwargs
    ):
        """
        Overridden constructor.

        :param Frame app: reference to main application class (if any)
        :param int ntripmode: 0 = open socket server, 1 = NTRIP server
        :param int maxclients: max no of clients allowed
        :param Queue msgqueue: queue containing raw GNSS messages
        :param str ipprot: (kwarg) IP protocol family (IPv4, IPv6)
        :param str ntripversion: (kwarg) NTRIP version ("1.0", "2.0")
        :param str ntripuser: (kwarg) NTRIP authentication user name
        :param str ntrippassword: (kwarg) NTRIP authentication password
        :param int verbosity: (kwarg) log verbosity (1 = medium)
        :param str logtofile: (kwarg) fully qualifed log file name ('')
        """

        self.__app = app  # Reference to main application class
        self.logger = getLogger(__name__)
        self._ntripmode = ntripmode
        self._maxclients = maxclients
        self._msgqueue = msgqueue
        self._connections = 0
        self._stream_thread = None
        self._stopmqread = Event()
        # set NTRIP Caster authentication credentials
        self.ntripversion = kwargs.pop("ntripversion", "2.0")
        self._ntripuser = kwargs.pop("ntripuser", getenv("PYGPSCLIENT_USER", "anon"))
        self._ntrippassword = kwargs.pop(
            "ntrippassword", getenv("PYGPSCLIENT_PASSWORD", "password")
        )
        self.address_family = ipprot2int(kwargs.pop("ipprot", "IPv4"))
        # set up pool of client queues
        self.clientqueues = []
        for _ in range(self._maxclients):
            self.clientqueues.append({"client": None, "queue": Queue()})
        self._start_read_thread()
        self.daemon_threads = True  # stops deadlock on abrupt termination
        super().__init__(*args, **kwargs)
        self.allow_reuse_address = True

    def server_close(self):
        """
        Overridden server close routine.
        """

        self.stop_read_thread()
        super().server_close()

    def handle_error(self, request, client_address):
        """
        Handle client exception.

        :param request: request object
        :param address: client address
        """

        self.logger.error(f"Client error {client_address} {request}")

    def verify_request(self, request, client_address) -> bool:
        """
        Verify client request.

        :param request: request object
        :param address: client address
        :return: verified y/n
        :rtype: bool
        """

        verify = self._connections < self._maxclients
        if not verify:
            self.logger.info(
                f"Request {client_address} rejected - maximum clients reached "
                f"{self._connections}/{self._maxclients}."
            )
            if hasattr(self.__app, "notify_client"):
                self.__app.notify_client(client_address, MAXCONNECTION)
        return verify

    def _start_read_thread(self):
        """
        Start GNSS message reader thread.
        """

        while not self._msgqueue.empty():  # flush queue
            self._msgqueue.get()

        self._stopmqread.clear()
        self._stream_thread = Thread(
            target=self._read_thread,
            args=(self._stopmqread, self._msgqueue, self.clientqueues),
            daemon=True,
        )
        self._stream_thread.start()

    def stop_read_thread(self):
        """
        Stop GNSS message reader thread.
        """

        self._stopmqread.set()

    def _read_thread(self, stopmqread: Event, msgqueue: Queue, clientqueues: dict):
        """
        THREADED
        Read from main GNSS message queue and place
        raw data on an output queue for each connected client.

        :param Event stopmqread: stop event for mq read thread
        :param Queue msgqueue: input message queue
        :param Dict clientqueues: pool of output queues for use by clients
        """

        while not stopmqread.is_set():
            raw = msgqueue.get()
            for i in range(self._maxclients):
                # if client connected to this queue
                if clientqueues[i]["client"] is not None:
                    clientqueues[i]["queue"].put(raw)

    def notify(self, address: tuple, status: int):
        """
        Alert calling app on client connection or disconnection.

        :param tuple address: client address
        :param int status: 0 = disconnected, 1 = connected, 2 = maxconnections
        """

        msg = ""
        if status == DISCONNECTED:
            msg = f"Client {address} disconnected."
            self.connections -= 1
        elif status == CONNECTED:
            msg = f"Client {address} connected."
            self.connections += 1
        self.logger.info(f"{msg} Total clients {self._connections}/{self._maxclients}.")
        if hasattr(self.__app, "notify_client"):
            self.__app.notify_client(address, status)

    @property
    def credentials(self) -> bytes:
        """
        Getter for basic authorization credentials.
        """

        user = self._ntripuser + ":" + self._ntrippassword
        return b64encode(user.encode(encoding="utf-8"))

    @property
    def connections(self):
        """
        Getter for client connections.
        """

        return self._connections

    @connections.setter
    def connections(self, clients: int):
        """
        Setter for client connections.
        Also updates no. of clients on settings panel.

        :param int clients: no of client connections
        """

        self._connections = clients
        if hasattr(self.__app, "update_clients"):
            self.__app.update_clients(self._connections)

    @property
    def ntripmode(self) -> int:
        """
        Getter for ntrip mode.

        :return: 0 = open socket server, 1 = ntrip mode
        :rtype: int
        """

        return self._ntripmode

    @property
    def latlon(self) -> tuple:
        """
        Get current lat / lon from receiver.

        :return=: tuple of (lat, lon)
        :rtype: tuple
        """

        if hasattr(self.__app, "gnss_status"):
            return (self.__app.gnss_status.lat, self.__app.gnss_status.lon)
        return ("", "")


class ClientHandler(StreamRequestHandler):
    """
    Threaded TCP client connection handler class.
    """

    def __init__(self, *args, **kwargs):
        """
        Overridden constructor.
        """

        self._qidx = None
        self._msgqueue = None
        self._allowed = False

        super().__init__(*args, **kwargs)

    def setup(self, *args, **kwargs):
        """
        Overridden client handler setup routine.
        Allocates available message queue to client.
        """

        # find next unused client queue in pool...
        for i, clq in enumerate(self.server.clientqueues):
            if clq["client"] is None:
                self._allowed = True
                self.server.clientqueues[i]["client"] = self.client_address
                self._msgqueue = clq["queue"]
                while not self._msgqueue.empty():  # flush queue
                    self._msgqueue.get()
                self._qidx = i
                self.server.notify(self.client_address, CONNECTED)
                break
        if self._qidx is None:  # no available client queues in pool
            return

        super().setup(*args, **kwargs)

    def finish(self, *args, **kwargs):
        """
        Overridden client handler finish routine.
        De-allocates message queue from client.
        """

        if self._qidx is not None:
            self.server.clientqueues[self._qidx]["client"] = None

        if self._allowed:
            self.server.notify(self.client_address, DISCONNECTED)
            super().finish(*args, **kwargs)

    def handle(self):
        """
        Overridden main client handler.

        If in NTRIP server mode, will respond to NTRIP client authentication
        and sourcetable requests and, if valid, stream relevant RTCM3 data
        from the input message queue to the socket.

        If in open socket server mode, will simply stream content of
        input message queue to the socket.
        """

        while self._allowed:  # if connection allowed, loop until terminated
            try:
                if self.server.ntripmode:  # NTRIP server mode
                    self.data = self.request.recv(BUFSIZE)
                    resptype, resp = self._process_ntrip_request(self.data)
                    if resptype is not None:
                        self.wfile.write(resp)  # send HTTP response
                        self.wfile.flush()
                    if resptype == RTCM:  # RTCM3 data request
                        while True:  # send continuous RTCM data stream
                            self._write_from_mq()
                    else:
                        break

                else:  # open socket server mode
                    self._write_from_mq()

            except (
                ConnectionRefusedError,
                ConnectionAbortedError,
                ConnectionResetError,
                BrokenPipeError,
                TimeoutError,
            ):
                break

    def _process_ntrip_request(self, data: bytes) -> bytes:
        """
        Process NTRIP client request.

        :param bytes data: client request
        :return: client response
        :rtype: bytes or None if request rejected
        """

        strreq = False
        authorized = False
        validmp = False
        mountpoint = ""

        request = data.strip().split(b"\r\n")
        for part in request:
            if part[0:21] == b"Authorization: Basic ":
                authorized = part[21:] == self.server.credentials
            if part[0:3] == b"GET":
                get = part.split(b" ")
                mountpoint = get[1].decode("utf-8")
                if mountpoint == "":  # no mountpoint, hence sourcetable request
                    strreq = True
                elif mountpoint == f"/{PYGPSMP}":  # valid mountpoint
                    validmp = True

        http_date, server_date = self._format_dates()
        if not authorized:  # respond with 401
            if self.server.ntripversion == "1.0":
                http = (
                    "HTTP/1.1 401 Unauthorized\r\n"
                    f"Date: {http_date}\r\n"
                    f'WWW-Authenticate: Basic realm="{mountpoint}"\r\n'
                    "Content-Type: text/html\r\n"
                    "Connection: close\r\n\r\n"
                    "<!DOCTYPE html>\r\n"
                    "<html><head><title>401 Unauthorized</title></head><body "
                    "style='background-color:white; color:black;'>\r\n"
                    "<h1 style='text-align:center;'>"
                    "The server does not recognize your privileges "
                    "to the requested entity/stream</h1>\r\n"
                    "</body></html>\r\n\r\n"
                )
            else:
                http = (
                    "HTTP/1.1 401 Unauthorized\r\n"
                    "Ntrip-Version: Ntrip/2.0\r\n"
                    f"Server: {PYGPSMP.upper()}_NTRIP_Caster_{VERSION}/of:{server_date}\r\n"
                    f"Date: {http_date}\r\n"
                    f'WWW-Authenticate: Basic realm="{mountpoint}"\r\n'
                    "Connection: close\r\n\r\n"
                )
            return BAD, bytes(http, "UTF-8")
        if strreq or (not strreq and not validmp):  # respond with nominal sourcetable
            http = self._format_sourcetable()
            return SRT, bytes(http, "UTF-8")
        if validmp:  # respond by opening RTCM3 stream
            http = self._format_data()
            return RTCM, bytes(http, "UTF-8")
        return None, None

    def _format_sourcetable(self) -> str:
        """
        Format nominal HTTP sourcetable response.

        :return: HTTP response string
        :rtype: str
        """

        http_date, server_date = self._format_dates()
        lat, lon = self.server.latlon
        ipaddr, port = self.server.server_address
        pygu = PYGPSMP.upper()
        # sourcetable based on ZED-F9P capabilities
        sourcetable = (
            f"CAS;{ipaddr};{port};{PYGPSMP}/{VERSION};SEMU;0;GBR;{lat};{lon};0.0.0.0;0;none\r\n"
            f"NET;{pygu};SEMU;B;N;none;none;none;none\r\n"
            f"STR;{PYGPSMP};{pygu};RTCM 3.3;"
            "1005(5),1077(1),1087(1),1097(1),1127(1),1230(1);"
            f"2;GPS+GLO+GAL+BEI;{pygu};GBR;{lat};{lon};0;0;{pygu};none;B;N;0;\r\n"
            "ENDSOURCETABLE\r\n"
        )
        if self.server.ntripversion == "1.0":
            http = (
                "SOURCETABLE 200 OK\r\n"
                f"Date: {http_date}\r\n"
                "Connection: close\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(sourcetable)}\r\n"
                "\r\n"  # necessary to separate body from header
                f"{sourcetable}"
            )
        else:
            http = (
                "HTTP/1.1 200 OK\r\n"
                "Ntrip-Version: Ntrip/2.0\r\n"
                # "Ntrip-Flags: st_filter,st_auth,st_match,st_strict,rtsp,plain_rtp\r\n"
                f"Server: {pygu}_NTRIP_Caster_{VERSION}/of:{server_date}\r\n"
                f"Date: {http_date}\r\n"
                "Connection: close\r\n"
                "Content-Type: gnss/sourcetable\r\n"
                f"Content-Length: {len(sourcetable)}\r\n"
                "\r\n"  # necessary to separate body from header
                f"{sourcetable}"
            )
        return http

    def _format_data(self) -> str:
        """
        Format nominal HTTP data response.

        :return: HTTP response string
        :rtype: str
        """

        http_date, server_date = self._format_dates()
        if self.server.ntripversion == "1.0":
            http = "ICY 200 OK\r\n\r\n"
        else:
            http = (
                "HTTP/1.1 200 OK"
                "Ntrip-Version: Ntrip/2.0\r\n"
                f"Server: {PYGPSMP.upper()}_NTRIP_Caster_{VERSION}/of:{server_date}\r\n"
                f"Date: {http_date}\r\n"
                "Cache-Control: no-store, no-cache, max-age=0\r\n"
                "Pragma: no-cache\r\n"
                "Connection: close\r\n"
                "Content-Type: gnss/data\r\n"
                "\r\n"  # necessary to separate body from header
            )
        return http

    def _format_dates(self) -> tuple:
        """
        Format response header dates.

        :return: tuple of (http_date, server_date)
        :rtype: tuple
        """

        dat = datetime.now(timezone.utc)
        http_date = dat.strftime("%a, %d %b %Y %H:%M:%S %Z")
        server_date = dat.strftime("%d %b %Y")
        return (http_date, server_date)

    def _write_from_mq(self):
        """
        Get data from message queue and write to socket.
        """

        raw = self._msgqueue.get()
        if raw is not None:
            self.wfile.write(raw)
            self.wfile.flush()


def runserver(
    host: str,
    port: int,
    mq: Queue,
    ntripmode: int = 0,
    maxclients: int = 5,
    **kwargs,
):
    """
    THREADED
    Socket server function to be run as thread.

    :param str host: host IP
    :param int port: port
    :param Queue mq: output message queue
    :param int ntripmode: 0 = basic, 1 = ntrip caster
    :param int maxclients: max concurrent clients
    :param str ntripversion: (kwarg) NTRIP version 1.0 or 2.0
    """

    with SocketServer(
        CLIAPP,
        ntripmode,
        maxclients,
        mq,  # message queue containing raw data from source
        (host, port),
        ClientHandler,
        ntripversion=kwargs.get("ntripversion", "2.0"),
        ntripuser=kwargs.get("ntripuser", "anon"),
        ntrippassword=kwargs.get("ntrippassword", "password"),
    ) as server:
        server.serve_forever()
