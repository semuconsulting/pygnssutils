"""
gnssmqttclient.py

MQTT SPARTN client class, retrieving correction data from an IP (MQTT)
source and (optionally) sending the data to a designated writeable output
medium (serial, file, socket, queue).

Calling app, if defined, can implement the following methods:
- set_event() - create <<spartn_read>> event
- dialog() - return reference to MQTT client configuration dialog

Thingstream > Location Services > PointPerfect Thing > Credentials
Default location for key files is user's HOME directory

Created on 20 Feb 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

# pylint: disable=invalid-name

import socket
from datetime import datetime, timezone
from io import BufferedWriter, BytesIO, TextIOWrapper
from os import getenv, path
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from time import sleep

import paho.mqtt.client as mqtt
from paho.mqtt import __version__ as PAHO_MQTT_VERSION
from pyspartn import (
    SPARTNMessageError,
    SPARTNParseError,
    SPARTNReader,
    SPARTNStreamError,
)
from pyubx2 import SET, UBXParseError, UBXReader
from serial import Serial

from pygnssutils.exceptions import ParameterError
from pygnssutils.globals import (
    CLIAPP,
    LOGLIMIT,
    OUTPORT_SPARTN,
    SPARTN_EVENT,
    SPARTN_PPSERVER,
    TOPIC_ASSIST,
    TOPIC_DATA,
    TOPIC_FREQ,
    TOPIC_KEY,
    VERBOSITY_LOW,
    VERBOSITY_MEDIUM,
)
from pygnssutils.mqttmessage import MQTTMessage

TIMEOUT = 8
DLGTSPARTN = "SPARTN Configuration"


class GNSSMQTTClient:
    """
    SPARTN MQTT client class.
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
        clientid = getenv("MQTTCLIENTID", default="enter-client-id")

        self._settings = {
            "server": SPARTN_PPSERVER,
            "port": OUTPORT_SPARTN,
            "clientid": clientid,
            "region": "eu",
            "mode": 0,
            "topic_ip": 1,
            "topic_mga": 1,
            "topic_key": 1,
            "tlscrt": path.join(Path.home(), f"device-{clientid}-pp-cert.crt"),
            "tlskey": path.join(Path.home(), f"device-{clientid}-pp-key.pem"),
            "spartndecode": 0,
            "spartnkey": getenv("MQTTKEY", default=None),
            "spartnbasedate": datetime.now(timezone.utc),
            "output": None,
        }

        self._timeout = kwargs.get("timeout", TIMEOUT)
        self.errevent = kwargs.get("errevent", Event())
        self._verbosity = int(kwargs.get("verbosity", VERBOSITY_MEDIUM))
        self._logtofile = int(kwargs.get("logtofile", 0))
        self._logpath = kwargs.get("logpath", ".")
        self._loglines = 0
        self._socket = None
        self._connected = False
        self._stopevent = Event()
        self._mqtt_thread = None
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
        Getter for SPARTN IP settings.
        """

        return self._settings

    @settings.setter
    def settings(self, settings: dict):
        """
        Setter for SPARTN IP settings.

        :param dict settings: SPARTN IP settings dictionary
        """

        self._settings = settings

    @property
    def connected(self):
        """
        Connection status getter.
        """

        return self._connected

    def start(self, **kwargs) -> int:
        """
        Start MQTT handler thread.

        :return: return code
        :rtype: int
        """

        try:
            for kwarg in [
                "server",
                "port",
                "clientid",
                "region",
                "mode",
                "topic_ip",
                "topic_mga",
                "topic_key",
                "tlscrt",
                "tlskey",
                "spartndecode",
                "spartnkey",
                "spartnbasedate",
                "output",
            ]:
                if kwarg in kwargs:
                    self._settings[kwarg] = kwargs.get(kwarg)
            self._verbosity = int(kwargs.get("verbosity", self._verbosity))
            self._logtofile = int(kwargs.get("logtofile", self._logtofile))
            self._logpath = kwargs.get("logpath", self._logpath)

        except (ParameterError, ValueError, TypeError) as err:
            self._do_log(
                f"Invalid input arguments {kwargs}\n{err}\nType gnssntripclient -h for help.",
                VERBOSITY_LOW,
            )
            self._validargs = False
            return 0

        self._do_log(
            f"Starting MQTT client with arguments {self._settings}.",
            VERBOSITY_MEDIUM,
        )
        self._stopevent.clear()
        self._mqtt_thread = Thread(
            target=self._run,
            args=(
                self.__app,
                self._settings,
                self._timeout,
                self._stopevent,
            ),
            daemon=True,
        )
        self._mqtt_thread.start()
        return 1

    def stop(self):
        """
        Stop MQTT handler thread.
        """

        self._stopevent.set()
        self._mqtt_thread = None
        self._do_log(
            "MQTT Client Stopped.",
            VERBOSITY_MEDIUM,
        )

    def _run(
        self,
        app: object,
        settings: dict,
        timeout: int,
        stopevent: Event,
    ):
        """
        THREADED Run MQTT client thread.

        :param object app: calling application
        :param dict settings: dict of settings
        :param int timeout: connection timeout in seconds
        :param event stopevent: stop event
        """

        # these pylint exclusions are necessary to accommodate old and new versions
        # of the paho.mqtt api...
        # pylint: disable=redundant-keyword-arg, no-member, no-value-for-parameter

        topics = []
        mode = "Lb" if settings.get("mode", 0) else "ip"
        if settings["topic_ip"]:
            topics.append((TOPIC_DATA.format(mode, settings["region"]), 0))
        if settings["topic_mga"]:
            topics.append((TOPIC_ASSIST, 0))
        if settings["topic_key"]:
            topics.append((TOPIC_KEY.format(mode), 0))
        if mode == "Lb":
            topics.append((TOPIC_FREQ, 0))
        userdata = {
            "output": settings["output"],
            "topics": topics,
            "app": app,
            "decode": settings["spartndecode"],
            "key": settings["spartnkey"],
            "basedate": settings["spartnbasedate"],
            "verbosity": self._verbosity,
        }

        try:
            if PAHO_MQTT_VERSION < "2.0.0":
                client = mqtt.Client(
                    client_id=settings["clientid"],
                    userdata=userdata,
                )
            else:
                client = mqtt.Client(
                    mqtt.CallbackAPIVersion.VERSION1,
                    client_id=settings["clientid"],
                    userdata=userdata,
                )
            client.on_connect = self.on_connect
            client.on_disconnect = self.on_disconnect
            client.on_message = self.on_message
            client.tls_set(certfile=settings["tlscrt"], keyfile=settings["tlskey"])
            i = 1
            while not stopevent.is_set():
                try:
                    client.connect(settings["server"], port=settings["port"])
                    break
                except Exception as err:  # pylint: disable=broad-exception-caught
                    if i > 4:
                        raise TimeoutError(
                            f"Unable to connect to {settings['server']}"
                            + f":{settings['port']} in {timeout} seconds. {err}"
                        ) from err
                    self._do_log(f"Trying to connect {i} ...", VERBOSITY_MEDIUM)
                    sleep(timeout / 4)
                    i += 1

            client.loop_start()
            while not stopevent.is_set():
                # run the client loop in the same thread, as callback access gnss
                # client.loop(timeout=0.1)
                sleep(0.1)
        except (FileNotFoundError, TimeoutError) as err:
            self._do_log(f"ERROR! {err}", VERBOSITY_MEDIUM)
            GNSSMQTTClient.on_error(userdata, err)
            self.stop()
            self.errevent.set()

        finally:
            client.loop_stop()

    @staticmethod
    def on_connect(client, userdata, flags, rcd):  # pylint: disable=unused-argument
        """
        The callback for when the client receives a CONNACK response from the server.

        :param object client: client
        :param list userdata:  list of user defined data items
        :param list flags: optional flags
        :param int rcd: return status code
        """

        if rcd == 0:
            client.subscribe(userdata["topics"])
        else:
            GNSSMQTTClient.on_error(userdata, rcd)

    @staticmethod
    def on_connect_fail(client, userdata, rcd):  # pylint: disable=unused-argument
        """
        The callback for when the client fails to connect to the server.

        :param object client: client
        :param list userdata:  list of user defined data items
        :param int rcd: return status code
        """

        GNSSMQTTClient.on_error(userdata, rcd)

    @staticmethod
    def on_disconnect(client, userdata, rcd):  # pylint: disable=unused-argument
        """
        The callback for when the client disconnects from the server.

        :param object client: client
        :param list userdata:  list of user defined data items
        :param int rcd: return status code
        """

        GNSSMQTTClient.on_error(userdata, rcd)

    @staticmethod
    def on_message(client, userdata, msg):  # pylint: disable=unused-argument
        """
        The callback for when a PUBLISH message is received from the server.
        Some MQTT topics may contain more than one UBX or SPARTN message in
        a single payload.

        :param object client: MQTT client
        :param list userdata: list of user defined data items
        :param object msg: SPARTN or UBX message topic content
        """

        output = userdata["output"]
        app = userdata["app"]
        verbosity = userdata["verbosity"]

        def do_log(message: object, loglevel: int):
            """
            Write timestamped log message according to verbosity settings.

            :param object message: message or object to log
            :param int loglevel: log level for this message (0,1,2)
            """

            if verbosity >= loglevel:
                print(f"{datetime.now()}: {message}")

        def do_write(userdata: dict, raw: bytes, parsed: object):
            """
            Send SPARTN data to designated output medium.

            If output is Queue, will send both raw and parsed data.

            :param dict userdata: user defined data dict
            :param bytes raw: raw data
            :param object parsed: parsed message
            """

            do_log(
                parsed if verbosity > VERBOSITY_MEDIUM else parsed.identity,
                VERBOSITY_MEDIUM,
            )

            if output is not None:
                if isinstance(output, (Serial, BufferedWriter)):
                    output.write(raw)
                elif isinstance(output, TextIOWrapper):
                    output.write(str(parsed))
                elif isinstance(output, Queue):
                    output.put(raw if app == CLIAPP else (raw, parsed))
                elif isinstance(output, socket.socket):
                    output.sendall(raw)

            if app is not None:
                if hasattr(app, "set_event"):
                    app.set_event(SPARTN_EVENT)

        if "ubx" in msg.topic:  # UBX MGA-* or RXM-SPARTNKEY messages
            ubr = UBXReader(BytesIO(msg.payload), msgmode=SET)
            try:
                for raw, parsed in ubr:
                    do_write(userdata, raw, parsed)
            except UBXParseError:
                parsed = f"MQTT UBXParseError {msg.topic} {msg.payload}"
                do_write(userdata, msg.payload, parsed)
        elif "frequencies" in msg.topic:  # frequency values
            parsed = MQTTMessage(msg.topic, msg.payload)
            do_write(userdata, msg.payload, parsed)
        else:  # SPARTN protocol message
            spr = SPARTNReader(
                BytesIO(msg.payload),
                decode=userdata["decode"],
                key=userdata["key"],
                basedate=userdata["basedate"],
            )
            try:
                for raw, parsed in spr:
                    do_write(userdata, raw, parsed)
            except (SPARTNMessageError, SPARTNParseError, SPARTNStreamError):
                parsed = f"MQTT SPARTNParseError {msg.topic} {msg.payload}"
                do_write(userdata, msg.payload, parsed)

    @staticmethod
    def on_error(userdata: dict, err: object):
        """
        Report return code back to any calling application.

        :param dict userdata: user defined data dict
        :param object rcd: return code (int or str)
        """

        if isinstance(err, int):
            err = mqtt.error_string(err)
        app = userdata["app"]
        if app is None:
            print(err)
        else:
            if hasattr(app, "dialog"):
                dlg = app.dialog(DLGTSPARTN)
                if dlg is not None:
                    if hasattr(dlg, "disconnect_ip"):
                        dlg.disconnect_ip(f"{err} ")

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
            self._logfile = path.join(self._logpath, f"gnssspartnclient-{tim}.log")
            self._loglines = 0
