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
a local serial port (USB or UART1).

GNSSNTRIPClient receives RTK data from the NTRIP caster
and outputs it to a message queue. A skeleton GNSSApp class
reads data from this queue and sends it to the receiver, while
reading and parsing data from the receiver and printing it
to the terminal.

The example also optionally sends NMEA GGA position sentences
to the caster at a prescribed interval, using either fixed
reference coordinates or live coordinates from the receiver.

For brevity, the example will print out just the identities of
all incoming GNSS and NTRIP messages, but the full message can
be printed by setting the optional 'idonly' flag to False.

An optional 'enableubx' flag suppresses NMEA receiver output
and substitutes a minimum set of UBX messages (NAV-PVT, NAV-SAT,
RXM-RTCM).

NB: Some NTRIP casters may stop sending RTK data after a while
if they're not receiving legitimate NMEA GGA position updates
from the client.

Created on 5 Jun 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""
# pylint: disable=invalid-name

from queue import Empty, Queue
from threading import Event, Thread
from time import sleep

from pynmeagps import NMEAMessageError, NMEAParseError
from pyrtcm import RTCMMessage, RTCMMessageError, RTCMParseError
from pyubx2 import (
    NMEA_PROTOCOL,
    RTCM3_PROTOCOL,
    UBX_PROTOCOL,
    UBXMessage,
    UBXMessageError,
    UBXParseError,
    UBXReader,
)
from serial import Serial

from pygnssutils import VERBOSITY_LOW, GNSSNTRIPClient

CONNECTED = 1


