"""
gnssntripclient_cli.py

CLI wrapper for GNSSNTRIPClient class.

Created on 24 Jul 2024

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from datetime import datetime, timezone
from os import getenv
from queue import Queue
from threading import Thread
from time import sleep

from serial import Serial

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import (
    CLIAPP,
    DEFAULT_TLS_PORTS,
    EPILOG,
    OUTPUT_FILE,
    OUTPUT_NONE,
    OUTPUT_SERIAL,
    OUTPUT_SOCKET,
    VERBOSITY_CRITICAL,
    VERBOSITY_DEBUG,
    VERBOSITY_HIGH,
    VERBOSITY_LOW,
    VERBOSITY_MEDIUM,
)
from pygnssutils.gnssntripclient import (
    GGAFIXED,
    GGALIVE,
    INACTIVITY_TIMEOUT,
    MAX_RETRY,
    RETRY_INTERVAL,
    RTCM,
    SPARTN,
    WAITTIME,
    GNSSNTRIPClient,
)
from pygnssutils.socket_server import runserver


def runclient(**kwargs):
    """
    Start NTRIP client with CLI parameters.
    """

    with GNSSNTRIPClient(CLIAPP, **kwargs) as gnc:
        gnc.run(**kwargs)
        # run until stop event or user presses CTRL-C
        while not gnc.stopevent.is_set():
            sleep(WAITTIME)
        sleep(0.5)


def main():
    """
    CLI Entry point.

    :param: as per GNSSNTRIPClient constructor and run() method.
    :raises: ParameterError if parameters are invalid
    """
    # pylint: disable=raise-missing-from, too-many-statements

    ap = ArgumentParser(
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument(
        "-S", "--server", required=True, help="NTRIP server (caster) URL", default=""
    )
    ap.add_argument(
        "-P", "--port", required=False, help="NTRIP port", type=int, default=2101
    )
    ap.add_argument(
        "-M",
        "--mountpoint",
        required=False,
        help="NTRIP mountpoint (leave blank to get sourcetable)",
        default="",
    )
    ap.add_argument(
        "-H",
        "--https",
        required=False,
        help=(
            f"HTTPS (TLS) connection? 0 = HTTP, "
            f"1 = HTTPS (defaults to 1 if port in {DEFAULT_TLS_PORTS})"
        ),
        type=int,
        choices=[0, 1],
        default=0,
    )
    ap.add_argument(
        "-I",
        "--ipprot",
        required=False,
        help="IP protocol",
        choices=["IPv4", "IPv6"],
        default="IPv4",
    )
    ap.add_argument(
        "--flowinfo", required=False, help="Flow info for IPv6", type=int, default=0
    )
    ap.add_argument(
        "--scopeid", required=False, help="Scope ID for IPv6", type=int, default=0
    )
    ap.add_argument(
        "--retries",
        required=False,
        help="Maximum failed connection retries",
        type=int,
        default=MAX_RETRY,
    )
    ap.add_argument(
        "--retryinterval",
        required=False,
        help="Retry interval in seconds (* retries)",
        type=int,
        default=RETRY_INTERVAL,
    )
    ap.add_argument(
        "--timeout",
        required=False,
        help="Inactivity timeout in seconds",
        type=int,
        default=INACTIVITY_TIMEOUT,
    )
    ap.add_argument(
        "--ntripversion",
        required=False,
        dest="version",
        help="NTRIP protocol version",
        default="2.0",
    )
    ap.add_argument(
        "--datatype",
        required=False,
        help="Data type (RTCM or SPARTN)",
        choices=[RTCM, "rtcm", SPARTN, "spartn"],
        default=RTCM,
    )
    ap.add_argument(
        "--ntripuser",
        required=False,
        help="NTRIP authentication user",
        default=getenv("PYGPSCLIENT_USER", "anon"),
    )
    ap.add_argument(
        "--ntrippassword",
        required=False,
        help="NTRIP authentication password",
        default=getenv("PYGPSCLIENT_PASSWORD", "password"),
    )
    ap.add_argument(
        "--ggainterval",
        required=False,
        help="GGA NMEA sentence transmission interval (-1 = None)",
        type=int,
        default=-1,
    )
    ap.add_argument(
        "--ggamode",
        required=False,
        help=f"GGA pos source; {GGALIVE} = live from receiver, {GGAFIXED} = fixed reference",
        type=int,
        choices=[GGALIVE, GGAFIXED],
        default=GGAFIXED,
    )
    ap.add_argument(
        "--reflat", required=False, help="reference latitude", type=float, default=0.0
    )
    ap.add_argument(
        "--reflon", required=False, help="reference longitude", type=float, default=0.0
    )
    ap.add_argument(
        "--refalt", required=False, help="reference altitude", type=float, default=0.0
    )
    ap.add_argument(
        "--refsep", required=False, help="reference separation", type=float, default=0.0
    )
    ap.add_argument(
        "--spartndecode",
        required=False,
        help="Decode SPARTN payload?",
        type=int,
        choices=[0, 1],
        default=0,
    )
    ap.add_argument(
        "--spartnkey",
        required=False,
        help="Decryption key for encrypted SPARTN payloads",
        default=getenv("MQTTKEY", default=None),
    )
    ap.add_argument(
        "--spartnbasedate",
        required=False,
        help="Decryption basedate for encrypted SPARTN payloads",
        default=datetime.now(timezone.utc),
    )
    ap.add_argument(
        "--verbosity",
        required=False,
        help=(
            f"Log message verbosity "
            f"{VERBOSITY_CRITICAL} = critical, "
            f"{VERBOSITY_LOW} = low (error), "
            f"{VERBOSITY_MEDIUM} = medium (warning), "
            f"{VERBOSITY_HIGH} = high (info), {VERBOSITY_DEBUG} = debug"
        ),
        type=int,
        choices=[
            VERBOSITY_CRITICAL,
            VERBOSITY_LOW,
            VERBOSITY_MEDIUM,
            VERBOSITY_HIGH,
            VERBOSITY_DEBUG,
        ],
        default=VERBOSITY_MEDIUM,
    )
    ap.add_argument(
        "--logtofile",
        required=False,
        help="fully qualified log file name, or '' for no log file",
        type=str,
        default="",
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
            f"Output medium as formatted string. "
            f"If clioutput = {OUTPUT_FILE}, format = file name (e.g. '/home/myuser/rtcm.log'); "
            f"If clioutput = {OUTPUT_SERIAL}, format = port@baudrate (e.g. '/dev/tty.ACM0@38400'); "
            f"If clioutput = {OUTPUT_SOCKET}, format = hostip:port (e.g. '0.0.0.0:50010'). "
            "NB: gnssntripclient will have exclusive use of any serial or server port."
        ),
        default=None,
    )

    args = ap.parse_args()
    kwargs = vars(args)

    # assume HTTPS if port is 443 or 2102 (PointPerfect NTRIP TLS port)
    kwargs["https"] = 1 if kwargs["port"] in DEFAULT_TLS_PORTS else kwargs["https"]

    cliout = kwargs.pop("clioutput", OUTPUT_NONE)
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
            # output from ntrip client via a message queue
            Thread(
                target=runserver,
                args=(host, int(port), kwargs["output"]),
                daemon=True,
            ).start()
            runclient(**kwargs)
        else:
            kwargs["output"] = None
            runclient(**kwargs)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
