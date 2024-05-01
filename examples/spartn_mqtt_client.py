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

python3 spartn_mqtt_client.py clientid="abcd1234-abcd-efgh-4321-1234567890ab" region="eu" decode=1 key="abcdef1234567890abcdef1234567890" outfile="spartnmqtt.log"

Run from /examples folder.

Created on 12 Feb 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

from datetime import datetime, timezone
from os import path, getenv
from pathlib import Path
from sys import argv
from time import sleep

from pygnssutils import GNSSMQTTClient


SERVER = "pp.services.u-blox.com"
PORT = 8883


def main(**kwargs):
    """
    Main routine.
    """

    clientid = kwargs.get("clientid", getenv("MQTTCLIENTID", ""))
    region = kwargs.get("region", "eu")
    decode = int(kwargs.get("decode", 0))
    key = kwargs.get("key", getenv("MQTTKEY", None))
    outfile = kwargs.get("outfile", "spartnmqtt.log")

    with open(outfile, "wb") as out:
        gmc = GNSSMQTTClient()

        print(f"SPARTN MQTT Client started, writing output to {outfile}...")
        gmc.start(
            server=SERVER,
            port=PORT,
            clientid=clientid,
            tlscrt=path.join(Path.home(), f"device-{clientid}-pp-cert.crt"),
            tlskey=path.join(Path.home(), f"device-{clientid}-pp-key.pem"),
            region=region,
            mode=0,
            topic_ip=1,
            topic_mga=0,
            topic_key=0,
            spartndecode=decode,
            spartnkey=key,
            spartnbasedate=datetime.now(timezone.utc),
            output=None,
        )

        try:
            while True:
                sleep(3)
        except KeyboardInterrupt:
            print("SPARTN MQTT Client terminated by User")
            print(
                f"To decrypt the contents of the output file {outfile} using pyspartn,",
                f"use kwargs: decode=True, key=key_supplied_by_service_provider, basedate={repr(datetime.now(timezone.utc))}",
            )


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
