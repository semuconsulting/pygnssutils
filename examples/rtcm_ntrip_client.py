"""
rtcm_ntrip_client.py

Illustration of RTCM3 NTRIP Client using GNSSNTRIPClient
class from pygnssutils library. Can be used with any 
NTRIP caster.

NB: requires a valid userid and password. These can be set as
environment variables PYGPSCLIENT_USER and PYGPSCLIENT_PASSWORD,
or passed as keyword arguments user and password.

Usage:

python3 rtcm_ntrip_client.py server="yourcaster" port=2101 mountpoint="yourmountpoint" user="youruser" password="yourpassword" outfile="rtcmntrip.log"

Run from /examples folder.

Created on 12 Feb 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

from logging import getLogger
from os import getenv
from sys import argv
from time import sleep

from pygnssutils import VERBOSITY_HIGH, GNSSNTRIPClient, set_logging

DEFAULT_PORT = 2101


def main(**kwargs):
    """
    Main routine.
    """

    logger = getLogger("pygnssutils.gnssntripclient")
    set_logging(logger, VERBOSITY_HIGH)
    server = kwargs.get("server", "rtk2go.com")
    port = int(kwargs.get("port", DEFAULT_PORT))
    mountpoint = kwargs.get("mountpoint", "")
    user = kwargs.get("user", getenv("PYGPSCLIENT_USER", "user"))
    password = kwargs.get("password", getenv("PYGPSCLIENT_PASSWORD", "password"))
    outfile = kwargs.get("outfile", "rtcmntrip.log")

    with open(outfile, "wb") as out:
        gnc = GNSSNTRIPClient()

        https = 1 if port == 443 else 0

        logger.info(
            f"RTCM NTRIP Client started, writing output to {outfile}... Press CTRL-C to terminate."
        )
        gnc.run(
            server=server,
            port=port,
            https=https,
            mountpoint=mountpoint,
            datatype="RTCM",
            ntripuser=user,
            ntrippassword=password,
            ggainterval=-1,
            output=out,
        )

        try:
            while True:
                sleep(3)
        except KeyboardInterrupt:
            logger.info("RTCM NTRIP Client terminated by User")


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
