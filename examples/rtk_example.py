"""
pygnssutils - rtk_example.py

*** FOR ILLUSTRATION ONLY - NOT FOR PRODUCTION USE ***

PLEASE RESPECT THE TERMS OF USE OF ANY NTRIP CASTER YOU
USE WITH THIS EXAMPLE - INAPPROPRIATE USE CAN RESULT IN
YOUR NTRIP USER ACCOUNT OR IP BEING TEMPORARILY BLOCKED.

This example illustrates how to use the UBXReader and
GNSSNTRIPClient classes to get RTCM3 RTK data from a
designated NTRIP caster/mountpoint and apply it to an
RTK-compatible GNSS receiver (e.g. ZED-F9P) connected to
a local serial port.

GNSSNTRIPClient receives RTK data from the NTRIP caster
and outputs it to a message queue. A send thread reads data
from this queue and sends it to the receiver. A read thread
reads and parses data from the receiver and prints it to the
terminal.

The example also optionally sends NMEA GGA position sentences
to the caster at a prescribed interval, using either fixed
reference coordinates or live coordinates from the receiver.

For brevity, the example will print out just the identities of
all incoming GNSS and NTRIP messages, but the full message can
be printed by setting the global PRINT_FULL variable to True.

The example also includes a simple illustration of horizontal
accuracy. Set the global SHOW_ACCURACY variable to True.

If the receiver is a u-blox UBX receiver, it can be configured
to output UBX RXM-RTCM messages which acknowledge receipt of
incoming RTK data and confirm whether or not it was used (i.e.
RTK correction applied).

NB: Some NTRIP casters may stop sending RTK data after a while
if they're not receiving legitimate NMEA GGA position updates
from the client.

Created on 5 Jun 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""
# pylint: disable=broad-except

from io import BufferedReader
from queue import Queue
from threading import Event, Lock, Thread
from time import sleep

from pyrtcm import RTCM_MSGIDS
from pyubx2 import NMEA_PROTOCOL, RTCM3_PROTOCOL, UBX_PROTOCOL, UBXReader, protocol
from serial import Serial

from pygnssutils import VERBOSITY_LOW, GNSSNTRIPClient, haversine

# Set to True to print entire GNSS/NTRIP message rather than just identity
PRINT_FULL = False
# Set to True to show estimated horizontal accuracy
SHOW_ACCURACY = False


def read_gnss(stream, lock, stopevent):
    """
    THREADED
    Reads and parses incoming GNSS data from receiver.
    """

    ubr = UBXReader(
        BufferedReader(stream),
        protfilter=(NMEA_PROTOCOL | UBX_PROTOCOL | RTCM3_PROTOCOL),
    )

    while not stopevent.is_set():
        try:
            if stream.in_waiting:
                lock.acquire()
                (raw_data, parsed_data) = ubr.read()  # pylint: disable=unused-variable
                lock.release()
                if parsed_data:
                    idy = parsed_data.identity

                    if SHOW_ACCURACY:
                        # show estimated horizontal accuracy and distance between receiver
                        # coordinates and fixed reference point
                        if hasattr(parsed_data, "lat") and hasattr(parsed_data, "lon"):
                            lat = parsed_data.lat
                            lon = parsed_data.lon
                            dev = haversine(lat, lon, REFLAT, REFLON) * 1000  # meters
                            print(
                                f"Receiver coordinates: {lat}, {lon}\r\n",
                                f"Approximate deviation from fixed ref: {dev:06,f} m",
                            )
                        if hasattr(parsed_data, "hAcc"):
                            unit = 1 if idy == "PUBX" else 0.001
                            print(
                                f"Estimated horizontal accuracy: {(parsed_data.hAcc * unit):.3f} m"
                            )

                    # if it's an RXM-RTCM message, show which RTCM3 message
                    # it's acknowledging and whether it's been used or not.""
                    if idy == "RXM-RTCM":
                        nty = (
                            f" - {parsed_data.msgType} "
                            f"{'Used' if parsed_data.msgUsed > 0 else 'Not used'}"
                        )
                    else:
                        nty = ""
                    if PRINT_FULL:
                        print(parsed_data)
                    else:
                        print(f"GNSS>> {idy}{nty}")
        except Exception as err:
            print(f"Something went wrong in read thread {err}")
            break


def send_gnss(stream, lock, stopevent, inqueue):
    """
    THREADED
    Reads RTCM3 data from message queue and sends it to receiver.
    """

    while not stopevent.is_set():
        try:
            raw_data, parsed_data = inqueue.get()
            if protocol(raw_data) == RTCM3_PROTOCOL:
                if PRINT_FULL:
                    print(parsed_data)
                else:
                    print(
                        f"NTRIP>> {parsed_data.identity} {RTCM_MSGIDS[parsed_data.identity]}"
                    )
                lock.acquire()
                stream.write(raw_data)
                lock.release()
        except Exception as err:
            print(f"Something went wrong in send thread {err}")
            break


if __name__ == "__main__":
    # pylint: disable=invalid-name

    # GNSS receiver serial port parameters - AMEND AS REQUIRED:
    SERIAL_PORT = "/dev/tty.usbmodem101"
    BAUDRATE = 38400
    TIMEOUT = 0.1

    # NTRIP caster parameters - AMEND AS REQUIRED:
    # Ideally, mountpoint should be <30 km from location.
    IPPROT = "IPv4"  # or "IPv6"
    NTRIP_SERVER = "ntrip_caster.com"
    NTRIP_PORT = 2101
    FLOWINFO = 0  # for IPv6
    SCOPEID = 0  # for IPv6
    MOUNTPOINT = "MOUNTPOINT"
    NTRIP_USER = "myuser@mydomain.com"
    NTRIP_PASSWORD = "password"

    # NMEA GGA sentence status - AMEND AS REQUIRED:
    GGAMODE = 1  # use fixed reference position (0 = use live position)
    GGAINT = 10  # interval in seconds (-1 = do not send NMEA GGA sentences)
    # Fixed reference coordinates (used when GGAMODE = 1) - AMEND AS REQUIRED:
    REFLAT = 53
    REFLON = -2.4
    REFALT = 40
    REFSEP = 0

    serial_lock = Lock()
    ntrip_queue = Queue()
    stop = Event()

    try:
        print(f"Opening serial port {SERIAL_PORT} @ {BAUDRATE}...\n")
        with Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT) as serial:
            stop.clear()

            print("Starting read thread...\n")
            read_thread = Thread(
                target=read_gnss,
                args=(
                    serial,
                    serial_lock,
                    stop,
                ),
                daemon=True,
            )
            read_thread.start()

            print("Starting send thread...\n")
            send_thread = Thread(
                target=send_gnss,
                args=(
                    serial,
                    serial_lock,
                    stop,
                    ntrip_queue,
                ),
                daemon=True,
            )
            send_thread.start()

            print(f"Starting NTRIP client on {NTRIP_SERVER}:{NTRIP_PORT}...\n")
            with GNSSNTRIPClient(None, verbosity=VERBOSITY_LOW) as gnc:
                streaming = gnc.run(
                    ipprot=IPPROT,
                    server=NTRIP_SERVER,
                    port=NTRIP_PORT,
                    flowinfo=FLOWINFO,
                    scopeid=SCOPEID,
                    mountpoint=MOUNTPOINT,
                    user=NTRIP_USER,
                    password=NTRIP_PASSWORD,
                    reflat=REFLAT,
                    reflon=REFLON,
                    refalt=REFALT,
                    refsep=REFSEP,
                    ggamode=GGAMODE,
                    ggainterval=GGAINT,
                    output=ntrip_queue,
                )

                while streaming and not stop.is_set():  # run until user presses CTRL-C
                    sleep(1)
                sleep(1)

    except KeyboardInterrupt:
        stop.set()

    print("Terminated by user")
