"""
pygnssutils - rgnssmqttclient_example.py

Illustration of GNSSMQTTClient class.

Reads selected topics from MQTT server and outputs data to terminal or log file.

- ClientID can be provided as keyword argument or set in environment variable MQTTCLIENTID.
- SPARTN decryption key can be provided as keyword argument or set in environment variable MQTTKEY.
- Expects user's *.crt and *.pem files to be placed in user's home directory.

Usage:

   python3 gnssmqttclient_example.py clientid="your-client-id" outfile="spartn_ip.log" decode=1 decryptkey=yourkey decryptbasedate=yourbasedate

Created on 5 Jun 2023

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

from datetime import datetime
from os import getenv, path
from pathlib import Path
from sys import argv
from threading import Event
from time import sleep

from pygnssutils import OUTPORT_SPARTN, SPARTN_PPSERVER, GNSSMQTTClient


def main(**kwargs):
    """
    Main routine.
    """

    clientid = kwargs.get("clientid", getenv("MQTTCLIENTID", default="enter-client-id"))
    outfile = kwargs.get("outfile", None)
    decode = kwargs.get("decode", 0)
    decryptkey = kwargs.get("decryptkey", getenv("MQTTKEY", default=None))
    decryptbasedate = kwargs.get("decryptbasedate", datetime.now())
    stream = None

    if outfile is not None:
        stream = open(outfile, "wb")

    try:
        settings = {
            "server": SPARTN_PPSERVER,  # Thingstream MQTT server
            "port": OUTPORT_SPARTN,  # 8883
            "clientid": clientid,
            "region": "eu",
            "tlscrt": path.join(Path.home(), f"device-{clientid}-pp-cert.crt"),
            "tlskey": path.join(Path.home(), f"device-{clientid}-pp-key.pem"),
            "topic_ip": 1,  # SPARTN correction data (SPARTN OCB, HPAC & GAD messages)
            "topic_mga": 0,  # Assist Now ephemera data (UBX MGA-EPH-* messages)
            "topic_key": 0,  # SPARTN decryption keys (UBX RXM_SPARTNKEY messages)
            "decode": decode,
            "decryptkey": decryptkey,
            "decryptbasedate": decryptbasedate,
            "output": stream,
            "errevent": Event(),
        }
        with GNSSMQTTClient(None, **settings) as gsc:
            streaming = gsc.start(**settings)
            while (
                streaming and not settings["errevent"].is_set()
            ):  # run until error or user presses CTRL-C
                sleep(3)
            sleep(3)

    except (KeyboardInterrupt, TimeoutError):
        gsc.stop()
    finally:
        if outfile is not None:
            stream.close()


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
