"""
gnssntripclient.py

NTRIP client class, retrieving sourcetable and RTCM3 or SPARTN
correction data from an NTRIP server and (optionally) sending
the correction data to a designated writeable output medium
(serial, file, socket, queue).

Can also transmit client position back to NTRIP server at specified
intervals via formatted NMEA GGA sentences.

Calling app, if defined, can implement the following methods:
- set_event() - create <<ntrip_read>> event
- dialog() - return reference to NTRIP config client dialog
- get_coordinates() - return coordinates from receiver

Created on 03 Jun 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

# pylint: disable=invalid-name

import socket
import ssl
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from io import BufferedWriter, TextIOWrapper
from logging import getLogger
from os import getenv
from queue import Queue
from threading import Event, Thread
from time import sleep

from certifi import where as findcacerts
from pynmeagps import GET, NMEAMessage
from pyrtcm import RTCMMessageError, RTCMParseError, RTCMTypeError
from pyspartn import SPARTNMessageError, SPARTNParseError, SPARTNReader, SPARTNTypeError
from pyubx2 import ERR_IGNORE, RTCM3_PROTOCOL, UBXReader
from serial import Serial

from pygnssutils import __version__ as VERSION
from pygnssutils.exceptions import ParameterError
from pygnssutils.globals import (
    CLIAPP,
    DEFAULT_BUFSIZE,
    HTTPERR,
    MAXPORT,
    NOGGA,
    NTRIP_EVENT,
    OUTPORT_NTRIP,
)
from pygnssutils.helpers import find_mp_distance, format_conn, ipprot2int

TIMEOUT = 10
GGALIVE = 0
GGAFIXED = 1
DLGTNTRIP = "NTRIP Configuration"
RTCM = "RTCM"
SPARTN = "SPARTN"
MAX_RETRY = 5
RETRY_INTERVAL = 10
INACTIVITY_TIMEOUT = 10
WAITTIME = 3


class GNSSNTRIPClient:
    """
    NTRIP client class.
    """

    def __init__(self, app=None, **kwargs):
        """
        Constructor.

        :param object app: application from which this class is invoked (None)
        :param int retries: (kwarg) maximum failed connection retries (5)
        :param int retryinterval: (kwarg) retry interval in seconds (10)
        :param int timeout: (kwarg) inactivity timeout in seconds (10)
        """

        # pylint: disable=consider-using-with

        self.__app = app  # Reference to calling application class (if applicable)
        # configure logger with name "pygnssutils" in calling module
        self.logger = getLogger(__name__)
        self._validargs = True
        self._ntripqueue = Queue()
        # persist settings to allow any calling app to retrieve them
        self._settings = {
            "ipprot": socket.AF_INET,
            "server": "",
            "port": 2101,
            "https": 0,
            "flowinfo": 0,
            "scopeid": 0,
            "mountpoint": "",
            "distance": "",
            "version": "2.0",
            "datatype": RTCM,
            "ntripuser": "anon",
            "ntrippassword": "password",
            "ggainterval": "None",
            "ggamode": GGALIVE,
            "sourcetable": [],
            "reflat": 0.0,
            "reflon": 0.0,
            "refalt": 0.0,
            "refsep": 0.0,
            "spartndecode": 0,
            "spartnkey": getenv("MQTTKEY", default=None),
            "spartnbasedate": datetime.now(timezone.utc),
        }

        try:
            self._retries = int(kwargs.pop("retries", MAX_RETRY))
            self._retryinterval = int(kwargs.pop("retryinterval", RETRY_INTERVAL))
            self._timeout = int(kwargs.pop("timeout", INACTIVITY_TIMEOUT))
        except (ParameterError, ValueError, TypeError) as err:
            self.logger.critical(
                f"Invalid input arguments {kwargs=}\n{err=}\nType gnssntripclient -h for help.",
            )
            self._validargs = False

        self._socket = None
        self._connected = False
        self._stopevent = Event()
        self._ntrip_thread = None
        self._last_gga = datetime.fromordinal(1)
        self._retrycount = 0

    def __enter__(self):
        """
        Context manager enter routine.
        """

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Context manager exit routine.

        Terminates threads in an orderly fashion.
        """

        self.stop()

    @property
    def settings(self):
        """
        Getter for NTRIP settings.
        """

        return self._settings

    @settings.setter
    def settings(self, settings: dict):
        """
        Setter for NTRIP settings.

        :param dict settings: NTRIP settings dictionary
        """

        self._settings = settings

    @property
    def connected(self):
        """
        Connection status getter.
        """

        return self._connected

    def run(self, **kwargs) -> bool:
        """
        Open NTRIP server connection.

        If calling application implements a "get_coordinates" method to
        obtain live coordinates (i.e. from GNSS receiver), the method will
        use these instead of fixed reference coordinates.

        User login credentials can be obtained from environment variables
        PYGPSCLIENT_USER and PYGPSCLIENT_PASSWORD, or passed as kwargs.

        :param str ipprot: (kwarg) IP protocol IPv4/IPv6 ("IPv4")
        :param str server: (kwarg) NTRIP server URL ("")
        :param int port: (kwarg) NTRIP port (2101)
        :param int https: (kwarg) HTTPS (TLS) connection? 0 = HTTP 1 = HTTPS (0)
        :param int flowinfo: (kwarg) flowinfo for IPv6 (0)
        :param int scopeid: (kwarg) scopeid for IPv6 (0)
        :param str mountpoint: (kwarg) NTRIP mountpoint ("", leave blank to get sourcetable)
        :param str datatype: (kwarg) Data type - RTCM or SPARTN ("RTCM")
        :param str version: (kwarg) NTRIP protocol version ("2.0")
        :param str ntripuser: (kwarg) NTRIP authentication user ("anon")
        :param str ntrippassword: (kwarg) NTRIP authentication password ("password")
        :param int ggainterval: (kwarg) GGA sentence transmission interval (-1 = None)
        :param int ggamode: (kwarg) GGA pos source; 0 = live from receiver, 1 = fixed reference (0)
        :param str reflat: (kwarg) reference latitude (0.0)
        :param str reflon: (kwarg) reference longitude (0.0)
        :param str refalt: (kwarg) reference altitude (0.0)
        :param str refsep: (kwarg) reference separation (0.0)
        :param bool spartndecode: (kwarg) decode SPARTN messages (0)
        :param str spartnkey: (kwarg) SPARTN decryption key (None)
        :param object datetime: (kwarg) SPARTN decryption basedate (now(utc))
        :param object output: (kwarg) writeable output medium (serial, file, socket, queue) (None)
        :returns: boolean flag 0 = terminated, 1 = Ok to stream RTCM3 data from server
        :rtype: bool
        """
        # pylint: disable=unused-variable

        try:
            self._last_gga = datetime.fromordinal(1)

            ipprot = kwargs.get("ipprot", "IPv4")
            self._settings["ipprot"] = ipprot2int(ipprot)
            self._settings["server"] = server = kwargs.get("server", "")
            self._settings["port"] = port = int(kwargs.get("port", OUTPORT_NTRIP))
            self._settings["https"] = int(kwargs.get("https", 0))
            self._settings["flowinfo"] = int(kwargs.get("flowinfo", 0))
            self._settings["scopeid"] = int(kwargs.get("scopeid", 0))
            self._settings["mountpoint"] = mountpoint = kwargs.get("mountpoint", "")
            self._settings["datatype"] = kwargs.get("datatype", RTCM).upper()
            self._settings["version"] = kwargs.get("version", "2.0")
            self._settings["ntripuser"] = kwargs.get(
                "ntripuser", getenv("PYGPSCLIENT_USER", "user")
            )
            self._settings["ntrippassword"] = kwargs.get(
                "ntrippassword", getenv("PYGPSCLIENT_PASSWORD", "password")
            )
            self._settings["ggainterval"] = int(kwargs.get("ggainterval", NOGGA))
            self._settings["ggamode"] = int(kwargs.get("ggamode", GGALIVE))
            self._settings["reflat"] = kwargs.get("reflat", 0.0)
            self._settings["reflon"] = kwargs.get("reflon", 0.0)
            self._settings["refalt"] = kwargs.get("refalt", 0.0)
            self._settings["refsep"] = kwargs.get("refsep", 0.0)
            self._settings["spartndecode"] = kwargs.get("spartndecode", 0)
            self._settings["spartnkey"] = kwargs.get(
                "spartnkey", getenv("MQTTKEY", None)
            )
            self._settings["spartnbasedate"] = kwargs.get(
                "spartbasedate", datetime.now(timezone.utc)
            )
            output = kwargs.get("output", None)

            if server == "":
                raise ParameterError(f"Invalid server url {server}")
            if port > MAXPORT or port < 1:
                raise ParameterError(f"Invalid port {port}")

        except (ParameterError, ValueError, TypeError) as err:
            self.logger.critical(
                f"Invalid input arguments {kwargs}\n{err}\nType gnssntripclient -h for help."
            )
            self._validargs = False

        if self._validargs:
            self._connected = True
            self._start_read_thread(
                self._settings,
                self._stopevent,
                output,
            )
            if mountpoint != "":
                return 1
        return 0

    def stop(self):
        """
        Close NTRIP server connection.
        """

        self._stop_read_thread()
        self._connected = False

    def _app_update_status(self, status: bool, msgt: tuple = None):
        """
        THREADED
        Update NTRIP connection status in calling application.

        :param bool status: NTRIP server connection status
        :param tuple msgt: optional (message, color)
        """

        if self.__app is not None:
            if hasattr(self.__app, "dialog"):
                dlg = self.__app.dialog(DLGTNTRIP)
                if dlg is not None:
                    if hasattr(dlg, "set_controls"):
                        dlg.set_controls(status, msgt)

    def _app_get_coordinates(self) -> tuple:
        """
        THREADED
        Get live coordinates from receiver, or use fixed
        reference position, depending on ggamode setting.

        NB" 'fix' is a string e.g. "3D" or "RTK FLOAT"

        :returns: tuple of coordinate and fix data
        :rtype: tuple
        """

        lat = lon = alt = sep = 0.0
        fix, sip, hdop, diffage, diffstation = (1, 15, 0.98, 0, 0)  # arbitrary values
        if self._settings["ggamode"] == GGAFIXED:  # fixed reference position
            lat = self._settings["reflat"]
            lon = self._settings["reflon"]
            alt = self._settings["refalt"]
            sep = self._settings["refsep"]
        elif self.__app is not None:
            if hasattr(self.__app, "get_coordinates"):  # live position from receiver
                coords = self.__app.get_coordinates()
                if len(coords) == 10:  # new version (PyGPSClient >=1.4.20)
                    _, lat, lon, alt, sep, sip, fix, hdop, diffage, diffstation = coords
                else:  # old version (PyGPSClient <=1.4.19)
                    _, lat, lon, alt, sep = coords

        lat, lon, alt, sep = [
            0.0 if c == "" else float(c) for c in (lat, lon, alt, sep)
        ]

        return lat, lon, alt, sep, fix, sip, hdop, diffage, diffstation

    def _formatGET(self, settings: dict) -> str:
        """
        THREADED
        Format HTTP GET Request.

        :param dict settings: settings dictionary
        :return: formatted HTTP GET request
        :rtype: str
        """

        ggahdr = ""
        if settings["version"] == "2.0":
            hver = "1.1"
            nver = "Ntrip-Version: Ntrip/2.0\r\n"
            if settings["ggainterval"] != NOGGA:
                gga, _ = self._formatGGA()
                ggahdr = f"Ntrip-GGA: {gga.decode('utf-8')}"  # includes \r\n
        else:
            hver = "1.0"
            nver = ""

        mountpoint = "/" + settings["mountpoint"]
        user = settings["ntripuser"] + ":" + settings["ntrippassword"]
        user = b64encode(user.encode(encoding="utf-8"))
        req = (
            f"GET {mountpoint} HTTP/{hver}\r\n"
            f"Host: {settings['server']}:{settings['port']}\r\n"
            f"{nver}"
            f"User-Agent: NTRIP pygnssutils/{VERSION}\r\n"
            "Accept: */*\r\n"
            f"Authorization: Basic {user.decode(encoding='utf-8')}\r\n"
            f"{ggahdr}"
            "Connection: close\r\n\r\n"  # NECESSARY!!!
        )
        self.logger.debug(f"HTTP Header\n{req}")
        return req.encode(encoding="utf-8")

    def _formatGGA(self) -> tuple:
        """
        THREADED
        Format NMEA GGA sentence using pynmeagps. The raw string
        output is suitable for sending to an NTRIP socket.

        GGA timestamp will default to current UTC. GGA quality is
        derived from fix string.

        :return: tuple of (raw NMEA message as bytes, NMEAMessage)
        :rtype: tuple
        """

        try:
            lat, lon, alt, sep, fixs, sip, hdop, diffage, diffstation = (
                self._app_get_coordinates()
            )
            lat = float(lat)
            lon = float(lon)

            fixi = {
                "TIME ONLY": 0,
                "2D": 1,
                "3D": 1,
                "GNSS+DR": 1,
                "RTK": 5,
                "RTK FLOAT": 5,
                "RTK FIXED": 4,
                "DR": 6,
            }.get(fixs, 1)

            parsed_data = NMEAMessage(
                "GP",
                "GGA",
                GET,
                lat=lat,
                lon=lon,
                quality=fixi,
                numSV=sip,
                HDOP=hdop,
                alt=alt,
                altUnit="M",
                sep=sep,
                sepUnit="M",
                diffAge=diffage,
                diffStation=diffstation,
            )

            raw_data = parsed_data.serialize()
            return raw_data, parsed_data

        except ValueError:
            return None, None

    def _send_GGA(self, ggainterval: int, output: object):
        """
        THREADED
        Send NMEA GGA sentence to NTRIP server at prescribed interval.

        :param int ggainterval: GGA send interval in seconds (-1 = don't send)
        :param object output: writeable output medium e.g. serial port
        """

        if ggainterval != NOGGA:
            if datetime.now() > self._last_gga + timedelta(seconds=ggainterval):
                raw_data, parsed_data = self._formatGGA()
                if parsed_data is not None:
                    self._socket.sendall(raw_data)
                    self._do_output(output, raw_data, parsed_data)
                self._last_gga = datetime.now()

    def _get_closest_mountpoint(self) -> tuple:
        """
        THREADED
        Find closest mountpoint in sourcetable
        if valid reference lat/lon are available.

        :return: tuple of (mountpoint, distance)
        :rtype: tuple
        """

        try:
            lat, lon, _, _, _, _, _, _, _ = self._app_get_coordinates()
            closest_mp, dist = find_mp_distance(
                float(lat), float(lon), self._settings["sourcetable"]
            )
            if self._settings["mountpoint"] == "":
                self._settings["mountpoint"] = closest_mp
            self.logger.info(
                "Closest mountpoint to reference location"
                f"({lat}, {lon}) = {closest_mp}, {dist} km."
            )

        except ValueError:
            return None, None
        return closest_mp, dist

    def _start_read_thread(
        self,
        settings: dict,
        stopevent: Event,
        output: object,
    ):
        """
        Start the NTRIP reader thread.
        """

        if self._connected:
            self._stopevent.clear()
            self._ntrip_thread = Thread(
                target=self._read_thread,
                args=(
                    settings,
                    stopevent,
                    output,
                ),
                daemon=True,
            )
            self._ntrip_thread.start()

    def _stop_read_thread(self):
        """
        Stop NTRIP reader thread.
        """

        if self._ntrip_thread is not None:
            self._stopevent.set()
            self._ntrip_thread = None

        self.logger.info("Streaming terminated.")

    def _read_thread(
        self,
        settings: dict,
        stopevent: Event,
        output: object,
    ):
        """
        THREADED
        Try connecting to NTRIP caster.

        :param dict settings: settings as dictionary
        :param Event stopevent: stop event
        :param object output: output stream for raw data
        """

        self._retrycount = 0
        server = settings["server"]
        port = int(settings["port"])
        mountpoint = settings["mountpoint"]

        while self._retrycount <= self._retries and not stopevent.is_set():

            try:

                self._do_connection(settings, stopevent, output)

            except ssl.SSLCertVerificationError as err:
                tip = (
                    f" - try using '{server[4:]}' rather than '{server}' for the NTRIP caster URL"
                    if "certificate is not valid for 'www." in err.strerror
                    else (
                        f" - try adding the NTRIP caster URL SSL certificate to {findcacerts()}"
                        if "unable to get local issuer certificate" in err.strerror
                        else ""
                    )
                )
                self.logger.error(f"SSL Certificate Verification Error{tip}\n{err}")
                self._retrycount = self._retries
                stopevent.set()
                self._connected = False
                self._app_update_status(False, (f"Error!: {err.strerror[0:60]}", "red"))

            except (
                BrokenPipeError,
                ConnectionAbortedError,
                ConnectionRefusedError,
                ConnectionResetError,
                OverflowError,
                socket.gaierror,
                ssl.SSLError,
                TimeoutError,
            ) as err:
                errm = str(repr(err))
                erra = f"Connection Error {errm.split('(', 1)[0]}"
                errl = f"Error connecting to {server}:{port}/{mountpoint}: {errm}"
                if self._retrycount == self._retries:
                    stopevent.set()
                    self._connected = False
                    self.logger.critical(errl)
                    break
                self._retrycount += 1
                errr = (
                    f". Retrying in {self._retryinterval * self._retrycount} secs "
                    f"({self._retrycount}/{self._retries}) ..."
                )
                erra += errr
                errl += errr
                self.logger.warning(errl)
                self._app_update_status(False, (erra, "red"))

            sleep(self._retryinterval * self._retrycount)

    def _do_connection(
        self,
        settings: dict,
        stopevent: Event,
        output: object,
    ):
        """
        THREADED
        Opens socket to NTRIP server and reads incoming data.

        :param dict settings: settings as dictionary
        :param Event stopevent: stop event
        :param object output: output stream for raw data
        :raises: Various socket error types if connection fails
        """

        server = settings["server"]
        port = int(settings["port"])
        https = int(settings["https"])
        flowinfo = int(settings["flowinfo"])
        scopeid = int(settings["scopeid"])
        mountpoint = settings["mountpoint"]
        ggainterval = int(settings["ggainterval"])
        datatype = settings["datatype"]

        conn = format_conn(settings["ipprot"], server, port, flowinfo, scopeid)
        with socket.socket(settings["ipprot"], socket.SOCK_STREAM) as self._socket:
            if https:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.load_verify_locations(findcacerts())
                self._socket = context.wrap_socket(self._socket, server_hostname=server)
            self._socket.settimeout(TIMEOUT)
            self._socket.connect(conn)
            self._socket.sendall(self._formatGET(settings))
            # send GGA sentence with request
            # if mountpoint != "":
            #     self._send_GGA(ggainterval, output)
            while not stopevent.is_set():
                rc = self._do_header(self._socket, stopevent, output)
                if rc == "0":  # streaming RTCM3/SPARTN data from mountpoint
                    self._retrycount = 0
                    msg = f"Streaming {datatype} data from {server}:{port}/{mountpoint} ..."
                    self.logger.info(msg)
                    self._app_update_status(True, (msg, "blue"))
                    self._do_data(
                        self._socket,
                        datatype,
                        stopevent,
                        ggainterval,
                        output,
                    )
                elif rc == "1":  # retrieved sourcetable
                    stopevent.set()
                    self._connected = False
                    self._app_update_status(False, ("Sourcetable retrieved", "blue"))
                else:  # error message
                    self.logger.critical(
                        f"Error connecting to {server}:{port}/{mountpoint=}: {rc}"
                    )
                    stopevent.set()
                    self._connected = False
                    self._app_update_status(False, (f"Error!: {rc}", "red"))

    def _do_header(self, sock: socket, stopevent: Event, output: object) -> str:
        """
        THREADED
        Parse response header lines.

        :param socket sock: socket
        :param Event stopevent: stop event
        :return: return status or error message
        :rtype: str
        """

        stable = []
        data = True

        while data and not stopevent.is_set():
            try:
                data = sock.recv(DEFAULT_BUFSIZE)
                header_lines = data.decode(encoding="utf-8").split("\r\n")
                for line in header_lines:
                    # if sourcetable request, populate list
                    if True in [line.find(cd) > 0 for cd in HTTPERR]:  # HTTP 4nn, 50n
                        return line
                    if line.find("STR;") >= 0:  # sourcetable entry
                        strbits = line.split(";")
                        if strbits[0] == "STR":
                            strbits.pop(0)
                            stable.append(strbits)
                    elif line.find("ENDSOURCETABLE") >= 0:  # end of sourcetable
                        self._settings["sourcetable"] = stable
                        mp, dist = self._get_closest_mountpoint()
                        self._do_output(output, stable, (mp, dist))
                        self.logger.info(f"Complete sourcetable follows...\n{stable}")
                        return "1"

            except UnicodeDecodeError:
                data = False

        return "0"

    def _do_data(
        self,
        sock: socket,
        datatype: str,
        stopevent: Event,
        ggainterval: int,
        output: object,
    ):
        """
        THREADED
        Read and parse incoming NTRIP RTCM3/SPARTN data stream.

        :param socket sock: socket
        :param str datatype: RTCM or SPARTN
        :param Event stopevent: stop event
        :param int ggainterval: GGA transmission interval seconds
        :param object output: output stream for raw data
        :raises: TimeoutError if inactivity timeout exceeded
        """

        parser = None
        raw_data = None
        parsed_data = None
        last_activity = datetime.now()

        # parser will wrap socket as SocketStream
        if datatype == SPARTN:
            parser = SPARTNReader(
                sock,
                quitonerror=ERR_IGNORE,
                bufsize=DEFAULT_BUFSIZE,
                decode=self._settings["spartndecode"],
                key=self._settings["spartnkey"],
                basedate=self._settings["spartnbasedate"],
            )
        else:
            parser = UBXReader(
                sock,
                protfilter=RTCM3_PROTOCOL,
                quitonerror=ERR_IGNORE,
                bufsize=DEFAULT_BUFSIZE,
                labelmsm=True,
            )

        while not stopevent.is_set():
            try:
                raw_data, parsed_data = parser.read()
                if raw_data is None:
                    if datetime.now() - last_activity > timedelta(
                        seconds=self._timeout
                    ):
                        raise TimeoutError(
                            f"Inactivity timeout error after {self._timeout} seconds"
                        )
                else:
                    self._do_output(output, raw_data, parsed_data)
                    last_activity = datetime.now()
                self._send_GGA(ggainterval, output)

            except (
                RTCMMessageError,
                RTCMParseError,
                RTCMTypeError,
                SPARTNMessageError,
                SPARTNParseError,
                SPARTNTypeError,
            ) as err:
                parsed_data = f"Error parsing data stream {err}"
                self._do_output(output, raw_data, parsed_data)
                continue

    def _do_output(self, output: object, raw: bytes, parsed: object):
        """
        THREADED
        Send sourcetable/closest mountpoint or RTCM3/SPARTN data to designated output medium.

        If output is Queue, will send both raw and parsed data.

        :param object output: writeable output medium for raw data
        :param bytes raw: raw data
        :param object parsed: parsed message
        """

        if hasattr(parsed, "identity"):
            self.logger.info(f"{type(parsed).__name__} received: {parsed.identity}")
        self.logger.debug(parsed)
        if output is not None:
            # serialize sourcetable if outputting to stream
            if isinstance(raw, list) and not isinstance(output, Queue):
                raw = self._serialize_srt(raw)
            if isinstance(output, (Serial, BufferedWriter)):
                output.write(raw)
            elif isinstance(output, TextIOWrapper):
                output.write(str(parsed))
            elif isinstance(output, Queue):
                output.put(raw if self.__app == CLIAPP else (raw, parsed))
            elif isinstance(output, socket.socket):
                output.sendall(raw)

        # notify any calling app that data is available
        if self.__app is not None:
            if hasattr(self.__app, "set_event"):
                self.__app.set_event(NTRIP_EVENT)

    def _serialize_srt(self, sourcetable: list) -> bytes:
        """
        Serialize sourcetable.

        :param list sourcetable: sourcetable as list
        :return: sourcetable as bytes
        :rtype: bytes
        """

        srt = ""
        for row in sourcetable:
            for i, col in enumerate(row):
                dlm = "," if i < len(row) - 1 else "\r\n"
                srt += f"{col}{dlm}"
        return bytearray(srt, "utf-8")

    @property
    def stopevent(self) -> Event:
        """
        Getter for stop event.

        :return: stop event
        :rtype: Event
        """

        return self._stopevent
