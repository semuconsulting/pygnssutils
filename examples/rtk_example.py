"""
pygnssutils - rtk_example.py

*** FOR ILLUSTRATION ONLY - NOT FOR PRODUCTION USE ***

RUN FROM WITHIN /examples FOLDER:

python3 rtk_example.py

PLEASE RESPECT THE TERMS OF USE OF ANY NTRIP CASTER YOU
USE WITH THIS EXAMPLE - INAPPROPRIATE USE CAN RESULT IN
YOUR NTRIP USER ACCOUNT OR IP BEING TEMPORARILY BLOCKED.

This example illustrates how to use the UBXReader and
GNSSNTRIPClient classes to get RTCM3 or SPARTN RTK data
from a designated NTRIP caster/mountpoint and apply it
to an RTK-compatible u-blox GNSS receiver (e.g. ZED-F9P)
connected to a local serial port (USB or UART1).

GNSSNTRIPClient receives RTCM3 or SPARTN data from the NTRIP
caster and outputs it to a message queue. A basic
GNSSSkeletonApp class reads data from this queue and sends
it to the receiver, while reading and parsing data from the
receiver and printing it to the terminal.

GNSSNtripClient optionally sends NMEA GGA position sentences
to the caster at a prescribed interval, using either fixed
reference coordinates or live coordinates from the receiver.
For NTRIP 2.0 protocol, the first GGA sentence is embedded
in the HTTP GET request header.

NB: Some NTRIP casters may stop sending RTK data after a while
if they're not receiving legitimate NMEA GGA position updates
from the client.

Created on 5 Jun 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

# pylint: disable=invalid-name

from logging import getLogger
from queue import Empty, Queue
from sys import argv
from threading import Event
from time import sleep
from serial import Serial

from pygnssutils import (
    CLIAPP,
    VERBOSITY_DEBUG,
    VERBOSITY_HIGH,
    VERBOSITY_MEDIUM,
    GNSSNTRIPClient,
    set_logging,
    GNSSStreamer,
)

CONNECTED = 1

logger = getLogger("pygnssutils")


def main(**kwargs):
    """
    Main routine.
    """

    # GNSS receiver serial port parameters - AMEND AS REQUIRED:
    SERIAL_PORT = "/dev/ttyACM0"  # use "UBXSIMULATOR" to use dummy UBX serial stream
    BAUDRATE = 38400
    TIMEOUT = 10

    # NTRIP caster parameters - AMEND AS REQUIRED:
    # Ideally, mountpoint should be <30 km from location.
    IPPROT = "IPv4"  # or "IPv6"
    NTRIP_SERVER = "yourcaster"
    NTRIP_PORT = 2101
    HTTPS = 0  # 0 for HTTP, 1 for HTTPS
    FLOWINFO = 0  # for IPv6
    SCOPEID = 0  # for IPv6
    MOUNTPOINT = "yourmountpoint"  # leave blank to retrieve sourcetable
    NTRIP_USER = "youruserid"
    NTRIP_PASSWORD = "yourpassword"
    DATATYPE = "RTCM"  # "RTCM" or "SPARTN"

    # NMEA GGA sentence status - AMEND AS REQUIRED:
    GGAMODE = 0  # use fixed reference position (0 = use live position)
    GGAINT = 60  # interval in seconds (-1 = do not send NMEA GGA sentences)
    # Fixed reference coordinates (only used when GGAMODE = 1) - AMEND AS REQUIRED:
    REFLAT = 51.176534
    REFLON = -2.15453
    REFALT = 40.8542
    REFSEP = 26.1743

    outqueue = Queue()  # data output from receiver placed on this queue
    inqueue = Queue()  # data input to receiver placed on this queue
    stop_event = Event()

    set_logging(logger, VERBOSITY_HIGH)
    mylogger = getLogger("pygnssutils.rtk_example")

    try:
        with Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT) as stream:
            mylogger.info(
                f"Starting GNSS reader/writer on {SERIAL_PORT} @ {BAUDRATE}...\n"
            )
            with GNSSStreamer(
                CLIAPP,
                stream,
                stopevent=stop_event,
                outqueue=outqueue,
                inqueue=inqueue,
            ) as gna:
                gna.run()
                sleep(2)  # wait for receiver to output at least 1 navigation solution

                mylogger.info(
                    f"Starting NTRIP client on {NTRIP_SERVER}:{NTRIP_PORT}...\n"
                )
                with GNSSNTRIPClient(gna) as gnc:
                    streaming = gnc.run(
                        ipprot=IPPROT,
                        server=NTRIP_SERVER,
                        port=NTRIP_PORT,
                        https=HTTPS,
                        flowinfo=FLOWINFO,
                        scopeid=SCOPEID,
                        mountpoint=MOUNTPOINT,
                        ntripuser=NTRIP_USER,
                        ntrippassword=NTRIP_PASSWORD,
                        reflat=REFLAT,
                        reflon=REFLON,
                        refalt=REFALT,
                        refsep=REFSEP,
                        ggamode=GGAMODE,
                        ggainterval=GGAINT,
                        datatype=DATATYPE,
                        output=inqueue,  # send NTRIP data to receiver
                    )

                    while (
                        streaming and not stop_event.is_set()
                    ):  # run until user presses CTRL-C
                        if outqueue is not None:
                            # consume any received GNSS data from queue
                            try:
                                while not outqueue.empty():
                                    (_, parsed_data) = outqueue.get(False)
                                    outqueue.task_done()
                            except Empty:
                                pass
                        sleep(1)
                    sleep(1)

    except KeyboardInterrupt:
        stop_event.set()
        mylogger.info("Terminated by user")


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