class GNSSApp:
    """
    Skeleton GNSS application which communicates with the receiver and
    implements the get_coordinates() method needed by the GNSSNTRIPClient
    class.
    """

    def __init__(self, serial, baudrate, timeout, **kwargs):
        """
        Constructor.
        """

        self.serial = serial
        self.baudrate = baudrate
        self.timeout = timeout
        self.sendqueue = kwargs.get("sendqueue", None)
        self.stopevent = kwargs.get("stopevent", None)
        self.idonly = kwargs.get("idonly", True)
        self.enableubx = kwargs.get("enableubx", False)
        self.stream = None
        self.lat = 0
        self.lon = 0
        self.alt = 0
        self.sep = 0

    def __enter__(self):
        """
        Context manager enter routine.
        """

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Context manager exit routine.

        Terminates app in an orderly fashion.
        """

        self.stop()

    def run(self):
        """
        Run GNSS reader/writer.
        """

        self.enable_ubx(self.enableubx)

        self.stream = Serial(self.serial, self.baudrate, timeout=self.timeout)
        self.stopevent.clear()

        read_thread = Thread(
            target=self.read_loop,
            args=(
                self.stream,
                self.stopevent,
                self.sendqueue,
            ),
            daemon=True,
        )
        read_thread.start()

    def stop(self):
        """
        Stop GNSS reader/writer.
        """

        self.stopevent.set()
        if self.stream is not None:
            self.stream.close()

    def read_loop(self, stream, stopevent, sendqueue):
        """
        THREADED
        Reads and parses incoming GNSS data from the receiver,
        and sends any queued output data to the receiver.
        """

        ubr = UBXReader(
            stream, protfilter=(NMEA_PROTOCOL | UBX_PROTOCOL | RTCM3_PROTOCOL)
        )
        while not stopevent.is_set():
            try:
                if stream.in_waiting:
                    _, parsed_data = ubr.read()
                    if parsed_data:
                        idy = parsed_data.identity

                        if hasattr(parsed_data, "lat"):
                            self.lat = parsed_data.lat
                        if hasattr(parsed_data, "lon"):
                            self.lon = parsed_data.lon
                        if hasattr(parsed_data, "alt"):
                            self.alt = parsed_data.alt
                        if hasattr(parsed_data, "hMSL"):  # UBX hMSL is in mm
                            self.alt = parsed_data.hMSL / 1000
                        if hasattr(parsed_data, "sep"):
                            self.sep = parsed_data.sep
                        if hasattr(parsed_data, "hMSL") and hasattr(
                            parsed_data, "height"
                        ):
                            self.sep = (parsed_data.height - parsed_data.hMSL) / 1000
                        if hasattr(parsed_data, "hAcc"):  # UBX hAcc is in mm
                            unit = 1 if idy == "PUBX00" else 0.001
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

                        if self.idonly:
                            print(f"GNSS>> {idy}{nty}")
                        else:
                            print(parsed_data)

                # send any queued output data to receiver
                if sendqueue is not None:
                    try:
                        while not sendqueue.empty():
                            data = sendqueue.get(False)
                            if data is not None:
                                if isinstance(data, tuple):
                                    raw, parsed = data
                                    if isinstance(parsed, RTCMMessage):
                                        if self.idonly:
                                            print(f"NTRIP>> {parsed.identity}")
                                        else:
                                            print(parsed)
                                else:
                                    raw = data
                                ubr.datastream.write(raw)
                            sendqueue.task_done()
                    except Empty:
                        pass

            except (
                UBXMessageError,
                UBXParseError,
                NMEAMessageError,
                NMEAParseError,
                RTCMMessageError,
                RTCMParseError,
            ) as err:
                print(f"Error parsing data stream {err}")
                continue

    def enable_ubx(self, enable):
        """
        Enable UBX output and suppress NMEA.
        """

        nmea_state = 0 if enable else 1
        layers = 1
        transaction = 0
        cfg_data = []
        for port_type in ("USB", "UART1"):
            cfg_data.append((f"CFG_{port_type}OUTPROT_NMEA", nmea_state))
            cfg_data.append((f"CFG_{port_type}OUTPROT_UBX", enable))
            cfg_data.append((f"CFG_MSGOUT_UBX_NAV_PVT_{port_type}", enable))
            cfg_data.append((f"CFG_MSGOUT_UBX_NAV_SAT_{port_type}", enable * 4))
            cfg_data.append((f"CFG_MSGOUT_UBX_RXM_RTCM_{port_type}", enable))

        msg = UBXMessage.config_set(layers, transaction, cfg_data)
        self.sendqueue.put(msg.serialize())

    def get_coordinates(self) -> tuple:
        """
        Return current receiver navigation solution
        (method needed by GNSSNTRIPClient if GGAMODE = 0)
        """

        return (CONNECTED, self.lat, self.lon, self.alt, self.sep)

    def set_event(self, eventtype):
        """
        (stub method needed by GNSSNTRIPClient)
        """

        # create event of specified eventtype


if __name__ == "__main__":
    # GNSS receiver serial port parameters - AMEND AS REQUIRED:
    SERIAL_PORT = "/dev/ttyACM1"
    BAUDRATE = 38400
    TIMEOUT = 3

    # NTRIP caster parameters - AMEND AS REQUIRED:
    # Ideally, mountpoint should be <30 km from location.
    IPPROT = "IPv4"  # or "IPv6"
    NTRIP_SERVER = "ntripserver.com"
    NTRIP_PORT = 2101
    FLOWINFO = 0  # for IPv6
    SCOPEID = 0  # for IPv6
    MOUNTPOINT = "MountpointName3"
    NTRIP_USER = "myuser@mydomain.com"
    NTRIP_PASSWORD = "mypassword"

    # NMEA GGA sentence status - AMEND AS REQUIRED:
    GGAMODE = 1  # use fixed reference position (0 = use live position)
    GGAINT = 60  # interval in seconds (-1 = do not send NMEA GGA sentences)
    # Fixed reference coordinates (only used when GGAMODE = 1) - AMEND AS REQUIRED:
    REFLAT = 51
    REFLON = -2.15
    REFALT = 40
    REFSEP = 0

    send_queue = Queue()
    stop_event = Event()

    try:
        print(f"Starting GNSS reader/writer on {SERIAL_PORT} @ {BAUDRATE}...\n")
        with GNSSApp(
            SERIAL_PORT,
            BAUDRATE,
            TIMEOUT,
            sendqueue=send_queue,
            stopevent=stop_event,
            idonly=True,
            enableubx=True,
        ) as gna:
            gna.run()
            sleep(2)  # wait for receiver to output at least 1 navigation solution

            print(f"Starting NTRIP client on {NTRIP_SERVER}:{NTRIP_PORT}...\n")
            with GNSSNTRIPClient(gna, verbosity=VERBOSITY_LOW) as gnc:
                streaming = gnc.run(
                    ipprot=IPPROT,
                    server=NTRIP_SERVER,
                    port=NTRIP_PORT,
                    flowinfo=FLOWINFO,
                    scopeid=SCOPEID,
                    mountpoint=MOUNTPOINT,
                    # ntripuser=NTRIP_USER, # pygnssutils>=1.0.12
                    # ntrippassword=NTRIP_PASSWORD, # pygnssutils>=1.0.12
                    reflat=REFLAT,
                    reflon=REFLON,
                    refalt=REFALT,
                    refsep=REFSEP,
                    ggamode=GGAMODE,
                    ggainterval=GGAINT,
                    output=send_queue,
                )

                while (
                    streaming and not stop_event.is_set()
                ):  # run until user presses CTRL-C
                    sleep(1)
                sleep(1)

    except KeyboardInterrupt:
        stop_event.set()
        print("Terminated by user")
