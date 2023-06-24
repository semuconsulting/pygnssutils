"""
pygnssutils - rgnssmqttclient_example.py

Illustration of GNSSMQTTClient class.

Reads selected topics from MQTT server and outputs raw data to log file.

Expects user's Client ID to be set up in environment variable MQTTCLIENTID.
Expects user's *.crt and *.pem files to be placed in user's home directory.

Created on 5 Jun 2023

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

from time import sleep
from threading import Event
from os import getenv, path
from pathlib import Path
from pygnssutils import GNSSMQTTClient, SPARTN_PPSERVER, OUTPORT_SPARTN

clientid = getenv("MQTTCLIENTID")  # or hard code here

try:
    with open("spartn_ip.log", "wb") as outfile:
        kwargs = {
            "server": SPARTN_PPSERVER,  # Thingstream MQTT server
            "port": OUTPORT_SPARTN,  # 8883
            "clientid": clientid,
            "region": "eu",
            "tlscrt": path.join(Path.home(), f"device-{clientid}-pp-cert.crt"),
            "tlskey": path.join(Path.home(), f"device-{clientid}-pp-key.pem"),
            "topic_ip": 1,  # SPARTN correction data (SPARTN OCB, HPAC & GAD messages)
            "topic_mga": 0,  # Assist Now ephemera data (UBX MGA-EPH-* messages)
            "topic_key": 0,  # SPARTN decryption keys (UBX RXM_SPARTNKEY messages)
            "output": outfile,
            "errevent": Event(),
        }
        with GNSSMQTTClient(None, **kwargs) as gsc:
            streaming = gsc.start(**kwargs)
            while (
                streaming and not kwargs["errevent"].is_set()
            ):  # run until error or user presses CTRL-C
                sleep(3)
            sleep(3)

except (KeyboardInterrupt, TimeoutError):
    gsc.stop()
