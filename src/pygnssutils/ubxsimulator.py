"""
ubxsimulator.py

*** EXPERIMENTAL ***

Simple UBX GNSS serial device simulator.

Simulates a GNSS serial stream by generating synthetic UBX or NMEA messages
based on parameters defined in a json configuration file. Can simulate a
motion vector based on a specified course over ground and speed.

Example usage:

    from pygnssutils import UBXSimulator
    from pyubx2 import UBXReader

    with UBXSimulator(configfile="/home/myuser/ubxsimulator.json", interval=1, timeout=3) as stream:
        ubr = UBXReader(stream)
        for raw, parsed in ubr:
            print(parsed)

Generates mock acknowledgements (ACK-ACK) for valid incoming UBX commands
and polls.

See sample ubxsimulator.json configuration file in the \\\\examples folder.

NB: Principally intended for testing Python GNSS application functionality.
There is currently no attempt to simulate real-world satellite geodetics,
though this could be done using e.g. the Python `skyfield` library and the 
relevant satellite TLE (orbital elements) files. I may look into adding
such functionality as and when time permits. Contributions welcome.

Created on 3 Feb 2024

:author: semuadmin
:copyright: SEMU Consulting © 2024
:license: BSD 3-Clause
"""

# pylint: disable=too-many-locals, too-many-instance-attributes

from datetime import datetime, timedelta
from json import JSONDecodeError, load
from logging import getLogger
from math import cos, pi, sin
from os import getenv, path
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from time import sleep

from pynmeagps import NMEAMessage
from pyrtcm import RTCMMessage, RTCMMessageError, RTCMParseError, RTCMReader
from pyubx2 import (
    GET,
    RTCM3_PROTOCOL,
    UBX_PROTOCOL,
    UBXMessage,
    UBXMessageError,
    UBXParseError,
    UBXReader,
    escapeall,
    getinputmode,
    protocol,
    utc2itow,
)

from pygnssutils.globals import EARTH_RADIUS, UBXSIMULATOR

DEFAULT_INTERVAL = 1000  # milliseconds
DEFAULT_TIMEOUT = 3  # seconds
DEFAULT_PATH = path.join(Path.home(), "ubxsimulator")


