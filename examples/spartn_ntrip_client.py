"""
spartn_ntrip_client.py

Illustration of SPARTN NTRIP Client using GNSSNTRIPClient
class from pygnssutils library. Can be used with the 
u-blox Thingstream PointPerfect NTRIP service.

The contents of the output file can be decoded using the
spartn_decrypt.py example.

NB: requires a valid userid and password. These can be set as
environment variables PYGPSCLIENT_USER and PYGPSCLIENT_PASSWORD,
or passed as keyword arguments user and password.

At time of writing the PointPerfect NTRIP service is unencrypted
(eaf=0), so no key or basedate is required to decode the messages.

Usage:

python3 spartn_ntrip_client.py user="youruser" password="yourpassword" mountpoint="EU" outfile="spartnntrip.log" 

Run from /examples folder.

Created on 12 Feb 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

from os import path, getenv
from sys import argv
from time import sleep
from datetime import datetime, timezone

from pygnssutils import GNSSNTRIPClient

SERVER = "ppntrip.services.u-blox.com"
PORT = 2102
HTTPS = 1


def main(**kwargs):
    """
    Main routine.
    """

    user = kwargs.get("user", getenv("PYGPSCLIENT_USER", "user"))
    password = kwargs.get("password", getenv("PYGPSCLIENT_PASSWORD", "password"))
    decode = int(kwargs.get("decode", 0))
    key = kwargs.get("key", getenv("MQTTKEY", None))
    mountpoint = kwargs.get("mountpoint", "EU")
    outfile = kwargs.get("outfile", "spartnntrip.log")

    with open(outfile, "wb") as out:
        gnc = GNSSNTRIPClient()

        print(
            f"SPARTN NTRIP Client started, writing output to {outfile}... Press CTRL-C to terminate."
        )
        gnc.run(
            server=SERVER,
            port=PORT,
            https=HTTPS,
            mountpoint=mountpoint,
            datatype="SPARTN",
            ntripuser=user,
            ntrippassword=password,
            ggainterval=-1,
            spartndecode=decode,
            spartnkey=key,
            spartnbasedate=datetime.now(timezone.utc),
            output=out,
        )

        try:
            while True:
                sleep(3)
        except KeyboardInterrupt:
            print("SPARTN NTRIP Client terminated by User")


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
