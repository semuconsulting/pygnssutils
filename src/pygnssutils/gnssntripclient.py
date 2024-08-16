"""
gnssntripclient.py

NTRIP client class, retrieving sourcetable and RTCM3 or SPARTN
correction data from an NTRIP server and (optionally) sending
the correction data to a designated writeable output medium
(serial, file, socket, queue).

Can also transmit client position back to NTRIP server at specified
intervals via formatted NMEA GGA sentences.

Implemented in accordance with RTCM NTRIP client devices best practice
guidelines (rtcm-paper-2023-sc104-1344):

https://rtcm.myshopify.com/collections/differential-global-navigation-satellite-dgnss-standards/products/rtcm-paper-2023-sc104-1344-ntrip-client-devices-best-practices

Calling app, if defined, can implement the following methods:
- set_event() - create <<ntrip_read>> event
- dialog() - return reference to NTRIP config client GUI dialog
- get_coordinates() - return live gnss status data from receiver

NB: This utility is used by PyGPSClient - do not change footprint of
any public methods without first checking impact on PyGPSClient -
https://github.com/semuconsulting/PyGPSClient.

Created on 03 Jun 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

# pylint: disable=invalid-name

import socket
from datetime import datetime, timedelta, timezone
from io import BufferedWriter, TextIOWrapper
from logging import getLogger
from os import getenv
from queue import Queue
from threading import Event, Thread

from pynmeagps import GET, NMEAMessage
from pyspartn import SPARTNReader
from pyubx2 import ERR_IGNORE, RTCM3_PROTOCOL, UBXReader
from requests import Session, get
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError as ConnError
from requests.exceptions import HTTPError, Timeout
from serial import Serial
from urllib3.exceptions import ReadTimeoutError
from urllib3.response import HTTPResponse
from urllib3.util.retry import Retry

from pygnssutils._version import __version__ as VERSION
from pygnssutils.exceptions import ParameterError
from pygnssutils.globals import (
    CLIAPP,
    FIXES,
    MAXPORT,
    NOGGA,
    NTRIP_EVENT,
    OUTPORT_NTRIP,
    UTF8,
)
from pygnssutils.helpers import find_mp_distance, ipprot2int, serialize_srt

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
        :param object spartnbasedate: (kwarg) SPARTN decryption basedate (now(utc))
        :param object output: (kwarg) output handler (None)
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
            self._settings["reflat"] = float(kwargs.get("reflat", 0.0))
            self._settings["reflon"] = float(kwargs.get("reflon", 0.0))
            self._settings["refalt"] = float(kwargs.get("refalt", 0.0))
            self._settings["refsep"] = float(kwargs.get("refsep", 0.0))
            self._settings["spartndecode"] = int(kwargs.get("spartndecode", 0))
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

    def _formatGGA(self) -> tuple:
        """
        THREADED
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

    def _send_GGA(self, ggainterval: int, output: object):
        """
        THREADED
        Send NMEA GGA sentence to NTRIP server at prescribed interval.

        :param int ggainterval: GGA send interval in seconds (-1 = don't send)
        :param stream stream: caster TCP connection
        :param object output: writeable output medium e.g. serial port
        """

        if ggainterval != NOGGA:
            if datetime.now() > self._last_gga + timedelta(seconds=ggainterval):
                raw_data, parsed_data = self._formatGGA()
                if raw_data is not None:
                    # self._socket.sendall(raw_data) TODO
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

    def _do_sourcetable(
        self, stream: HTTPResponse, settings: dict, stopevent: Event, output: object
    ):
        """THREADED
        Process sourcetable from NTRIP caster into list.

        :param HTTPResponse stream: raw data stream fron NTRIP caster
        :param dict settings: settings
        :param object output: output handler
        :param Event stopevent: stop event
        """

        stable = []
        sourcetable = stream.read().decode(UTF8).split("\r\n")
        for line in sourcetable:
            if line.find("STR;") >= 0:
                strbits = line.split(";")
                if strbits[0] == "STR":
                    strbits.pop(0)
                    stable.append(strbits)
        settings["sourcetable"] = stable
        mp, dist = self._get_closest_mountpoint()
        self._do_output(output, stable, (mp, dist))
        stopevent.set()
        self._connected = False
        self.logger.info(f"Complete sourcetable follows...\n{stable}")
        self._app_update_status(False, ("Sourcetable retrieved", "blue"))

    def _do_data(
        self, stream: HTTPResponse, settings: dict, stopevent: Event, output: object
    ):
        """
        THREADED
        Process incoming RTCM or SPARTN datastream.

        :param HTTPResponse stream: raw data stream fron NTRIP caster
        :param dict settings: settings
        :param object output: output handler
        :param Event stopevent: stop event
        """

        print(type(stream))

        msg = (
            f"Streaming {settings["datatype"]} data from "
            f"{settings["server"]}:{settings["port"]}/{settings["mountpoint"]} ..."
        )
        self.logger.info(msg)
        self._app_update_status(True, (msg, "blue"))
        if settings["datatype"] == SPARTN:
            parser = SPARTNReader(
                stream,
                quitonerror=ERR_IGNORE,
                decode=settings["spartndecode"],
                key=settings["spartnkey"],
                basedate=settings["spartnbasedate"],
            )
        else:
            parser = UBXReader(
                stream,
                protfilter=RTCM3_PROTOCOL,
                quitonerror=ERR_IGNORE,
                labelmsm=True,
            )
        while not stopevent.is_set():
            raw, parsed = parser.read()
            if raw is not None:
                self._do_output(output, raw, parsed)
            if settings["ggainterval"] != NOGGA:
                self._send_GGA(settings["ggainterval"], output)

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

        # self._retrycount = 0
        scheme = "https" if settings["https"] else "http"
        # strip 'www.' from url to minimise SSL: CERTIFICATE_VERIFY_FAILED errors
        server = settings["server"].replace("www.", "")
        port = settings["port"]
        mountpoint = settings["mountpoint"]
        ggainterval = settings["ggainterval"]
        gga, _ = self._formatGGA()

        url = f"{scheme}://{server}:{port}/{mountpoint}"
        basic = HTTPBasicAuth(settings["ntripuser"], settings["ntrippassword"])
        sess = Session()
        retries = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 501, 503],
            allowed_methods={"GET"},
        )
        sess.mount("http://", HTTPAdapter(max_retries=retries))
        sess.mount("https://", HTTPAdapter(max_retries=retries))
        headers = {
            "User-Agent": f"NTRIP pygnssutils/{VERSION}",
        }
        if settings["version"] == "2.0":
            headers["Ntrip-Version"] = "Ntrip/2.0"
        if ggainterval != NOGGA:
            headers["Ntrip-GGA"] = f"{gga.decode(UTF8).rstrip()}"

        try:

            req = get(
                url, headers=headers, timeout=self._timeout, stream=True, auth=basic
            )
            with req.raw as stream:
                content = req.headers["Content-Type"]
                if content == "gnss/sourcetable":
                    self._do_sourcetable(stream, settings, stopevent, output)
                elif content == "gnss/data":
                    self._do_data(stream, settings, stopevent, output)

        except (HTTPError, ConnError, Timeout, ReadTimeoutError) as err:
            self.logger.critical(
                f"Error connecting to {server}:{port}/{mountpoint=}: {err}"
            )
            stopevent.set()
            self._connected = False
            self._app_update_status(False, (f"Error!: {err}", "red"))

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
                raw = serialize_srt(raw)
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

    @property
    def stopevent(self) -> Event:
        """
        Getter for stop event.

        :return: stop event
        :rtype: Event
        """

        return self._stopevent