class UBXSimulator:
    """
    Simple dummy GNSS UBX serial stream class.
    """

    def __init__(self, app=None, **kwargs):
        """
        Constructor.

        :param float interval: (kwarg) simulated navigation interval in seconds
        :param float timeout: (kwarg) simulated serial read timeout in seconds
        :param str configfile: (kwarg) fully qualified path to json config file
        """

        # Reference to calling application class (if applicable)
        self.__app = app  # pylint: disable=unused-private-member
        # configure logger with name "pygnssutils" in calling module
        self.logger = getLogger(__name__)
        self._config = self._readconfig(
            kwargs.get(
                "configfile",
                getenv(f"{UBXSIMULATOR.upper()}_JSON", DEFAULT_PATH + ".json"),
            )
        )
        self.logger.debug(f"Configuration loaded:\n{self._config}")
        self._interval = kwargs.get(
            "interval", (self._config.get("interval", DEFAULT_INTERVAL))
        )  # milliseconds
        self._timeout = kwargs.get(
            "timeout", (self._config.get("timeout", self._interval * 3))
        )
        self._stopevent = Event()
        self._outqueue = Queue()
        self._inqueue = Queue()
        self._buffer = b""
        self._mainloop_thread = None
        self._msgfactory_thread = None
        self._lastread = datetime.fromordinal(1)
        self._loops = 0

    def _readconfig(self, cfile: str) -> dict:
        """
        Get configuration from json file.

        :param str cfile: fully qualified path to config file
        :return: config as dict
        :rtype: dict
        """

        try:
            with open(cfile, "r", encoding="utf-8") as jsonfile:
                config = load(jsonfile)
        except (OSError, JSONDecodeError) as err:
            self.logger.error(f"Unable to read configuration file:\n{err}")
            return {
                "interval": DEFAULT_INTERVAL,
                "timeout": DEFAULT_TIMEOUT,
                "logfile": DEFAULT_PATH + ".log",
            }

        return config

    def __enter__(self):
        """
        Context manager enter routine.
        """

        self.start()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Context manager exit routine.
        """

        self.stop()

    def start(self):
        """
        Start streaming.
        """

        self.logger.info("UBX Simulator started")
        self._stopevent.clear()
        self._msgfactory_thread = Thread(
            target=self._msgfactory,
            args=(
                self._loops,
                self._config,
                self._stopevent,
                self._outqueue,
            ),
        )
        self._msgfactory_thread.start()
        sleep(self._interval / 1000)
        self._mainloop_thread = Thread(
            target=self._mainloop,
            args=(
                self._stopevent,
                self._outqueue,
                self._inqueue,
            ),
        )
        self._mainloop_thread.start()

    def stop(self):
        """
        Stop streaming.
        """

        self._stopevent.set()
        if self._mainloop_thread is not None:
            self._mainloop_thread.join()
        if self._msgfactory_thread is not None:
            self._msgfactory_thread.join()
        self.logger.info("UBX Simulator stopped")

    def _mainloop(self, stop: Event, outq: Queue, inq: Queue):
        """
        THREADED Main Loop.

        :param Event stop: stop event
        :param Queue outq: output queue
        :param Queue inq: input queue
        """

        while not stop.is_set():
            while not outq.empty():
                self._buffer += outq.get()
                outq.task_done()
            while not inq.empty():
                data = inq.get()
                self._datahandler(data, outq)
                inq.task_done()
            sleep(self._interval / 10000)

    def _msgfactory(
        self,
        loops: int,
        config: dict,
        stop: Event,
        outq: Queue,
    ) -> bytes:
        """
        THREADED message factory.

        Generate synthetic UBX or NMEA navigation messages using navigation
        interval and attribute values specified in configuration file.

        TODO allow dynamic attribute derivation for UBX messages.

        :param int loops: message loop counter
        :param dict config: configuration dictionary
        :param Event stop: stop event
        :param Queue outq: output queue
        """

        while not stop.is_set():

            nw = datetime.now()
            _, itow = utc2itow(nw)

            # time and global position attributes are applied to all msg types
            time_attrs = {
                "iTOW": itow,
                "year": nw.year,
                "month": nw.month,
                "day": nw.day,
                "hour": nw.hour,
                "min": nw.minute,
                "second": nw.second,
            }
            global_attrs = config.get("global", {})

            # simulate motion vector using course over ground and speed
            # NB: UBX NAV-PVT outputs speed as mm/s; NMEA RMC uses knots
            if config.get("simVector", False):
                lat1 = global_attrs.get("lat", 0)
                lon1 = global_attrs.get("lon", 0)
                spd = global_attrs.get("spd", 0) * 0.5144444  # knots -> m/s
                spd = global_attrs.get("gSpeed", spd * 1000) / 1000  # mm/s -> m/s
                cog = global_attrs.get("headMot", global_attrs.get("cog", 0))
                lat2, lon2 = self._add_vector(lat1, lon1, spd, cog, self._interval)
                global_attrs["lat"] = lat2
                global_attrs["lon"] = lon2

            ubxm = config.get("ubxmessages", [])
            for msg in ubxm:
                msgcls = msg["msgCls"]
                msgid = msg["msgId"]
                rate = msg.get("rate", 1)
                if not loops % rate:
                    attrs = {**time_attrs, **global_attrs, **msg["attrs"]}
                    ubx = UBXMessage(msgcls, msgid, GET, **attrs)
                    outq.put(ubx.serialize())

            nmeam = config.get("nmeamessages", [])
            for msg in nmeam:
                talker = msg["talker"]
                msgid = msg["msgId"]
                rate = msg.get("rate", 1)
                if not loops % rate:
                    # pynmeagps automatically defaults time to now()
                    attrs = {**global_attrs, **msg["attrs"]}
                    nme = NMEAMessage(talker, msgid, GET, **attrs)
                    outq.put(nme.serialize())

            sleep(self._interval / 1000)
            loops = (loops + 1) % 1024

    def _datahandler(self, data: bytes, outq: Queue):
        """
        THREADED
        Process incoming UBX or RTCM3 data.

        TODO enhance to mimic wider range of command or poll responses.

        :param bytes data: UBXMessage or RTCMMessage
        :param Queue outq: output queue
        """

        if data is None:
            return

        if isinstance(data, UBXMessage):
            self._do_ackack(data, outq)

            if data.identity == "MON-VER":
                self._do_monver(outq)
            if data.identity == "CFG-RATE":
                self._do_cfgrate(data, outq)

    def _do_send(self, msg: UBXMessage, outq: Queue):
        """
        Send synthetic command or query response.

        :param UBXMessage msg: UBXMessage
        :param Queue outq: output queue
        """

        raw = msg.serialize()
        outq.put(raw)
        self.logger.info(f"Response Sent by Simulator:\n{raw}\n{msg}")

    def _do_ackack(self, data: UBXMessage, outq: Queue):
        """
        Generate synthetic ACK ACK acknowledgement.

        :param UBXMessage msg: incoming UBXMessage
        :param Queue outq: output queue
        """

        msg = UBXMessage(
            "ACK",
            "ACK-ACK",
            GET,
            clsID=int.from_bytes(data.msg_cls, "little"),
            msgID=int.from_bytes(data.msg_id, "little"),
        )
        self._do_send(msg, outq)

    def _do_monver(self, outq: Queue):
        """
        Generate synthetic MON-VER poll response.

        :param Queue outq: output queue
        """

        parms = {
            "swVersion": b"ROM_CORE UBXSIM" + b"\x00" * 15,
            "hwVersion": b"UBXSIM" + b"\x00" * 4,
        }
        msg = UBXMessage("MON", "MON-VER", GET, **parms)
        self._do_send(msg, outq)

    def _do_cfgrate(self, data: UBXMessage, outq: Queue):
        """
        Update nav interval in response to CFG_RATE command.

        :param Queue outq: output queue
        """

        if hasattr(data, "measRate"):  # SET
            self._interval = data.measRate
        else:  # POLL
            parms = {
                "measRate": int(self._interval),
                "navRate": 1,
                "timeRef": 0,
            }
            msg = UBXMessage("CFG", "CFG-RATE", GET, **parms)
            self._do_send(msg, outq)

    def _add_vector(
        self,
        lat: float,
        lon: float,
        speed: float,
        course: float,
        interval: float = 1000,
        radius: float = EARTH_RADIUS,
    ) -> tuple:
        """
        Add vector to given lat/lon position.

        :param float lat: starting latitude
        :param float lon: starting longitude
        :param float speed: speed in m/s
        :param float course: course over ground in degrees
        :param float interval: navigation interval in milliseconds (1)
        :param float radius: earth radius in km (6371)
        :return: ending lat/lon
        :rtype: tuple
        """

        # convert speed to km/s
        course *= pi / 180
        dn = speed / 1000 * cos(course) * interval / 1000
        de = speed / 1000 * sin(course) * interval / 1000
        dlat = dn / radius
        dlon = de / (radius * cos(lat * pi / 180))
        lat2 = lat + dlat * 180 / pi
        lon2 = lon + dlon * 180 / pi
        return lat2, lon2

    def read(self, num: int = 1) -> bytes:
        """
        Read n bytes from buffer.

        :param int val: num of bytes to read (1)
        :return: bytes
        :raises: TimeoutError
        """

        while len(self._buffer) < num:
            sleep(self._interval / 20000)
            if datetime.now() > self._lastread + timedelta(seconds=self._timeout):
                raise TimeoutError
        data = self._buffer[0:num]
        self._buffer = self._buffer[num:]
        self._lastread = datetime.now()
        return data

    def readline(self) -> bytes:
        """
        Read line from buffer.

        :return: bytes
        """

        b = data = b""
        while b != b"\x0a":  # LF
            b = self.read()
            if b == b"":
                break
            data += b
        return data

    def write(self, data: bytes):
        """
        Simulated write to receiver.

        :param bytes data: UBX data
        """

        prot = protocol(data)
        try:
            if prot == RTCM3_PROTOCOL:
                rtm = RTCMReader.parse(data)
                self._inqueue.put(rtm)
                val = ("RTCM", rtm)
            elif prot == UBX_PROTOCOL:
                msgmode = getinputmode(data)  # returns SET or POLL
                ubx = UBXReader.parse(data, msgmode=msgmode)
                self._inqueue.put(ubx)
                val = ("UBX", ubx)
            else:
                val = (f"Other Protocol {prot}", None)
        except (
            UBXParseError,
            UBXMessageError,
            RTCMParseError,
            RTCMMessageError,
        ) as err:
            val = ("Invalid/Unknown Data:", f"{err}")
        self.logger.debug(
            f"{val[0]} Data Received by Simulator:\n{escapeall(data)}\n{val[1]}"
        )

    def close(self):
        """
        Close dummy serial stream.
        """

        self.stop()

    @property
    def is_open(self) -> bool:
        """
        Return status.

        :return: true or false
        :rtype: bool
        """

        return self._mainloop_thread is not None

    @property
    def in_waiting(self) -> int:
        """
        Return number of bytes in buffer.

        :return: buffer length
        :rtype: int
        """

        return len(self._buffer)
