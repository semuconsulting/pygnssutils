"""
pygnssutils - gnssapp.py

*** FOR ILLUSTRATION ONLY - NOT FOR PRODUCTION USE ***

Skeleton GNSS application which communicates with the receiver
and implements methods needed by other pygnssutils classes.

NB: Assumes receiver is connected via USB or UART1.

For brevity, will print out just the identities of all incoming
NMEA, UBX or RTCM messages, but the full message can be printed
by setting the optional 'idonly' flag to False.

An optional 'enableubx' flag suppresses NMEA receiver output
and substitutes a minimum set of UBX messages (NAV-PVT, NAV-SAT,
RXM-RTCM).

Created on 27 Jul 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""
# pylint: disable=invalid-name, too-many-instance-attributes

from queue import Empty, Queue
from threading import Event, Thread

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

CONNECTED = 1


class GNSSSkeletonApp:
    """
    Skeleton GNSS application which communicates with the receiver and
    implements methods needed by pygnssutils classes.
    """

    def __init__(self, serial: Serial, baudrate: int, timeout: float, **kwargs):
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
            target=self._read_loop,
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

    def _read_loop(self, stream: Serial, stopevent: Event, sendqueue: Queue):
        """
        THREADED
        Reads and parses incoming GNSS data from the receiver,
        and sends any queued output data to the receiver.

        :param Serial stream: serial stream
        :param Event stopevent: stop event
        :param Queue sendqueue: queue for messages to send to receiver
        """

        ubr = UBXReader(
            stream, protfilter=(NMEA_PROTOCOL | UBX_PROTOCOL | RTCM3_PROTOCOL)
        )
        while not stopevent.is_set():
            try:
                if stream.in_waiting:
                    _, parsed_data = ubr.read()
                    if parsed_data:
                        # extract current navigation solution
                        self._extract_coordinates(parsed_data)

                        # if it's an RXM-RTCM message, show which RTCM3 message
                        # it's acknowledging and whether it's been used or not.""
                        if parsed_data.identity == "RXM-RTCM":
                            nty = (
                                f" - {parsed_data.msgType} "
                                f"{'Used' if parsed_data.msgUsed > 0 else 'Not used'}"
                            )
                        else:
                            nty = ""

                        if self.idonly:
                            print(f"GNSS>> {parsed_data.identity}{nty}")
                        else:
                            print(parsed_data)

                # send any queued output data to receiver
                self._send_data(ubr.datastream, sendqueue)

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

    def _extract_coordinates(self, parsed_data: object):
        """
        Extract current navigation solution from NMEA or UBX message.

        :param object parsed_data: parsed NMEA or UBX navigation message
        """

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
        if hasattr(parsed_data, "hMSL") and hasattr(parsed_data, "height"):
            self.sep = (parsed_data.height - parsed_data.hMSL) / 1000
        if hasattr(parsed_data, "hAcc"):  # UBX hAcc is in mm
            unit = 1 if parsed_data.identity == "PUBX00" else 1000
            print(f"Estimated horizontal accuracy: {(parsed_data.hAcc / unit):.3f} m")

    def _send_data(self, stream: Serial, sendqueue: Queue):
        """
        Send any queued output data to receiver.
        Queue data is tuple of (raw_data, parsed_data).

        :param Serial stream: serial stream
        :param Queue sendqueue: queue for messages to send to receiver
        """

        if sendqueue is not None:
            try:
                while not sendqueue.empty():
                    data = sendqueue.get(False)
                    if data is not None:
                        raw, parsed = data
                        source = (
                            "NTRIP>>" if isinstance(parsed, RTCMMessage) else "GNSS<<"
                        )
                        if self.idonly:
                            print(f"{source} {parsed.identity}")
                        else:
                            print(parsed)
                        stream.write(raw)
                        sendqueue.task_done()
            except Empty:
                pass

    def enable_ubx(self, enable: bool):
        """
        Enable UBX output and suppress NMEA.

        :param bool enable: enable UBX and suppress NMEA output
        """

        layers = 1
        transaction = 0
        cfg_data = []
        for port_type in ("USB", "UART1"):
            cfg_data.append((f"CFG_{port_type}OUTPROT_NMEA", not enable))
            cfg_data.append((f"CFG_{port_type}OUTPROT_UBX", enable))
            cfg_data.append((f"CFG_MSGOUT_UBX_NAV_PVT_{port_type}", enable))
            cfg_data.append((f"CFG_MSGOUT_UBX_NAV_SAT_{port_type}", enable * 4))
            cfg_data.append((f"CFG_MSGOUT_UBX_RXM_RTCM_{port_type}", enable))

        msg = UBXMessage.config_set(layers, transaction, cfg_data)
        self.sendqueue.put((msg.serialize(), msg))

    def get_coordinates(self) -> tuple:
        """
        Return current receiver navigation solution
        (method needed by GNSSNTRIPClient if GGAMODE = 0)

        :return: tuple of (connection status, lat, lon, alt and sep)
        :rtype: tuple
        """

        return (CONNECTED, self.lat, self.lon, self.alt, self.sep)

    def set_event(self, eventtype: str):
        """
        (stub method needed by GNSSNTRIPClient if app is not None)

        :param str eventtype: name of event to create
        """

        # create event of specified eventtype
