"""
spartn_mqtt_client.py

Illustration of SPARTN MQTT Client using GNSSMQTTClient
class from pygnssutils library. Can be used with the 
u-blox Thingstream PointPerfect MQTT service.

The contents of the output file can be decoded using the
spartn_decrypt.py example.

NB: requires a valid ClientID and TLS cert (*.crt) and key (*.pem)
files - these can be downloaded from your Thingstream account.
ClientID can be set using environment variable MQTTCLIENTID or
passed as the keyword argument clientid. The cert and key files
should be stored in the user's home directory.

Usage:

python3 spartn_mqtt_client.py clientid="abcd1234-abcd-efgh-4321-1234567890ab" outfile="spartnmqtt.log"

Run from /examples folder.

Created on 12 Feb 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

from datetime import datetime, UTC
from os import path, getenv
from pathlib import Path
from sys import argv
from time import sleep

from pygnssutils import GNSSMQTTClient


SERVER = "pp.services.u-blox.com"
PORT = 8883
REGION = "eu"  # amend to your region
DECODE = 0


def main(**kwargs):
    """
    Main routine.
    """

    clientid = kwargs.get("clientid", getenv("MQTTCLIENTID", ""))
    outfile = kwargs.get("outfile", "spartnmqtt.log")

    with open(outfile, "wb") as out:
        gmc = GNSSMQTTClient()

        print(
            f"SPARTN MQTT Client started, writing output to {outfile}... Press CTRL-C to terminate."
        )
        gmc.start(
            server=SERVER,
            port=PORT,
            clientid=clientid,
            tlscrt=path.join(Path.home(), f"device-{clientid}-pp-cert.crt"),
            tlskey=path.join(Path.home(), f"device-{clientid}-pp-key.pem"),
            region=REGION,
            mode=0,
            topic_ip=1,  # SPARTN data
            topic_mga=0,  # UBX MGA data
            topic_key=0,  # UBX RXM-SPARTNKEY data
            decode=DECODE,
            decryptkey=getenv("MQTTKEY", default=None),
            decryptbasedate=datetime.now(UTC),
            output=out,
        )

        try:
            while True:
                sleep(3)
        except KeyboardInterrupt:
            print("SPARTN MQTT Client terminated by User")
            print(
                f"To decrypt the contents of the output file {outfile} using pyspartn,",
                f"use kwargs: decode=True, key=key_supplied_by_service_provider, basedate={repr(datetime.now(UTC))}",
            )


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
