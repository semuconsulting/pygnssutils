"""
gnssntripclient.py

Command line utility, installed with PyPi library pygnssutils,
which acts as an NTRIP client, retrieving sourcetable and RTCM3
correction data from an NTRIP server and (optionally)
sending the correction data to a designated writeable output
medium (serial, file, socket, queue).

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

import os
import socket
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from base64 import b64encode
from datetime import datetime, timedelta
from io import BufferedWriter, TextIOWrapper
from queue import Queue
from threading import Event, Thread
from time import sleep

from pynmeagps import GET, NMEAMessage
from pyrtcm import RTCMMessageError, RTCMParseError, RTCMTypeError
from pyubx2 import ERR_IGNORE, RTCM3_PROTOCOL, UBXReader
from serial import Serial

from pygnssutils._version import __version__ as VERSION
from pygnssutils.exceptions import ParameterError
from pygnssutils.globals import (
    DEFAULT_BUFSIZE,
    EPILOG,
    HTTPERR,
    LOGLIMIT,
    MAXPORT,
    NOGGA,
    NTRIP_EVENT,
    OUTPORT_NTRIP,
    VERBOSITY_LOW,
    VERBOSITY_MEDIUM,
)
from pygnssutils.helpers import find_mp_distance, format_conn, ipprot2int

TIMEOUT = 10
GGALIVE = 0
GGAFIXED = 1
DLGTNTRIP = "NTRIP Configuration"


class GNSSNTRIPClient:
    """
    NTRIP client class.
    """

    def __init__(self, app=None, **kwargs):
        """
        Constructor.

        :param object app: application from which this class is invoked (None)
        :param object verbosity: (kwarg) log verbosity (1 = medium)
        :param object logtofile: (kwarg) log to file (0 = False)
        :param object logpath: (kwarg) log file path (".")
        """

        self.__app = app  # Reference to calling application class (if applicable)
        self._validargs = True
        self._loglines = 0
        self._ntripqueue = Queue()
        # persist settings to allow any calling app to retrieve them
        self._settings = {
            "ipprot": socket.AF_INET,
            "server": "",
            "port": 2101,
            "flowinfo": 0,
            "scopeid": 0,
            "mountpoint": "",
            "distance": "",
            "version": "2.0",
            "user": "anon",
            "password": "password",
            "ggainterval": "None",
            "ggamode": GGALIVE,
            "sourcetable": [],
            "reflat": 0.0,
            "reflon": 0.0,
            "refalt": 0.0,
            "refsep": 0.0,
        }

        try:
            self._verbosity = int(kwargs.get("verbosity", VERBOSITY_MEDIUM))
            self._logtofile = int(kwargs.get("logtofile", 0))
            self._logpath = kwargs.get("logpath", ".")

        except (ParameterError, ValueError, TypeError) as err:
            self._do_log(
                f"Invalid input arguments {kwargs}\n{err}\nType gnssntripclient -h for help.",
                VERBOSITY_LOW,
            )
            self._validargs = False

        self._socket = None
        self._connected = False
        self._stopevent = Event()
        self._ntrip_thread = None
        self._last_gga = datetime.fromordinal(1)
        self._logfile = ""

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
        NTRIP_USER and NTRIP_PASSWORD, or passed as kwargs.

        :param str ipprot: (kwarg) IP protocol IPv4/IPv6 ("IPv4")
        :param str server: (kwarg) NTRIP server URL ("")
        :param int port: (kwarg) NTRIP port (2101)
        :param int flowinfo: (kwarg) flowinfo for IPv6 (0)
        :param int scopeid: (kwarg) scopeid for IPv6 (0)
        :param str mountpoint: (kwarg) NTRIP mountpoint ("", leave blank to get sourcetable)
        :param str version: (kwarg) NTRIP protocol version ("2.0")
        :param str user: (kwarg) login user ("anon" or env variable NTRIP_USER)
        :param str password: (kwarg) login password ("password" or env variable NTRIP_PASSWORD)
        :param int ggainterval: (kwarg) GGA sentence transmission interval (-1 = None)
        :param int ggamode: (kwarg) GGA pos source; 0 = live from receiver, 1 = fixed reference (0)
        :param str reflat: (kwarg) reference latitude (0.0)
        :param str reflon: (kwarg) reference longitude (0.0)
        :param str refalt: (kwarg) reference altitude (0.0)
        :param str refsep: (kwarg) reference separation (0.0)
        :param object output: (kwarg) writeable output medium (serial, file, socket, queue) (None)
        :returns: boolean flag 0 = terminated, 1 = Ok to stream RTCM3 data from server
        :rtype: bool
        """
        # pylint: disable=unused-variable

        try:
            user = os.getenv("NTRIP_USER", "anon")
            password = os.getenv("NTRIP_PASSWORD", "password")
            self._last_gga = datetime.fromordinal(1)

            ipprot = kwargs.get("ipprot", "IPv4")
            self.settings["ipprot"] = ipprot2int(ipprot)
            self._settings["server"] = server = kwargs.get("server", "")
            self._settings["port"] = port = int(kwargs.get("port", OUTPORT_NTRIP))
            self._settings["flowinfo"] = int(kwargs.get("flowinfo", 0))
            self._settings["scopeid"] = int(kwargs.get("scopeid", 0))
            self._settings["mountpoint"] = mountpoint = kwargs.get("mountpoint", "")
            self._settings["version"] = kwargs.get("version", "2.0")
            self._settings["user"] = kwargs.get("user", user)
            self._settings["password"] = kwargs.get("password", password)
            self._settings["ggainterval"] = int(kwargs.get("ggainterval", NOGGA))
            self._settings["ggamode"] = int(kwargs.get("ggamode", GGALIVE))
            self._settings["reflat"] = kwargs.get("reflat", 0.0)
            self._settings["reflon"] = kwargs.get("reflon", 0.0)
            self._settings["refalt"] = kwargs.get("refalt", 0.0)
            self._settings["refsep"] = kwargs.get("refsep", 0.0)
            output = kwargs.get("output", None)

            if server == "":
                raise ParameterError(f"Invalid server url {server}")
            if port > MAXPORT or port < 1:
                raise ParameterError(f"Invalid port {port}")

        except (ParameterError, ValueError, TypeError) as err:
            self._do_log(
                f"Invalid input arguments {kwargs}\n{err}\n"
                + "Type gnssntripclient -h for help.",
                VERBOSITY_LOW,
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

        :returns: tuple of (lat, lon, alt, sep)
        :rtype: tuple
        """

        lat = lon = alt = sep = 0.0
        if self._settings["ggamode"] == GGAFIXED:  # Fixed reference position
            lat = self._settings["reflat"]
            lon = self._settings["reflon"]
            alt = self._settings["refalt"]
            sep = self._settings["refsep"]
        elif hasattr(self.__app, "get_coordinates"):  # live position from receiver
            _, lat, lon, alt, sep = self.__app.get_coordinates()

        lat, lon, alt, sep = [
            0.0 if c == "" else float(c) for c in (lat, lon, alt, sep)
        ]

        return lat, lon, alt, sep

    def _formatGET(self, settings: dict) -> str:
        """
        THREADED
        Format HTTP GET Request.

        :param dict settings: settings dictionary
        :return: formatted HTTP GET request
        :rtype: str
        """

        mountpoint = "/" + settings["mountpoint"]
        user = settings["user"] + ":" + settings["password"]
        user = b64encode(user.encode(encoding="utf-8"))
        req = (
            f"GET {mountpoint} HTTP/1.0\r\n"
            + "User-Agent: NTRIP pygnssutils\r\n"
            + "Accept: */*\r\n"
            + f"Authorization: Basic {user.decode(encoding='utf-8')}\r\n"
            + "Connection: close\r\n\r\n"  # NECESSARY!!!
        )
        return req.encode(encoding="utf-8")

    def _formatGGA(self) -> tuple:
        """
        THREADED
        Format NMEA GGA sentence using pynmeagps. The raw string
        output is suitable for sending to an NTRIP socket.

        :return: tuple of (raw NMEA message as bytes, NMEAMessage)
        :rtype: tuple
        """
        # time will default to current UTC

        try:
            lat, lon, alt, sep = self._app_get_coordinates()
            lat = float(lat)
            lon = float(lon)

            parsed_data = NMEAMessage(
                "GP",
                "GGA",
                GET,
                lat=lat,
                NS="S" if lat < 0 else "N",
                lon=lon,
                EW="W" if lon < 0 else "E",
                quality=1,
                numSV=15,
                HDOP=0,
                alt=alt,
                altUnit="M",
                sep=sep,
                sepUnit="M",
                diffAge="",
                diffStation=0,
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
                    self._do_write(output, raw_data, parsed_data)
                self._last_gga = datetime.now()

    def _get_closest_mountpoint(self):
        """
        THREADED
        Find closest mountpoint in sourcetable
        if valid reference lat/lon are available.
        """

        try:
            lat, lon, _, _ = self._app_get_coordinates()
            closest_mp, dist = find_mp_distance(
                float(lat), float(lon), self._settings["sourcetable"]
            )
            if self._settings["mountpoint"] == "":
                self._settings["mountpoint"] = closest_mp
            self._do_log(
                "Closest mountpoint to reference location "
                + f"({lat}, {lon}) = {closest_mp}, {dist} km\n"
            )

        except ValueError:
            pass

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

    def _read_thread(
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
        :param object output: output stream for RTCM3 data
        """

        try:
            server = settings["server"]
            port = int(settings["port"])
            flowinfo = int(settings["flowinfo"])
            scopeid = int(settings["scopeid"])
            mountpoint = settings["mountpoint"]
            ggainterval = int(settings["ggainterval"])
            conn = format_conn(settings["ipprot"], server, port, flowinfo, scopeid)
            with socket.socket(settings["ipprot"], socket.SOCK_STREAM) as self._socket:
                self._socket.settimeout(TIMEOUT)
                self._socket.connect(conn)
                self._socket.sendall(self._formatGET(settings))
                # send GGA sentence with request
                if mountpoint != "":
                    self._send_GGA(ggainterval, output)
                while not stopevent.is_set():
                    rc = self._do_header(self._socket, stopevent)
                    if rc == "0":  # streaming RTMC3 data from mountpoint
                        self._do_log(f"Using mountpoint {mountpoint}\n")
                        self._do_data(self._socket, stopevent, ggainterval, output)
                    elif rc == "1":  # retrieved sourcetable
                        stopevent.set()
                        self._connected = False
                        self._app_update_status(False)
                    else:  # error message
                        stopevent.set()
                        self._connected = False
                        self._app_update_status(False, (f"Error!: {rc}", "red"))
        except (
            socket.gaierror,
            ConnectionRefusedError,
            ConnectionAbortedError,
            ConnectionResetError,
            BrokenPipeError,
            TimeoutError,
            OverflowError,
        ):
            stopevent.set()
            self._connected = False

    def _do_header(self, sock: socket, stopevent: Event) -> str:
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
                    if True in [line.find(cd) > 0 for cd in HTTPERR]:  # HTTP 40x
                        self._do_log(line, VERBOSITY_MEDIUM, False)
                        return line
                    elif line.find("STR;") >= 0:  # sourcetable entry
                        strbits = line.split(";")
                        if strbits[0] == "STR":
                            strbits.pop(0)
                            stable.append(strbits)
                    elif line.find("ENDSOURCETABLE") >= 0:  # end of sourcetable
                        self._settings["sourcetable"] = stable
                        self._get_closest_mountpoint()
                        self._do_log("Complete sourcetable follows...\n")
                        for lines in self._settings["sourcetable"]:
                            self._do_log(lines, VERBOSITY_MEDIUM, False)
                        return "1"

            except UnicodeDecodeError:
                data = False

        return "0"

    def _do_data(
        self, sock: socket, stopevent: Event, ggainterval: int, output: object
    ):
        """
        THREADED
        Read and parse incoming NTRIP RTCM3 data stream.

        :param socket sock: socket
        :param Event stopevent: stop event
        :param int ggainterval: GGA transmission interval seconds
        :param object output: output stream for RTCM3 messages
        """

        # UBXReader will wrap socket as SocketStream
        ubr = UBXReader(
            sock,
            protfilter=RTCM3_PROTOCOL,
            quitonerror=ERR_IGNORE,
            bufsize=DEFAULT_BUFSIZE,
            labelmsm=True,
        )

        raw_data = None
        parsed_data = None
        while not stopevent.is_set():
            try:
                raw_data, parsed_data = ubr.read()
                if raw_data is not None:
                    self._do_write(output, raw_data, parsed_data)
                self._send_GGA(ggainterval, output)

            except (
                RTCMMessageError,
                RTCMParseError,
                RTCMTypeError,
            ) as err:
                parsed_data = f"Error parsing data stream {err}"
                self._do_write(output, raw_data, parsed_data)
                continue

    def _do_write(self, output: object, raw: bytes, parsed: object):
        """
        THREADED
        Send RTCM3 data to designated output medium.

        If output is Queue, will send both raw and parsed data.

        :param object output: writeable output medium for RTCM3 data
        :param bytes raw: raw data
        :param object parsed: parsed message
        """

        self._do_log(parsed, VERBOSITY_MEDIUM)
        if output is not None:
            if isinstance(output, (Serial, BufferedWriter)):
                output.write(raw)
            elif isinstance(output, TextIOWrapper):
                output.write(str(parsed))
            elif isinstance(output, Queue):
                output.put((raw, parsed))
            elif isinstance(output, socket.socket):
                output.sendall(raw)

        # self._app_notify()  # notify any calling app that data is available
        if self.__app is not None:
            self.__app.set_event(NTRIP_EVENT)

    def _do_log(
        self,
        message: object,
        loglevel: int = VERBOSITY_MEDIUM,
        timestamp: bool = True,
    ):
        """
        THREADED
        Write timestamped log message according to verbosity and logfile settings.

        :param object message: message or object to log
        :param int loglevel: log level for this message (0,1,2)
        :param bool timestamp: prefix message with timestamp (Y/N)
        """

        if timestamp:
            message = f"{datetime.now()}: {str(message)}"
        else:
            message = str(message)

        if self._verbosity >= loglevel:
            if self._logtofile:
                self._cycle_log()
                with open(self._logfile, "a", encoding="UTF-8") as log:
                    log.write(message + "\n")
                    self._loglines += 1
            else:
                print(message)

    def _cycle_log(self):
        """
        THREADED
        Generate new timestamped logfile path.
        """

        if not self._loglines % LOGLIMIT:
            tim = datetime.now().strftime("%Y%m%d%H%M%S")
            self._logfile = os.path.join(self._logpath, f"gnssntripclient-{tim}.log")
            self._loglines = 0


def main():
    """
    CLI Entry point.

    :param int waittime: response wait time in seconds (3)
    :param: as per GNSSNTRIPClient constructor and run() method.
    :raises: ParameterError if parameters are invalid
    """
    # pylint: disable=raise-missing-from

    ap = ArgumentParser(
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument(
        "-I",
        "--ipprot",
        required=False,
        help="IP protocol",
        choices=["IPv4", "IPv6"],
        default="IPv4",
    )
    ap.add_argument(
        "-S", "--server", required=True, help="NTRIP server (caster) URL", default=""
    )
    ap.add_argument(
        "-P", "--port", required=False, help="NTRIP port", type=int, default=2101
    )
    ap.add_argument(
        "--flowinfo", required=False, help="Flow info for IPv6", type=int, default=0
    )
    ap.add_argument(
        "--scopeid", required=False, help="Scope ID for IPv6", type=int, default=0
    )
    ap.add_argument(
        "-M",
        "--mountpoint",
        required=False,
        help="NTRIP mountpoint (leave blank to get sourcetable)",
        default="",
    )
    ap.add_argument(
        "--ntripversion",
        required=False,
        dest="version",
        help="NTRIP protocol version",
        default="2.0",
    )
    ap.add_argument(
        "--waittime",
        required=False,
        help="Response wait time",
        type=int,
        default=3,
    )
    ap.add_argument(
        "--user",
        required=False,
        help="login user (or set env variable NTRIP_USER)",
        default="anon",
    )
    ap.add_argument(
        "--password",
        required=False,
        help="login password (or set env variable NTRIP_PASSWORD)",
        default="password",
    )
    ap.add_argument(
        "--ggainterval",
        required=False,
        help="GGA sentence transmission interval (-1 = None)",
        type=int,
        default=-1,
    )
    ap.add_argument(
        "--ggamode",
        required=False,
        help="GGA pos source; 0 = live from receiver, 1 = fixed reference",
        type=int,
        choices=[0, 1],
        default=0,
    )
    ap.add_argument(
        "--reflat", required=False, help="reference latitude", type=float, default=0.0
    )
    ap.add_argument(
        "--reflon", required=False, help="reference longitude", type=float, default=0.0
    )
    ap.add_argument(
        "--refalt", required=False, help="reference altitude", type=float, default=0.0
    )
    ap.add_argument(
        "--refsep", required=False, help="reference separation", type=float, default=0.0
    )
    ap.add_argument(
        "--verbosity",
        required=False,
        help="Log message verbosity 0 = low, 1 = medium, 2 = high, 3 = debug",
        type=int,
        choices=[0, 1, 2, 3],
        default=1,
    )
    ap.add_argument(
        "--logtofile",
        required=False,
        help="0 = log to stdout, 1 = log to file '/logpath/gnssntripclient-timestamp.log'",
        type=int,
        choices=[0, 1],
        default=0,
    )
    ap.add_argument(
        "--logpath",
        required=False,
        help="Fully qualified path to logfile folder",
        default=".",
    )

    args = ap.parse_args()
    kwargs = vars(args)

    try:
        with GNSSNTRIPClient(None, **kwargs) as gnc:
            streaming = gnc.run(**kwargs)

            while streaming:  # run until user presses CTRL-C
                sleep(args.waittime)
            sleep(args.waittime)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
