"""
pygnssutils - gnssapp.py

*** FOR ILLUSTRATION ONLY - NOT FOR PRODUCTION USE ***

Skeleton GNSS application which continuously receives and parses NMEA, UBX or RTCM
data from a receiver until the stop Event is set or stop() method invoked. Assumes
receiver is connected via serial USB or UART1 port.

The app also implements basic methods needed by certain pygnssutils classes.

Optional keyword arguments:

- recvqueue - if defined, a tuple of (raw_data, parsed_data) from the receiver will
  be placed on this Queue. This Queue can then be consumed by an external application.
- sendqueue - if defined, any data placed on this Queue will be sent to the receiver
  (e.g. UBX commands/polls or NTRIP RTCM data). Data must be a tuple of 
  (raw_data, parsed_data).
- idonly - determines whether the app prints out the entire parsed message,
  or just the message identity.
- enableubx - suppresses NMEA receiver output and substitutes a minimum set
  of UBX messages instead (NAV-PVT, NAV-SAT, NAV-DOP, RXM-RTCM).
- showstatus - show GNSS status at terminal.

Created on 27 Jul 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from logging import getLogger
from queue import Empty, Queue
from threading import Event, Thread
from time import sleep

from pynmeagps import NMEAMessageError, NMEAParseError
from pyrtcm import RTCMMessageError, RTCMParseError
from pyubx2 import (
    CARRSOLN,
    FIXTYPE,
    NMEA_PROTOCOL,
    RTCM3_PROTOCOL,
    UBX_PROTOCOL,
    UBXMessage,
    UBXMessageError,
    UBXParseError,
    UBXReader,
)
from serial import Serial

from pygnssutils import VERBOSITY_MEDIUM, UBXSimulator, set_common_args

DISCONNECTED = 0
CONNECTED = 1
FIXTYPE_GGA = {
    0: "NO FIX",
    1: "3D",
    2: "3D",
    4: "RTK FIXED",
    5: "RTK FLOAT",
    6: "DR",
}
DIFFAGE_PVT = {
    0: 0,
    1: 1,
    2: 2,
    3: 5,
    4: 10,
    5: 15,
    6: 20,
    7: 30,
    8: 45,
    9: 60,
    10: 90,
    11: 120,
}


class GNSSSkeletonApp:
    """
    Skeleton GNSS application which communicates with a GNSS receiver.
    """

    def __init__(
        self, port: str, baudrate: int, timeout: float, stopevent: Event, **kwargs
    ):
        """
        Constructor.

        :param str port: serial port e.g. "/dev/ttyACM1"
        :param int baudrate: baudrate
        :param float timeout: serial timeout in seconds
        :param Event stopevent: stop event
        """

        self.verbosity = kwargs.get("verbosity", VERBOSITY_MEDIUM)
        # configure logger with name "pygnssutils" in calling module
        self.logger = getLogger("pygnssutils.gnssapp")
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.stopevent = stopevent
        self.recvqueue = kwargs.get("recvqueue", None)
        self.sendqueue = kwargs.get("sendqueue", None)
        self.enableubx = kwargs.get("enableubx", True)
        self.showstatus = kwargs.get("showstatus", True)
        self.stream = None
        self.connected = DISCONNECTED
        self.fix = 0
        self.siv = 0
        self.lat = 0
        self.lon = 0
        self.alt = 0
        self.sep = 0
        self.hacc = 0
        self.sip = 0
        self.fix = "NO FIX"
        self.hdop = 0
        self.diffage = 0
        self.diffstation = 0

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

        self.logger.info("Starting GNSS reader/writer...")
        self.enable_ubx(self.enableubx)

        if self.port == "UBXSIMULATOR":
            self.stream = UBXSimulator(
                configfile="ubxsimulator.json", interval=1000, timeout=3
            )
            self.stream.start()
        else:
            self.stream = Serial(self.port, self.baudrate, timeout=self.timeout)
        self.connected = CONNECTED
        self.stopevent.clear()

        read_thread = Thread(
            target=self._read_loop,
            args=(
                self.stream,
                self.stopevent,
                self.recvqueue,
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
        self.connected = DISCONNECTED
        if self.stream is not None:
            self.stream.close()
        self.logger.info("GNSS reader/writer stopped")

    def _read_loop(
        self, stream: Serial, stopevent: Event, recvqueue: Queue, sendqueue: Queue
    ):
        """
        THREADED
        Reads and parses incoming GNSS data from the receiver,
        and sends any queued output data to the receiver.

        :param Serial stream: serial stream
        :param Event stopevent: stop event
        :param Queue recvqueue: queue for messages from receiver
        :param Queue sendqueue: queue for messages to send to receiver
        """

        ubr = UBXReader(
            stream, protfilter=(NMEA_PROTOCOL | UBX_PROTOCOL | RTCM3_PROTOCOL)
        )
        while not stopevent.is_set():
            try:
                if stream.in_waiting:
                    raw_data, parsed_data = ubr.read()
                    if parsed_data:
                        self._extract_data(parsed_data)
                        self.logger.info(f"GNSS>> {parsed_data.identity}")
                        self.logger.debug(parsed_data)
                        if recvqueue is not None:
                            # place data on receive queue
                            recvqueue.put((raw_data, parsed_data))

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
                self.logger.critical(f"Error parsing data stream {err}")
                continue

    def _extract_data(self, parsed_data: object):
        """
        Extract current navigation solution from NMEA or UBX message.

        :param object parsed_data: parsed NMEA or UBX navigation message
        """

        if hasattr(parsed_data, "fixType"):
            self.fix = FIXTYPE.get(parsed_data.fixType, "NO FIX")
        if hasattr(parsed_data, "carrSoln"):
            if parsed_data.carrSoln != 0:  # NO RTK
                self.fix = f"{CARRSOLN.get(parsed_data.carrSoln, self.fix)}"
        if hasattr(parsed_data, "quality"):
            self.fix = FIXTYPE_GGA.get(parsed_data.quality, "NO FIX")
        if hasattr(parsed_data, "numSV"):
            self.sip = parsed_data.numSV
        if hasattr(parsed_data, "lat"):
            self.lat = parsed_data.lat
        if hasattr(parsed_data, "lon"):
            self.lon = parsed_data.lon
        if hasattr(parsed_data, "alt"):
            self.alt = parsed_data.alt
        if hasattr(parsed_data, "HDOP"):
            self.hdop = parsed_data.HDOP
        if hasattr(parsed_data, "hDOP"):
            self.hdop = parsed_data.hDOP
        if hasattr(parsed_data, "diffAge"):
            self.diffage = parsed_data.diffAge
        if hasattr(parsed_data, "lastCorrectionAge"):
            self.diffage = DIFFAGE_PVT.get(parsed_data.lastCorrectionAge, 0)
        if hasattr(parsed_data, "diffStation"):
            self.diffstation = parsed_data.diffStation
        if hasattr(parsed_data, "hMSL"):  # UBX hMSL is in mm
            self.alt = parsed_data.hMSL / 1000
        if hasattr(parsed_data, "sep"):
            self.sep = parsed_data.sep
        if hasattr(parsed_data, "hMSL") and hasattr(parsed_data, "height"):
            self.sep = (parsed_data.height - parsed_data.hMSL) / 1000
        if hasattr(parsed_data, "hAcc"):  # UBX hAcc is in mm
            unit = 1 if parsed_data.identity == "PUBX00" else 1000
            self.hacc = parsed_data.hAcc / unit
        if self.showstatus:
            self.logger.info(
                f"fix {self.fix}, sip {self.sip}, lat {self.lat}, "
                f"lon {self.lon}, alt {self.alt:.3f} m, hAcc {self.hacc:.3f} m"
            )

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
                    raw_data, parsed_data = data
                    self.logger.info(f"GNSS<< {parsed_data.identity}")
                    self.logger.debug(f"{parsed_data}")
                    stream.write(raw_data)
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
            cfg_data.append((f"CFG_MSGOUT_UBX_NAV_DOP_{port_type}", enable * 4))
            cfg_data.append((f"CFG_MSGOUT_UBX_RXM_COR_{port_type}", enable))

        msg = UBXMessage.config_set(layers, transaction, cfg_data)
        self.sendqueue.put((msg.serialize(), msg))

    def get_coordinates(self) -> tuple:
        """
        Return current receiver navigation solution.
        (method needed by certain pygnssutils classes)

        :return: tuple
        :rtype: tuple
        """

        return (
            self.connected,
            self.lat,
            self.lon,
            self.alt,
            self.sep,
            self.sip,
            self.fix,
            self.hdop,
            self.diffage,
            self.diffstation,
        )


def main(**kwargs):
    """
    Main routine - CLI entry point.
    """

    recv_queue = Queue()  # set to None to print data to stdout
    send_queue = Queue()
    stop_event = Event()

    try:

        with GNSSSkeletonApp(
            kwargs.get("port", "/dev/ttyACM0"),
            int(kwargs.get("baudrate", 38400)),
            float(kwargs.get("timeout", 3)),
            stop_event,
            recvqueue=recv_queue,
            sendqueue=send_queue,
            verbosity=int(kwargs.get("verbosity", VERBOSITY_MEDIUM)),
            enableubx=int(kwargs.get("enableubx", 1)),
            showstatus=int(kwargs.get("showstatus", 1)),
        ) as gna:
            gna.run()
            while True:
                sleep(1)

    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":

    ap = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument(
        "-P", "--port", required=False, help="Serial port", default="/dev/ttyACM1"
    )
    ap.add_argument(
        "-B", "--baudrate", required=False, help="Baud rate", default=38400, type=int
    )
    ap.add_argument(
        "-T", "--timeout", required=False, help="Timeout in secs", default=3, type=float
    )
    ap.add_argument(
        "--enableubx", required=False, help="Enable UBX output", default=1, type=int
    )
    ap.add_argument(
        "--showstatus", required=False, help="Show GNSS status", default=1, type=int
    )
    args = set_common_args(ap)

    main(**args)
