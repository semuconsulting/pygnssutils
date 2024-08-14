"""
ntripclient_asyncio.py

WORK IN PROGRESS - USE AT OWN RISK

Framework for asyncio version of NTRIP client.

Sends GET request to NTRIP caster, processes response and
sends RTCM datastream to receiver at designed serial port.

Usage:

python3 ntripclient_asyncio.py serial=/dev/ttyACM0 baudrate=38400 timeout=3 \
   caster=http://rtk2go.com:2101 tls=0 mountpoint=yourmp user=youruser password=yourpassword

Set mountpoint="" to retrieve sourcetable.

Type CTRL-C to terminate.

Created on 14 Aug 2024

:author: semuadmin
:copyright: 2024 SEMU Consulting
:license: BSD 3-Clause
"""

import asyncio
from base64 import b64encode
from io import BytesIO
from logging import getLogger
from sys import argv
from urllib.parse import urlsplit

from pyubx2 import ERR_IGNORE, RTCM3_PROTOCOL, UBXReader
from serial import Serial

from pygnssutils import HTTPERR, VERBOSITY_HIGH, set_logging

logger = getLogger("ntripclient_asyncio")
set_logging(logger, VERBOSITY_HIGH)


async def serial_worker(ser, inq):
    """
    Send raw RTCM data to receiver port.

    :param ser: serial stream
    :param inq: rtcm input queue
    """

    while True:
        raw = await inq.get()
        # await asyncio.sleep(0.01)
        rc = ser.write(raw)
        logger.info(f"serial_worker sent {rc} bytes")
        inq.task_done()


async def ntrip_worker(reader, outq):
    """
    Process NTRIP response.

    :param reader: socket reader
    :param outq: rtcm output queue
    """

    # pylint: disable=too-many-branches

    hdr = body = errc = ""
    stbl = []
    header = True
    while True:
        if header:  # processing HTTP header
            line = await reader.readline()
            line = line.decode()
            if "200 OK" in line:
                pass
            for errc in HTTPERR:
                if errc in line:
                    body = "err"
            if "400" in line:  # doesn't always return full error string
                errc = "400 Bad Request"
                body = "err"
            if "gnss/data" in line:
                body = "dat"
            if "gnss/sourcetable" in line:
                body = "srt"
            if line:
                hdr += line
            if line == "\r\n":  # end of header, start of body
                logger.info(f"Response:\n{hdr}")
                header = False
        elif body == "err":
            logger.error(f"HTTP error: {errc}")
            break
        elif body == "srt":  # processing gnss/sourcetable
            line = await reader.readline()
            line = line.decode()
            stbl.append(line)
            if "ENDSOURCETABLE" in line:
                logger.info(f"Sourcetable:\n{stbl}\n")
                break
        elif body == "dat":  # processing gnss/data
            line = await reader.read(4096)
            data = BytesIO(line)
            parser = UBXReader(data, protfilter=RTCM3_PROTOCOL, quitonerror=ERR_IGNORE)
            for raw, parsed in parser:
                if parsed is None:
                    break
                await outq.put(raw)
                logger.info(f"ntrip_worker received RTCM {parsed.identity}")


async def app(**kwargs):
    """
    Send HTTP(S) GET request to NTRIP caster and process response.
    Set mountpoint = "" to retrieve sourcetable.

    :param caster: NTRIP caster URL
    :param tls: TLS (HTTPS) connection True/False
    :param mountpoint: NTRIP mountpoint
    """

    serial = kwargs.get("serial", "/dev/ttyACM0")
    baudrate = int(kwargs.get("baudrate", 38400))
    timeout = int(kwargs.get("timeout", 3))
    ser = Serial(serial, baudrate, timeout=timeout)
    url = urlsplit(kwargs.get("caster", "http://rtk2go.com:2101"))
    tls = int(kwargs.get("tls", 0))
    mountpoint = kwargs.get("mountpoint", "")
    credentials = f"{kwargs.get("user", "anon")}:{kwargs.get("password", "password")}"
    credentials = b64encode(credentials.encode(encoding="utf-8")).decode(
        encoding="utf-8"
    )
    rtcmqueue = asyncio.Queue()
    if tls:
        reader, writer = await asyncio.open_connection(
            url.hostname,
            url.port,
            ssl=True,
        )
    else:
        reader, writer = await asyncio.open_connection(url.hostname, url.port)

    query = (
        f"GET /{mountpoint} HTTP/1.1\r\n"
        f"Host: {url.hostname}:{url.port}\r\n"
        "Ntrip-Version: Ntrip/2.0\r\n"
        "User-Agent: NTRIP ntripclient_asyncio/1.0.0\r\n"
        "Accept: */*\r\n"
        f"Authorization: Basic {credentials}\r\n"
        "Connection: close\r\n\r\n"  # NECESSARY!!!
    )
    logger.info(f"Query:\n{query}")

    writer.write(query.encode("utf-8"))

    try:

        tasks = []
        tasks.append(serial_worker(ser, rtcmqueue))
        tasks.append(ntrip_worker(reader, rtcmqueue))
        await asyncio.gather(*tasks, return_exceptions=True)

    except asyncio.exceptions.CancelledError:
        logger.warning("Task(s) cancelled")
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":

    asyncio.run(app(**dict(arg.split("=") for arg in argv[1:])))
