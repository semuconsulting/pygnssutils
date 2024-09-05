"""
gnssmqttclient.py

MQTT SPARTN client class, retrieving correction data from an IP (MQTT)
source and (optionally) sending the data to a designated writeable output
medium (serial, file, socket, queue).

Calling app, if defined, can implement the following methods:
 - set_event() - create <<spartn_read>> event
 - dialog() - return reference to MQTT client configuration dialog

Can utilise the following environment variables:
 - MQTTKEY - SPARTN payload decription key (valid for 4 weeks)
 - MQTTCRT - MQTT server (PointPerfect) TLS certificate
 - MQTTPEM - MQTT server (PointPerfect) TLS key
 - MQTTCLIENTID - MQTT server client ID

Credentials can be download from:
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
from logging import getLogger
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
    OUTPORT_SPARTN,
    SPARTN_EVENT,
    SPARTN_PPSERVER,
    TOPIC_ASSIST,
    TOPIC_DATA,
    TOPIC_FREQ,
    TOPIC_KEY,
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
        """

        self.__app = app  # Reference to calling application class (if applicable)
        # configure logger with name "pygnssutils" in calling module
        self.logger = getLogger(__name__)
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
            "tlscrt": getenv(
                "MQTTCRT",
                default=path.join(Path.home(), f"device-{clientid}-pp-cert.crt"),
            ),
            "tlskey": getenv(
                "MQTTPEM",
                default=path.join(Path.home(), f"device-{clientid}-pp-key.pem"),
            ),
            "spartndecode": 0,
            "spartnkey": getenv("MQTTKEY", default=None),
            "spartnbasedate": datetime.now(timezone.utc),
            "output": None,
        }

        self._timeout = kwargs.get("timeout", TIMEOUT)
        self.errevent = kwargs.get("errevent", Event())
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
            self._settings["server"] = kwargs.get("server", self._settings["server"])
            self._settings["port"] = int(kwargs.get("port", self._settings["port"]))
            self._settings["clientid"] = kwargs.get(
                "clientid", self._settings["clientid"]
            )
            self._settings["region"] = kwargs.get("region", self._settings["region"])
            self._settings["mode"] = int(kwargs.get("mode", self._settings["mode"]))
            self._settings["topic_ip"] = int(
                kwargs.get("topic_ip", self._settings["topic_ip"])
            )
            self._settings["topic_mga"] = int(
                kwargs.get("topic_mga", self._settings["topic_mga"])
            )
            self._settings["topic_key"] = int(
                kwargs.get("topic_key", self._settings["topic_key"])
            )
            self._settings["tlscrt"] = kwargs.get("tlscrt", self._settings["tlscrt"])
            self._settings["tlskey"] = kwargs.get("tlskey", self._settings["tlskey"])
            self._settings["spartndecode"] = int(
                kwargs.get("spartndecode", self._settings["spartndecode"])
            )
            self._settings["spartnkey"] = kwargs.get(
                "spartnkey", self._settings["spartnkey"]
            )
            self._settings["spartnbasedate"] = kwargs.get(
                "spartnbasedate", self._settings["spartnbasedate"]
            )
            self._settings["output"] = kwargs.get("output", self._settings["output"])

        except (ParameterError, ValueError, TypeError) as err:
            self.logger.critical(
                f"Invalid input arguments {kwargs}\n{err}\nType gnssntripclient -h for help."
            )
            self._validargs = False
            return 0

        self.logger.info(f"Starting MQTT client with arguments {self._settings}.")
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
        self.logger.info("MQTT Client Stopped.")

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
            "logger": self.logger,
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
                    self.logger.info(f"Trying to connect {i} ...")
                    sleep(timeout / 4)
                    i += 1

            client.loop_start()
            while not stopevent.is_set():
                # run the client loop in the same thread, as callback access gnss
                # client.loop(timeout=0.1)
                sleep(0.1)
        except (FileNotFoundError, TimeoutError) as err:
            self.logger.critical(f"ERROR! {err}")
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
        msglogger = userdata["logger"]

        def do_write(raw: bytes, parsed: object):
            """
            Send SPARTN data to designated output medium.

            If output is Queue, will send both raw and parsed data.

            :param dict userdata: user defined data dict
            :param bytes raw: raw data
            :param object parsed: parsed message
            """

            if hasattr(parsed, "identity"):
                msglogger.info(parsed.identity)
            msglogger.debug(parsed)

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
                    do_write(raw, parsed)
            except UBXParseError:
                parsed = f"MQTT UBXParseError {msg.topic} {msg.payload}"
                do_write(msg.payload, parsed)
        elif "frequencies" in msg.topic:  # frequency values
            parsed = MQTTMessage(msg.topic, msg.payload)
            do_write(msg.payload, parsed)
        else:  # SPARTN protocol message
            spr = SPARTNReader(
                BytesIO(msg.payload),
                decode=userdata["decode"],
                key=userdata["key"],
                basedate=userdata["basedate"],
            )
            try:
                for raw, parsed in spr:
                    do_write(raw, parsed)
            except (SPARTNMessageError, SPARTNParseError, SPARTNStreamError):
                parsed = f"MQTT SPARTNParseError {msg.topic} {msg.payload}"
                do_write(msg.payload, parsed)

    @staticmethod
    def on_error(userdata: dict, err: object):
        """
        Report return code back to any calling application.

        :param dict userdata: user defined data dict
        :param object rcd: return code (int or str)
        """

        errlogger = userdata["logger"]

        if isinstance(err, int):
            err = mqtt.error_string(err)
        app = userdata["app"]
        if app is None:
            errlogger.error(err)
        else:
            if hasattr(app, "dialog"):
                dlg = app.dialog(DLGTSPARTN)
                if dlg is not None:
                    if hasattr(dlg, "disconnect_ip"):
                        dlg.disconnect_ip(f"{err} ")
