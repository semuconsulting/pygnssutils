"""
gnssntripclient.py

NTRIP client class; essentially an HTTP client capable of
retrieving sourcetable and RTCM3 or SPARTN
correction data from an NTRIP server and (optionally) sending
the correction data to a designated writeable output medium
(serial, file, socket, queue).

Can also transmit client position back to NTRIP server at specified
intervals via formatted NMEA GGA sentences.

Calling app, if defined, can implement the following methods:
- set_event() - create <<ntrip_read>> event
- dialog() - return reference to NTRIP config client dialog
- get_coordinates() - return coordinates from receiver

NB: This utility is used by PyGPSClient - do not change footprint of
any public methods without first checking impact on PyGPSClient -
https://github.com/semuconsulting/PyGPSClient.

Created on 03 Jun 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

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
from pyubx2 import ERR_LOG, RTCM3_PROTOCOL, UBXReader
from serial import Serial

from pygnssutils._version import __version__ as VERSION
from pygnssutils.exceptions import ParameterError
from pygnssutils.globals import (
    CLIAPP,
    DEFAULT_BUFSIZE,
    ENCODE_CHUNKED,
    ENCODE_COMPRESS,
    ENCODE_DEFLATE,
    ENCODE_GZIP,
    ENCODE_NONE,
    FIXES,
    MAXPORT,
    NOGGA,
    NTRIP_EVENT,
    OUTPORT_NTRIP,
)
from pygnssutils.helpers import find_mp_distance, ipprot2int
from pygnssutils.socketwrapper import SocketWrapper

TIMEOUT = 3
GGALIVE = 0
GGAFIXED = 1
DLGTNTRIP = "NTRIP Configuration"
RTCM = "rtcm"
SPARTN = "spartn"
MAX_RETRY = 5
RETRY_INTERVAL = 5
INACTIVITY_TIMEOUT = 10
WAITTIME = 3


class GNSSNTRIPClient:
    """
    NTRIP client class.
    """

    def __init__(
        self,
        app=None,
        **kwargs,
    ):
        """
        Constructor.

        :param object app: application from which this class is invoked (None)
        :param int retries: (kwarg) maximum failed connection retries (5)
        :param int retryinterval: (kwarg) retry interval in seconds (10)
        :param int timeout: (kwarg) inactivity timeout in seconds (10)
        """

        self.__app = app  # Reference to calling application class (if applicable)
        # configure logger with name "pygnssutils" in calling module
        self.logger = getLogger(__name__)
        self._ntripqueue = Queue()
        # initialise and persist settings to allow any calling app to retrieve them
        self._settings = {}
        self.settings = self._settings

        try:
            self._retries = int(kwargs.pop("retries", MAX_RETRY))
            self._retryinterval = int(kwargs.pop("retryinterval", RETRY_INTERVAL))
            self._timeout = int(kwargs.pop("timeout", INACTIVITY_TIMEOUT))
        except (ParameterError, ValueError, TypeError) as err:
            msg = f"Invalid input arguments {err}"
            self._app_update_status(False, (str(err), "red"))
            raise ParameterError(msg + "\nType gnssntripclient -h for help.") from err

        self._socket = None
        self._connected = False
        self._stopevent = Event()
        self._ntrip_thread = None
        self._last_gga = datetime.fromordinal(1)
        self._retrycount = 0
        self._ntrip_version = "2.0"
        self._response_headers = {}
        self._response_status = {}
        self._response_body = None
        self._output = None

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

    def run(self, **kwargs) -> bool:
        """
        Open NTRIP client connection.

        If calling application implements a "get_coordinates" method to
        obtain live coordinates (i.e. from GNSS receiver), the method will
        use these instead of fixed reference coordinates.

        User login credentials can be obtained from environment variables
        PYGPSCLIENT_USER and PYGPSCLIENT_PASSWORD, or passed as kwargs.

        :param str server: (kwarg) NTRIP server URL ("")
        :param int port: (kwarg) NTRIP port (2101)
        :param int https: (kwarg) HTTPS (TLS) connection? 0 = HTTP 1 = HTTPS (0)
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
        :param object stopevent: (kwarg) stopevent to terminate `run()` (internal `Event()`)
        :returns: boolean flag 0 = stream terminated, 1 = streaming data
        :rtype: bool
        """

        # pylint: disable=unused-variable

        try:
            self._stopevent = kwargs.get("stopevent", self._stopevent)
            self._last_gga = datetime.fromordinal(1)
            self.settings = kwargs
            self._output = kwargs.get("output", None)

            if self._settings["server"] == "":
                raise ParameterError(f"Invalid server URL {self._settings['server']}")
            if not 1 < self._settings["port"] < MAXPORT:
                raise ParameterError(f"Invalid port {self._settings['port']}")

        except (ParameterError, ValueError, TypeError) as err:
            msg = f"Invalid input arguments - {err}"
            self._app_update_status(False, (str(err), "red"))
            raise ParameterError(msg + "\nType gnssntripclient -h for help.") from err

        self._connected = True
        self._start_read_thread(
            self._settings,
            self._stopevent,
            self._output,
        )
        if self.settings["mountpoint"] != "":
            return 1
        return 0

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
            stopevent.clear()
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
            # while self._ntrip_thread.is_alive():
            #     sleep(0.1)
            self._ntrip_thread = None

        self._app_update_status(False, ("Disconnected", "blue"))

    def stop(self):
        """
        Close NTRIP server connection.
        """

        self._stop_read_thread()
        self._connected = False

    def _read_thread(
        self,
        settings: dict,
        stopevent: Event,
        output: object,
    ):
        """
        Try connecting to NTRIP caster.

        :param dict settings: settings as dictionary
        :param Event stopevent: stop event
        :param object output: output stream for raw data
        """

        self._retrycount = 0
        hostname = settings["server"]
        errc = ""  # critical error message

        while self._retrycount <= self._retries and not stopevent.is_set():

            try:

                self._do_connection(settings, stopevent, output)

            except ssl.SSLCertVerificationError as err:
                errc = err.strerror
                if "certificate is not valid for 'www." in err.strerror:
                    errc += (
                        f" - try using '{hostname[4:]}' rather than "
                        f"'{hostname}' for the NTRIP caster URL"
                    )
                elif "unable to get local issuer certificate" in err.strerror:
                    errc += f" - try adding the NTRIP caster URL SSL certificate to {findcacerts()}"
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
                if self._retrycount == self._retries:
                    errc = errm  # no more retries so critical error
                else:
                    self._retrycount += 1
                    errm += (
                        f". Retrying in {self._retryinterval * (2**self._retrycount)} secs "
                        f"({self._retrycount}/{self._retries}) ..."
                    )
                    self._app_update_status(False, (errm, "red"))
            except Exception as err:  # pylint: disable=broad-exception-caught
                errc = str(repr(err))

            if errc != "":  # break connection on critical error
                stopevent.set()
                self._connected = False
                self._app_update_status(False, (errc, "red"))
                break

            sleep(self._retryinterval * (2**self._retrycount))

    def _do_connection(
        self,
        settings: dict,
        stopevent: Event,
        output: object,
    ):
        """
        Opens socket to NTRIP server and reads incoming data.

        :param dict settings: settings as dictionary
        :param Event stopevent: stop event
        :param object output: output stream for raw data
        :raises: Various socket error types if connection fails
        """

        hostname = settings["server"]
        port = int(settings["port"])
        https = int(settings["https"])

        # create a IPv4, IPv6 dual-stack socket for connection
        ip = socket.gethostbyname(hostname)
        with socket.create_connection((ip, port), self._timeout) as self._socket:
            if https:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.load_verify_locations(findcacerts())
                self._socket = context.wrap_socket(
                    self._socket, server_hostname=hostname
                )

            self._do_request(self._socket, settings, output)

            if not self.responseok:
                stopevent.set()
                self._connected = False
                msg = (
                    f"Connection failed {self._response_status['code']} "
                    f"{self._response_status['description']}"
                )
                self._app_update_status(False, (msg, "red"))
            elif self.is_sourcetable:
                stable = self._parse_sourcetable(self.response_body)
                self._settings["sourcetable"] = stable
                mp, dist = self._get_closest_mountpoint()
                self._do_output(output, stable, (mp, dist))
                self._app_update_status(False, ("Sourcetable retrieved", "blue"))
                stopevent.set()
                self._connected = False

    def _do_request(self, sock: socket, settings: dict, output: object):
        """
        Send formatted HTTP(S) GET request and process response.

        :param socket sock: raw socket
        :param dict settings: settings
        :param object output: output stream for raw data
        """

        hostname = settings["server"]
        port = int(settings["port"])
        datatype = settings["datatype"].lower()
        ggainterval = settings["ggainterval"]
        path = settings["mountpoint"]

        request_headers = self._set_headers(settings)
        self.logger.debug(f"Request headers:\n{request_headers}")
        self._response_body = b""
        awaiting_response = True

        sock.sendall(request_headers.encode())

        while True:
            data = sock.recv(DEFAULT_BUFSIZE)
            if len(data) == 0:
                break
            if awaiting_response:
                data = self._parse_response_header(data)
                awaiting_response = False
            if (
                self.is_gnssdata
                and not awaiting_response
                and not self._stopevent.is_set()
            ):
                # stream gnss data until disconnection
                msg = f"Streaming {datatype} data from {hostname}:{port}/{path} ..."
                self._app_update_status(True, (msg, "blue"))
                self._parse_ntrip_data(
                    sock,
                    datatype,
                    ggainterval,
                    output,
                )
            if not self.is_gnssdata and not awaiting_response:
                self._response_body = self._response_body + data

    def _set_headers(self, settings: dict) -> str:
        """
        Construct HTTP(S) GET request headers.

        :param dict settings: settings
        :return: request headers as string
        :rtype: str
        """

        headers = ""
        path = settings["mountpoint"]
        hostname = settings["server"]
        port = settings["port"]
        user = settings["ntripuser"]
        password = settings["ntrippassword"]
        ntrip_version = settings["version"]
        ggainterval = settings["ggainterval"]
        if ggainterval == NOGGA:
            gga = ""
        else:
            gga, _ = self._format_gga()

        cred = b64encode(f"{user}:{password}".encode()).decode()
        headers += f"Authorization: Basic {cred}\r\n"
        httpver = "1.1"
        gga_as_data = ""
        if ntrip_version == "2.0":
            headers += "Ntrip-Version: Ntrip/2.0\r\n"
            if ggainterval != NOGGA:
                headers += f"Ntrip-GGA: {gga.decode()}"  # includes \r\n
        else:
            httpver = "1.0"
            if ggainterval != NOGGA:
                gga_as_data = gga.decode()

        return (
            f"GET /{path} HTTP/{httpver}\r\n"
            f"Host: {hostname}:{port}\r\n"
            f"User-Agent: NTRIP pygnssutils/{VERSION}\r\n"
            f"{headers}"
            "Accept: */*\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{gga_as_data}"
        )

    def _parse_response_header(self, data: bytes) -> bytes:
        """
        Parse response header and body.

        :param bytes data: raw data from socket
        :return: response body as bytes
        :rtype: bytes
        :raises: Exception
        """

        try:
            hdrbdy = data.split(b"\r\n\r\n", 1)
            if len(hdrbdy) == 1:  # no body content
                # some poorly implemented ICY responses only have
                # a single "\r\n" between response header and body
                if hdrbdy[0][:12] == b"ICY 200 OK\r\n":
                    hdr, bdy = hdrbdy[0][:10], hdrbdy[0][12:]
                else:
                    hdr, bdy = hdrbdy[0], b""
            else:  # has body content
                hdr, bdy = hdrbdy
            hdr = hdr.decode().split("\r\n")
            status = hdr[0].split(" ", 3)
            self._response_status = {
                "protocol": status[0],
                "code": int(status[1]),
                "description": status[2],
            }
            for line in hdr:
                rsp = line.split(":", 1)
                if len(rsp) > 1:
                    self._response_headers[rsp[0].lower().strip()] = rsp[1].strip()
            self.logger.debug(
                f"Response: {self._response_status}\n{self._response_headers}"
            )
            return bdy
        except Exception as err:
            raise ConnectionAbortedError(
                f"Unable to parse response headers - {err}"
            ) from err  # caught in _read_thread()

    def _parse_ntrip_data(
        self,
        sock: socket,
        datatype: str,
        ggainterval: int,
        output: object,
    ):
        """
        Read and parse incoming NTRIP RTCM3/SPARTN data stream.

        :param socket sock: raw socket
        :param str datatype: RTCM or SPARTN
        :param int ggainterval: GGA transmission interval seconds
        :raises: TimeoutError if inactivity timeout exceeded
        """

        parser = None
        raw_data = None
        parsed_data = None
        last_activity = datetime.now()
        stream = SocketWrapper(sock, self.encoding)

        # parser will wrap socket as SocketStream
        if datatype == SPARTN:
            parser = SPARTNReader(
                stream,
                quitonerror=ERR_LOG,
                bufsize=DEFAULT_BUFSIZE,
                decode=self._settings["spartndecode"],
                key=self._settings["spartnkey"],
                basedate=self._settings["spartnbasedate"],
            )
        else:
            parser = UBXReader(
                stream,
                protfilter=RTCM3_PROTOCOL,
                quitonerror=ERR_LOG,
                bufsize=DEFAULT_BUFSIZE,
                labelmsm=True,
            )

        while not self._stopevent.is_set():
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
                    if hasattr(parsed_data, "identity"):
                        self.logger.info(f"Message received: {parsed_data.identity}")
                    self.logger.debug(parsed_data)
                    self._do_output(output, raw_data, parsed_data)
                    last_activity = datetime.now()
                self._send_gga(ggainterval, output)

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

    def _parse_sourcetable(self, response: str) -> list:
        """
        Parse raw gnss/sourcetable response into list of mountpoints.

        :param str response: response body as string
        :return: sourcetable as list of mountpoints
        :rtype: list
        """

        self.logger.info(f"Sourcetable:\n{response}")
        sourcetable = []
        response = response.split("\r\n")
        for line in response:
            if line.find("STR;") >= 0:  # mountpoint entry
                strbits = line.split(";")
                if strbits[0] == "STR":
                    strbits.pop(0)
                    sourcetable.append(strbits)
        return sourcetable

    def _serialize_sourcetable(self, sourcetable: list) -> bytes:
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

    def _format_gga(self) -> tuple:
        """
        Format NMEA GGA sentence using pynmeagps. The raw string
        output is suitable for sending to an NTRIP socket.
        GGA timestamp will default to current UTC. GGA quality is
        derived from fix string.

        :return: tuple of (raw NMEA message as bytes, NMEAMessage)
        :rtype: tuple
        :rtype: tuple
        """

        try:
            lat, lon, alt, sep, fixs, sip, hdop, diffage, diffstation = (
                self._app_get_coordinates()
            )
            lat = float(lat)
            lon = float(lon)
            fixi = FIXES.get(fixs, 1)
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

    def _send_gga(self, ggainterval: int, output: object):
        """
        Send NMEA GGA sentence to NTRIP server at prescribed interval.

        :param int ggainterval: GGA send interval in seconds (-1 = don't send)
        :param object output: writeable output medium e.g. serial port
        """

        if ggainterval != NOGGA:
            if datetime.now() > self._last_gga + timedelta(seconds=ggainterval):
                raw_data, parsed_data = self._format_gga()
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
                "Closest mountpoint to reference location "
                f"({lat}, {lon}) = {closest_mp}, {dist} km."
            )

        except ValueError:
            return None, None
        return closest_mp, dist

    def _do_output(self, output: object, raw: bytes, parsed: object):
        """
        Send sourcetable/closest mountpoint or RTCM3/SPARTN data to designated output medium.

        If output is Queue, will send both raw and parsed data.

        :param object output: writeable output medium for raw data
        :param bytes raw: raw data
        :param object parsed: parsed message
        """

        if output is not None:
            # serialize sourcetable if outputting to stream
            if isinstance(raw, list) and not isinstance(output, Queue):
                raw = self._serialize_sourcetable(raw)
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

    def _app_update_status(self, status: bool, msgt: tuple = None):
        """
        Update NTRIP connection status in calling application.

        :param bool status: NTRIP server connection status
        :param tuple msgt: (message, color)
        """

        if msgt[1] == "red":
            self.logger.error(msgt[0])
        else:
            self.logger.info(msgt[0])
        if self.__app is not None:
            if hasattr(self.__app, "dialog"):
                dlg = self.__app.dialog(DLGTNTRIP)
                if dlg is not None:
                    if hasattr(dlg, "set_controls"):
                        dlg.set_controls(status, msgt)

    def _app_get_coordinates(self) -> tuple:
        """
        Get live coordinates from receiver, or use fixed
        reference position, depending on ggamode setting.

        NB: 'fix' is a string e.g. "3D" or "RTK FLOAT"

        :returns: tuple of coordinate and fix data
        :rtype: tuple
        """

        lat = lon = alt = sep = 0.0
        fix, sip, hdop, diffage, diffstation = ("3D", 15, 0.98, 0, 0)
        if self._settings["ggamode"] == GGAFIXED:  # fixed reference position
            lat = self._settings["reflat"]
            lon = self._settings["reflon"]
            alt = self._settings["refalt"]
            sep = self._settings["refsep"]
        elif self.__app is not None:
            if hasattr(self.__app, "get_coordinates"):  # live position from receiver
                coords = self.__app.get_coordinates()
                if isinstance(coords, tuple):  # old version (PyGPSClient <=1.4.19)
                    _, lat, lon, alt, sep = coords
                else:  # new version uses dict (PyGPSClient >=1.4.20)
                    lat = coords.get("lat", lat)
                    lon = coords.get("lon", lon)
                    alt = coords.get("alt", alt)
                    sep = coords.get("sep", sep)
                    sip = coords.get("sip", sip)
                    fix = coords.get("fix", fix)
                    hdop = coords.get("hdop", hdop)
                    diffage = coords.get("diffage", diffage)
                    diffstation = coords.get("diffstation", diffstation)

        lat, lon, alt, sep = [
            0.0 if c == "" else float(c) for c in (lat, lon, alt, sep)
        ]

        return lat, lon, alt, sep, fix, sip, hdop, diffage, diffstation

    @property
    def settings(self):
        """
        Getter for NTRIP settings.
        """

        return self._settings

    @settings.setter
    def settings(self, kwargs: dict):
        """
        Setter for NTRIP settings.

        :param dict kwargs: NTRIP settings (see run() method for kwargs)
        """

        ipprot = kwargs.get("ipprot", "IPv4")
        self._settings["ipprot"] = ipprot2int(ipprot)
        self._settings["server"] = kwargs.get("server", "")
        self._settings["port"] = int(kwargs.get("port", OUTPORT_NTRIP))
        self._settings["https"] = int(kwargs.get("https", 0))
        self._settings["flowinfo"] = int(kwargs.get("flowinfo", 0))
        self._settings["scopeid"] = int(kwargs.get("scopeid", 0))
        self._settings["mountpoint"] = kwargs.get("mountpoint", "")
        self._settings["sourcetable"] = kwargs.get("sourcetable", [])
        self._settings["datatype"] = kwargs.get("datatype", RTCM).upper()
        self._settings["version"] = kwargs.get("version", "2.0")
        self._ntrip_version = self._settings["version"]
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
        self._settings["spartnkey"] = kwargs.get("spartnkey", getenv("MQTTKEY", None))
        self._settings["spartnbasedate"] = kwargs.get(
            "spartbasedate", datetime.now(timezone.utc)
        )

    @property
    def connected(self):
        """
        Connection status getter.
        """

        return self._connected

    @property
    def responseok(self) -> bool:
        """
        Response OK indicator (i.e. 200 OK).

        :return: True/False
        :rtype: bool
        """

        return self._response_status["code"] == 200

    @property
    def status(self) -> dict:
        """
        Get response status e.g. {protocol: "HTTP/1.1", code: 200, description: "OK"}.

        :return: dict of protocol, status code, status description
        :rtype: dict
        """

        return self._response_status

    @property
    def content_type(self) -> str:
        """
        Get content type e.g. "text/html" or "gnss/data".

        :return: content type
        :rtype: str
        """

        return self._response_headers.get("content-type", "")

    @property
    def response_body(self) -> object:
        """
        Get response body if available.

        :return: response body as bytes or string, depending on encoding
        :rtype: object
        """

        if "text/" in self.content_type or self.is_sourcetable:
            return self._response_body.decode()
        return self._response_body

    @property
    def encoding(self) -> int:
        """
        Get response transfer-encoding settings
        (chunked, deflate, compress, gzip).

        :return: OR'd transfer-encoding value
        :rtype: int
        """

        encoding = ENCODE_NONE
        enc = self._response_headers.get("transfer-encoding", "").lower()

        if "chunked" in enc:
            encoding |= ENCODE_CHUNKED
        if "deflate" in enc:  # zlib compression
            encoding |= ENCODE_DEFLATE
        if "compress" in enc:  # Lempel-Ziv-Welch (LZW) compression
            encoding |= ENCODE_COMPRESS
        if "gzip" in enc:  # Lempel-Zif compression with 32-bit CRC
            encoding |= ENCODE_GZIP

        return encoding

    @property
    def is_gnssdata(self) -> bool:
        """
        Check if response is NTRIP data stream (RTCM or SPARTN).

        :return: gnss/data True/False
        :rtype: bool
        """

        return (self._ntrip_version == "2.0" and self.content_type == "gnss/data") or (
            self._ntrip_version == "1.0" and self.status["protocol"].lower() == "icy"
        )

    @property
    def is_sourcetable(self) -> bool:
        """
        Check if response is NTRIP sourcetable.

        :return: gnss/sourcetable True/False
        :rtype: bool
        """

        return (
            self._ntrip_version == "2.0" and self.content_type == "gnss/sourcetable"
        ) or (
            self._ntrip_version == "1.0"
            and self.status["protocol"].lower() == "sourcetable"
        )

    @property
    def stopevent(self) -> Event:
        """
        Getter for stop event.

        :return: stop event
        :rtype: Event
        """

        return self._stopevent
