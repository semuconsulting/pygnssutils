"""
spart_decrypt.py

Illustration of how to read, decrypt and decode the contents
of a binary SPARTN log file e.g. from an Thingstream PointPerfect
SPARTN MQTT or NTRIP service.

NB: decryption requires the key and basedate applicable at the
time the SPARTN log was originally captured.

Usage:

python3 spartn_decrypt.py infile="d9s_spartn_data.bin" key="bc75cdd919406d61c3df9e26c2f7e77a" basedate="2023-9-1-18:0:0"

Run from /examples folder. Can use output from mqtt_spartn_client.py
example.

Configured by default to use d9s_spartn_data.bin sample file.

FYI: SPARTNMessage objects implement a protected attribute `_padding`,
which represents the number of redundant bits added to the payload
content in order to byte-align the payload with the exact number of
bytes specified in the transport layer payload length nData. If the
payload has been successfully decrypted and decoded, the value of
_padding should always be >=0, <=8.

Created on 12 Feb 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

from datetime import UTC, datetime
from os import getenv
from sys import argv

from pyspartn import SPARTNReader, ERRIGNORE


def main(**kwargs):
    """
    Read, decrypt and decode SPARTN log file.
    """

    infile = kwargs.get("infile", "d9s_spartn_data.bin")
    key = kwargs.get(
        "key", getenv("MQTTKEY", default="bc75cdd919406d61c3df9e26c2f7e77a")
    )
    basedate = kwargs.get("basedate", "2023-9-1-18:0:0")
    if basedate == "":
        basedate = datetime.now(UTC)
    else:
        basedate = datetime.strptime(basedate, "%Y-%m-%d-%H:%M:%S")
    counts = {"OCB": 0, "HPAC": 0, "GAD": 0}

    with open(infile, "rb") as stream:
        spr = SPARTNReader(
            stream,
            decode=True,
            key=key,
            basedate=basedate,
            quitonerror=ERRIGNORE,  # 1 = log errors, 2 = terminate on error
        )
        for _, parsed in spr:
            for key in counts:
                if key in parsed.identity:
                    counts[key] += 1
            # print(parsed)
            # uncomment this line for an informal check on successful decryption...
            print(f"{parsed.identity} - Decrypted OK? {0 <= parsed._padding <= 8}")

    print(f"SPARTN messages read from {infile}: {str(counts).strip('{}')}")


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
