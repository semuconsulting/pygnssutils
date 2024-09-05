"""
gnssmqttclient_cli.py

CLI wrapper for GNSSMQTTClient class.

Created on 24 Jul 2024

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from datetime import datetime, timezone
from os import getenv, path
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from time import sleep

from serial import Serial

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import (
    CLIAPP,
    EPILOG,
    OUTPORT_SPARTN,
    OUTPUT_FILE,
    OUTPUT_NONE,
    OUTPUT_SERIAL,
    OUTPUT_SOCKET,
    SPARTN_PPSERVER,
)
from pygnssutils.gnssmqttclient import TIMEOUT, GNSSMQTTClient
from pygnssutils.helpers import set_common_args
from pygnssutils.socket_server import runserver

TIMEOUT = 8
DLGTSPARTN = "SPARTN Configuration"


def runclient(**kwargs):
    """
    Start MQTT client with CLI parameters.
    """

    waittime = float(kwargs["waittime"])
    with GNSSMQTTClient(CLIAPP, **kwargs) as gsc:
        streaming = gsc.start(**kwargs)
        while streaming and not kwargs["errevent"].is_set():
            sleep(waittime)
        sleep(waittime)


def main():
    """
    CLI Entry point.

    :param int waittime: response wait time in seconds (3)
    :param: as per GNSSSPARTNClient constructor and run() method.
    :raises: ParameterError if parameters are invalid
    """
    # pylint: disable=raise-missing-from

    clientid = getenv("MQTTCLIENTID", default="enter-client-id")
    ap = ArgumentParser(
        description="Client ID can be read from environment variable MQTTCLIENTID",
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument(
        "-I",
        "--clientid",
        required=False,
        help="Client ID",
        default=clientid,
    )
    ap.add_argument(
        "-S",
        "--server",
        required=False,
        help="SPARTN MQTT server URL",
        default=SPARTN_PPSERVER,
    )
    ap.add_argument(
        "-P",
        "--port",
        required=False,
        help="SPARTN MQTT server port",
        type=int,
        default=OUTPORT_SPARTN,
    )
    ap.add_argument(
        "-R",
        "--region",
        required=False,
        help="SPARTN region code",
        choices=["us", "eu", "au", "kr", "jp"],
        default="eu",
    )
    ap.add_argument(
        "-M",
        "--mode",
        required=False,
        help="SPARTN mode (0 - IP,1 - L-Band)",
        type=int,
        choices=[0, 1],
        default=0,
    )
    ap.add_argument(
        "--topic_ip",
        required=False,
        help="Subscribe to SPARTN IP topic for the selected region",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--topic_mga",
        required=False,
        help="Subscribe to UBX Assist-Now (MGA-EPH) topic",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--topic_key",
        required=False,
        help="Subscribe to UBX Key (RXM-SPARTNKEY) topic",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--tlscrt",
        required=False,
        help="Fully-qualified path to TLS cert (*.crt)",
        default=getenv(
            "MQTTCRT", default=path.join(Path.home(), f"device-{clientid}-pp-cert.crt")
        ),
    )
    ap.add_argument(
        "--tlskey",
        required=False,
        help="Fully-qualified path to TLS key (*.pem)",
        default=getenv(
            "MQTTPEM", default=path.join(Path.home(), f"device-{clientid}-pp-key.pem")
        ),
    )
    ap.add_argument(
        "--spartndecode",
        required=False,
        help="Decode payload?",
        type=int,
        choices=[0, 1],
        default=0,
    )
    ap.add_argument(
        "--spartnkey",
        required=False,
        help="Decryption key for encrypted payloads",
        default=getenv("MQTTKEY", default=None),
    )
    ap.add_argument(
        "--spartnbasedate",
        required=False,
        help="Decryption basedate for encrypted payloads",
        default=datetime.now(timezone.utc),
    )
    ap.add_argument(
        "--waittime",
        required=False,
        help="waitimer",
        type=float,
        default=0.5,
    )
    ap.add_argument(
        "--timeout",
        required=False,
        help="MQTT connection timeout (seconds)",
        type=int,
        default=TIMEOUT,
    )
    ap.add_argument(
        "--clioutput",
        required=False,
        help=(
            f"CLI output type {OUTPUT_NONE} = none, "
            f"{OUTPUT_FILE} = binary file, "
            f"{OUTPUT_SERIAL} = serial port, "
            f"{OUTPUT_SOCKET} = TCP socket server"
        ),
        type=int,
        choices=[OUTPUT_NONE, OUTPUT_FILE, OUTPUT_SERIAL, OUTPUT_SOCKET],
        default=OUTPUT_NONE,
    )
    ap.add_argument(
        "--output",
        required=False,
        help=(
            "Output medium as formatted string. "
            f"If clioutput = {OUTPUT_FILE}, format = file name (e.g. '/home/myuser/spartn.log'); "
            f"If clioutput = {OUTPUT_SERIAL}, format = port@baudrate (e.g. '/dev/tty.ACM0@38400'); "
            f"If clioutput = {OUTPUT_SOCKET}, format = hostip:port (e.g. '0.0.0.0:50010'). "
            "NB: gnssmqttclient will have exclusive use of any serial or server port."
        ),
        default=None,
    )
    kwargs = set_common_args("gnssmqttclient", ap)

    kwargs["errevent"] = Event()
    cliout = int(kwargs.pop("clioutput", OUTPUT_NONE))
    try:
        if cliout == OUTPUT_FILE:
            filename = kwargs["output"]
            with open(filename, "wb") as output:
                kwargs["output"] = output
                runclient(**kwargs)
        elif cliout == OUTPUT_SERIAL:
            port, baud = kwargs["output"].split("@")
            with Serial(port, int(baud), timeout=3) as output:
                kwargs["output"] = output
                runclient(**kwargs)
        elif cliout == OUTPUT_SOCKET:
            host, port = kwargs["output"].split(":")
            kwargs["output"] = Queue()
            # socket server runs as background thread, piping
            # output from mqtt client via a message queue
            Thread(
                target=runserver,
                args=(host, int(port), kwargs["output"]),
                daemon=True,
            ).start()
            runclient(**kwargs)
        else:
            kwargs["output"] = None
            runclient(**kwargs)
    except (KeyboardInterrupt, TimeoutError):
        pass


if __name__ == "__main__":
    main()
