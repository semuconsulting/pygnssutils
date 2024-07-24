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
from threading import Event
from time import sleep

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import (
    CLIAPP,
    EPILOG,
    OUTPORT_SPARTN,
    SPARTN_PPSERVER,
    VERBOSITY_DEBUG,
    VERBOSITY_HIGH,
    VERBOSITY_LOW,
    VERBOSITY_MEDIUM,
)
from pygnssutils.gnssmqttclient import TIMEOUT, GNSSMQTTClient

TIMEOUT = 8
DLGTSPARTN = "SPARTN Configuration"


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
        "-C",
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
        help="Subscribe to SPARTN MGA (Assist-Now) topic",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--topickey",
        required=False,
        help="Subscribe to SPARTN Key (RXM-SPARTNKEY) topic",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--tlscrt",
        required=False,
        help="Fully-qualified path to TLS cert (*.crt)",
        default=path.join(Path.home(), f"device-{clientid}-pp-cert.crt"),
    )
    ap.add_argument(
        "--tlskey",
        required=False,
        help="Fully-qualified path to TLS key (*.pem)",
        default=path.join(Path.home(), f"device-{clientid}-pp-key.pem"),
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
        "--output",
        required=False,
        help="Output medium (defaults to stdout)",
        default=None,
    )
    ap.add_argument(
        "--verbosity",
        required=False,
        help=(
            f"Log message verbosity {VERBOSITY_LOW} = low, {VERBOSITY_MEDIUM} = medium, "
            f"{VERBOSITY_HIGH} = high, {VERBOSITY_DEBUG} = debug"
        ),
        type=int,
        choices=[VERBOSITY_LOW, VERBOSITY_MEDIUM, VERBOSITY_HIGH, VERBOSITY_DEBUG],
        default=VERBOSITY_MEDIUM,
    )
    ap.add_argument(
        "--logtofile",
        required=False,
        help="0 = log to stdout, 1 = log to file '/logpath/gnssspartnclient-timestamp.log'",
        choices=[0, 1],
        type=int,
        default=0,
    )
    ap.add_argument(
        "--logpath",
        required=False,
        help="Fully qualified path to logfile folder",
        default=".",
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
        "--errevent",
        required=False,
        help="Error event",
        default=Event(),
    )

    args = ap.parse_args()
    kwargs = vars(args)
    try:
        with GNSSMQTTClient(CLIAPP, **kwargs) as gsc:
            streaming = gsc.start(**kwargs)
            while (
                streaming and not kwargs["errevent"].is_set()
            ):  # run until error or user presses CTRL-C
                sleep(args.waittime)
            sleep(args.waittime)

    except (KeyboardInterrupt, TimeoutError):
        gsc.stop()


if __name__ == "__main__":
    main()
