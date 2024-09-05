"""
gnssstreamer_cli.py

CLI wrapper for GNSSStreamer class.

Supported GNSS datastreams:
 - serial
 - socket
 - file
 - generic stream
Supported output channels:
 - terminal (stdout)
 - socket
 - binary file
 - text file
 - lambda expression
Supported input channels:
 - NTRIP RTCM client
 - NTRIP SPARTN client
 - MQTT SPARTN client
 - serial stream
 - file stream

Created on 24 Jul 2024

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from io import BufferedWriter, TextIOWrapper
from queue import Queue
from socket import create_connection, gethostbyname, socket
from threading import Event, Thread
from time import sleep
from types import FunctionType

from pyubx2 import ERR_LOG, SETPOLL, UBXReader
from serial import Serial, SerialException

from pygnssutils._version import __version__ as VERSION
from pygnssutils.exceptions import ParameterError
from pygnssutils.globals import (
    CLIAPP,
    ENCODE_CHUNKED,
    ENCODE_COMPRESS,
    ENCODE_DEFLATE,
    ENCODE_GZIP,
    ENCODE_NONE,
    EPILOG,
    FORMAT_BINARY,
    FORMAT_HEX,
    FORMAT_HEXTABLE,
    FORMAT_JSON,
    FORMAT_PARSED,
    FORMAT_PARSEDSTRING,
    INPUT_FILE,
    INPUT_MQTT_SPARTN,
    INPUT_NONE,
    INPUT_NTRIP_RTCM,
    INPUT_NTRIP_SPARTN,
    INPUT_SERIAL,
    OUTPUT_FILE,
    OUTPUT_HANDLER,
    OUTPUT_NONE,
    OUTPUT_SERIAL,
    OUTPUT_SOCKET,
    OUTPUT_TEXT_FILE,
    UBXSIMULATOR,
)
from pygnssutils.gnssmqttclient import GNSSMQTTClient
from pygnssutils.gnssntripclient import GNSSNTRIPClient
from pygnssutils.gnssstreamer import GNSSStreamer
from pygnssutils.helpers import parse_url, set_common_args
from pygnssutils.socket_server import runserver
from pygnssutils.socketwrapper import SocketWrapper
from pygnssutils.ubxsimulator import UBXSimulator

STATUSINTERVAL = 5


def _do_cli_output(raw_data: bytes, formatted_data: list, outqueue: Queue, **kwargs):
    """
    Custom CLI output handler for gnssstreamer.

    :param bytes raw_data: raw data
    :param list formatted_data: list of formatted data e.g. [NMEAMessage]
    :param Queue outqueue: queue containing output from GNSS datastream
    :raises: ParameterError
    """

    # pylint: disable=unused-argument

    output = kwargs.get("output", None)
    logger = kwargs.get("logger", None)
    if logger is not None:
        logger.debug(formatted_data)
    try:
        for line in formatted_data:
            if isinstance(output, (Serial, BufferedWriter)):
                output.write(line)
            elif isinstance(output, TextIOWrapper):
                output.write(f"{line}\n")
            elif isinstance(output, Queue):
                output.put(line)
            elif isinstance(output, socket):
                output.sendall(line)
            elif isinstance(output, FunctionType):  # lambda expression
                output(line)
            else:
                print(line)
    except TypeError as err:
        raise ParameterError(
            f"--format {kwargs.get('outformat', None)} and --output "
            f"{kwargs.get('output', None)} arguments are incompatible {err}"
        ) from err


def _setup_input_ntrip(app: object, datatype: str, **kwargs) -> object:
    """
    Set up NTRIP client as input data source.

    :param app: calling application (i.e. gnssstreamer)
    :param datatype: "RTCM" or "SPARTN"
    :return: reference to NTRIP client
    :rtype: GNSSNTRIPClient
    """

    prot, hostname, port, path = parse_url(kwargs["input"])
    prot = 1 if prot == "https" else 0

    gnc = GNSSNTRIPClient(app)
    gnc.run(
        server=hostname,
        port=port,
        https=prot,
        mountpoint=path,
        ntripuser=kwargs.get("rtkuser", "anon"),
        ntrippassword=kwargs.get("rtkpassword", "password"),
        ggamode=0,
        ggainterval=kwargs.get("rtkggaint", -1),
        datatype=datatype,
        output=kwargs["inqueue"],  # send NTRIP data to receiver
    )

    return gnc


def _setup_input_mqtt(app: object, datatype: str, **kwargs) -> object:
    """
    Set up MQTT SPARTN client as input data source.

    :param app: calling application (i.e. gnssstreamer)
    :param datatype: "MQTT"
    :return: reference to MQTT client
    :rtype: GNSSMQTTClient
    """

    # pylint: disable=unused-argument

    prot, hostname, port, path = parse_url(kwargs["input"])
    prot = 1 if prot == "https" else 0

    gmq = GNSSMQTTClient(app)
    gmq.start(
        server=hostname,
        port=port,
        clientid=kwargs.get("rtkuser", "anon"),
        region=path.lower(),  # e.g. "eu"
        mode=0,  # IP (as opposed to 1 = L-Band)
        output=kwargs["inqueue"],  # send SPARTN data to receiver
    )

    return gmq


def _setup_input_stream(app: object, datatype: str, **kwargs) -> object:
    """
    Set up serial stream as input data source.

    :param app: calling application (i.e. gnssstreamer)
    :param int datatype: "SERIAL" or "FILE"
    :return: reference to stream
    :rtype: stream
    :raises: ParameterError if input stream descriptor invalid or not found
    """

    # pylint: disable=unused-argument

    def runreader(stream: object, output: Queue):
        """
        THREADED
        Serial stream reader. Parses data from
        serial stream and passes it to receiver
        input queue.

        :param object stream: input stream
        :param Queue output: queue to receiver
        """

        try:
            ubr = UBXReader(stream, msgmode=SETPOLL, quitonerror=ERR_LOG)
            for raw, _ in ubr:
                if raw is not None:
                    output.put(raw)
                else:
                    break  # EOF
        except ValueError:
            pass  # null buffer, treat as EOF

    def startreader(stream: object, output: Queue):
        """
        Start serial reader thread.

        :param object stream: input stream
        :param Queue output: queue to receiver
        """

        Thread(
            target=runreader,
            args=(stream, output),
            daemon=True,
        ).start()

    instream = kwargs.get("input", "")
    output = kwargs["inqueue"]
    try:
        if datatype == "SERIAL":  # serial port
            port, baudrate = instream.split("@")
            with Serial(port, baudrate, timeout=5) as stream:
                startreader(stream, output)
        else:  # binary file
            with open(instream, "rb") as stream:
                startreader(stream, output)
    except (FileNotFoundError, SerialException, ValueError) as err:
        raise ParameterError(
            f"Invalid input stream descriptor '{instream}' {err}"
        ) from err


def _setup_output(**kwargs):
    """
    Process CLI arguments to setup specified
    output channel (serial, socket, file). The
    different output channels will be handled via
    the customer outputhandler `do_cli_output`.

    :param dict kwargs: parsed CLI arguments
    """

    cliout = int(kwargs.pop("clioutput", OUTPUT_NONE))
    output = kwargs.pop("output", None)
    if cliout == OUTPUT_FILE:
        filename = output
        with open(filename, "wb") as output:
            kwargs["output"] = output
            _setup_datastream(**kwargs)
    elif cliout == OUTPUT_TEXT_FILE:
        filename = output
        with open(filename, "w", encoding="utf-8") as output:
            kwargs["output"] = output
            _setup_datastream(**kwargs)
    elif cliout == OUTPUT_SERIAL:
        port, baud = output.split("@")
        with Serial(port, int(baud), timeout=3) as output:
            kwargs["output"] = output
            _setup_datastream(**kwargs)
    elif cliout == OUTPUT_SOCKET:
        host, port = output.split(":")
        output = Queue()
        # socket server runs as background thread, piping
        # output from gnssstreamer via a message queue
        Thread(
            target=runserver,
            args=(host, int(port), output),
            daemon=True,
        ).start()
        kwargs["output"] = output
        _setup_datastream(**kwargs)
    elif cliout == OUTPUT_HANDLER:
        output = eval(output)  # pylint: disable=eval-used
        kwargs["output"] = output
        _setup_datastream(**kwargs)
    else:
        kwargs["output"] = None
        _setup_datastream(**kwargs)


def _setup_datastream(**kwargs):
    """
    Process CLI arguments to setup specified
    input datastream (serial, socket, file, other),
    and then run streamer using this stream.

    :param dict kwargs: parsed CLI arguments
    :raises: ParameterError if args are invalid
    """

    datastream = kwargs.pop("datastream", None)
    port = kwargs.pop("port", None)
    sock = kwargs.pop("socket", None)
    baudrate = int(kwargs.pop("baudrate", 9600))
    timeout = int(kwargs.pop("timeout", 3))
    filename = kwargs.pop("filename", None)
    encoding = kwargs.pop("encoding", ENCODE_NONE)

    if datastream is None and port is None and socket is None and filename is None:
        raise ParameterError(
            "Either stream, port, socket or filename keyword argument "
            "must be provided.\nType gnsssteamer -h for help.",
        )

    if datastream is not None:  # generic stream
        with datastream as stream:
            _run_streamer(stream, **kwargs)
    elif port is not None:  # serial
        if port.upper() == UBXSIMULATOR:
            with UBXSimulator() as stream:
                _run_streamer(stream, **kwargs)
        else:
            with Serial(port, baudrate, timeout=timeout) as stream:
                _run_streamer(stream, **kwargs)
    elif sock is not None:  # socket
        hostport = sock.split(":")
        if len(hostport) != 2:
            raise ParameterError("socket argument must be in the format host:port")
        hostname = hostport[0]
        port = int(hostport[1])
        ip = gethostbyname(hostname)
        with create_connection((ip, port), timeout) as sock:
            # wrap socket to allow processing as normal stream
            stream = SocketWrapper(sock, encoding)
            _run_streamer(stream, **kwargs)
    elif filename is not None:  # binary file
        with open(filename, "rb") as stream:
            _run_streamer(stream, **kwargs)


def _run_streamer(stream, **kwargs):
    """
    Run streaming application with specified input and
    output channels and GNSS datastream.

    :param dict kwargs: parsed CLI arguments
    """

    cliinput = None
    stopevent = Event()
    stopevent.clear()
    inqueue = Queue()
    kwargs["stopevent"] = stopevent
    kwargs["inqueue"] = inqueue  # gnssstreamer input
    # kwargs["output"] = inqueue  # gnssntripclient output
    kwargs["outputhandler"] = _do_cli_output
    cliinput = int(kwargs.get("cliinput", INPUT_NONE))

    try:
        with GNSSStreamer(CLIAPP, stream, **kwargs) as app:

            # setup input channel
            if cliinput == INPUT_NTRIP_RTCM:
                _setup_input_ntrip(app, "RTCM", **kwargs)
            elif cliinput == INPUT_NTRIP_SPARTN:
                _setup_input_ntrip(app, "SPARTN", **kwargs)
            elif cliinput == INPUT_MQTT_SPARTN:
                _setup_input_mqtt(app, "MQTT", **kwargs)
            elif cliinput == INPUT_SERIAL:
                _setup_input_stream(app, "SERIAL", **kwargs)
            elif cliinput == INPUT_FILE:
                _setup_input_stream(app, "FILE", **kwargs)

            while not stopevent.is_set():  # loop until CTRL-C
                sleep(1)
            # cliinput.stop()
    except KeyboardInterrupt:
        stopevent.set()


def main():
    """
    CLI Entry point.
    """
    # pylint: disable=raise-missing-from

    ap = ArgumentParser(
        description="One of either -P port, -S socket or -F filename must be specified",
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument("-P", "--port", required=False, help="Serial port")
    ap.add_argument("-F", "--filename", required=False, help="Input file path/name")
    ap.add_argument(
        "-S",
        "--socket",
        required=False,
        help="Input socket host:port",
    )
    ap.add_argument(
        "--baudrate",
        required=False,
        help="Serial baud rate",
        type=int,
        choices=[4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800],
        default=9600,
    )
    ap.add_argument(
        "--timeout",
        required=False,
        help="Serial timeout in seconds",
        type=float,
        default=3.0,
    )
    ap.add_argument(
        "--format",
        required=False,
        help=(
            f"{FORMAT_PARSED} - parsed as object; "
            f"{FORMAT_BINARY} - binary (raw); "
            f"{FORMAT_HEX} - hexadecimal; "
            f"{FORMAT_HEXTABLE} - tabular hexadecimal; "
            f"{FORMAT_PARSEDSTRING} - parsed as string; "
            f"{FORMAT_JSON} - JSON. "
            f"Options can be OR'd e.g. {FORMAT_PARSED} | {FORMAT_HEXTABLE}."
        ),
        type=int,
        default=FORMAT_PARSED,
    )
    ap.add_argument(
        "--validate",
        required=False,
        help="1 = validate checksums, 0 = do not validate",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--msgmode",
        required=False,
        help="0 = GET, 1 = SET, 2 = POLL, 3 = SETPOLL",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
    )
    ap.add_argument(
        "--parsebitfield",
        required=False,
        help="1 = parse UBX 'X' attributes as bitfields, 0 = leave as bytes",
        type=int,
        choices=[0, 1],
        default=1,
    )
    ap.add_argument(
        "--encoding",
        required=False,
        help=(
            f"Socket stream encoding {ENCODE_NONE} = none, "
            f"{ENCODE_CHUNKED} = chunked, {ENCODE_GZIP} = gzip, "
            f"{ENCODE_COMPRESS} = compress, {ENCODE_DEFLATE} = deflate. "
            f"Options can be OR'd e.g. {ENCODE_CHUNKED} | {ENCODE_GZIP}."
        ),
        type=int,
        default=ENCODE_NONE,
    )
    ap.add_argument(
        "--quitonerror",
        required=False,
        help="0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors",
        type=int,
        choices=[0, 1, 2],
        default=1,
    )
    ap.add_argument(
        "--protfilter",
        required=False,
        help="1 = NMEA, 2 = UBX, 4 = RTCM3 (can be OR'd)",
        type=int,
        choices=[1, 2, 3, 4, 5, 6, 7],
        default=7,
    )
    ap.add_argument(
        "--msgfilter",
        required=False,
        help=(
            "Comma-separated string of message identities e.g. 'NAV-PVT,GNGSA,1087'. "
            + "A period clause may be added to each msg identity e.g. '1087(10)', "
            + "signifying the minimum period in seconds between messages of this type."
        ),
        default=None,
    )
    ap.add_argument(
        "--limit",
        required=False,
        help="Maximum number of messages to read (0 = unlimited)",
        type=int,
        default=0,
    )
    ap.add_argument(
        "--clioutput",
        required=False,
        help=(
            f"CLI output type {OUTPUT_NONE} = terminal, "
            f"{OUTPUT_FILE} = binary file, "
            f"{OUTPUT_SERIAL} = serial port, "
            f"{OUTPUT_SOCKET} = TCP socket server, "
            f"{OUTPUT_HANDLER} = evaluable Python expression, "
            f"{OUTPUT_TEXT_FILE} = text file"
        ),
        type=int,
        choices=[
            OUTPUT_NONE,
            OUTPUT_FILE,
            OUTPUT_SERIAL,
            OUTPUT_SOCKET,
            OUTPUT_HANDLER,
            OUTPUT_TEXT_FILE,
        ],
        default=OUTPUT_NONE,
    )
    ap.add_argument(
        "--output",
        required=False,
        help=(
            f"Output descriptor. "
            f"If clioutput = {OUTPUT_FILE} or {OUTPUT_TEXT_FILE}, format = file name "
            "(e.g. '/home/myuser/ubxdata.ubx'); "
            f"If clioutput = {OUTPUT_SERIAL}, format = port@baudrate (e.g. '/dev/tty.ACM0@38400'); "
            f"If clioutput = {OUTPUT_SOCKET}, format = hostip:port (e.g. '0.0.0.0:50010'); "
            f"If clioutput = {OUTPUT_HANDLER}, format = evaluable Python expression. "
            "NB: gnssstreamer will have exclusive use of any serial or server port."
        ),
        default=None,
    )
    ap.add_argument(
        "--cliinput",
        required=False,
        help=(
            f"CLI input type {INPUT_NONE} = none, "
            f"{INPUT_NTRIP_RTCM} = RTK NTRIP RTCM, "
            f"{INPUT_NTRIP_SPARTN} = RTK NTRIP SPARTN, "
            f"{INPUT_MQTT_SPARTN} = RTK MQTT SPARTN, "
            f"{INPUT_SERIAL} = serial port, "
            f"{INPUT_FILE} = binary file"
        ),
        type=int,
        choices=[
            INPUT_NONE,
            INPUT_NTRIP_RTCM,
            INPUT_NTRIP_SPARTN,
            INPUT_MQTT_SPARTN,
            INPUT_SERIAL,
            INPUT_FILE,
        ],
        default=INPUT_NONE,
    )
    ap.add_argument(
        "--input",
        required=False,
        help=(
            f"Input descriptor. "
            f"If cliinput = {INPUT_NTRIP_RTCM}, format = full url "
            "(e.g. 'http://rtk2go.com:2101/MOUNTPOINT'); "
            f"If cliinput = {INPUT_NTRIP_SPARTN}, format = full url "
            "(e.g. 'https://ppntrip.services.u-blox.com:2102/EU'); "
            f"If cliinput = {INPUT_MQTT_SPARTN}, format = full url "
            "(e.g. 'https://pp.services.u-blox.com:8883/eu', where /path signifies region); "
            f"If cliinput = {INPUT_SERIAL}, format = port@baudrate (e.g. '/dev/tty.ACM1@38400'); "
            f"If cliinput = {INPUT_FILE}, format = file name (e.g. '/home/myuser/ubxconfig.ubx'). "
            "NB: gnssstreamer will have exclusive use of any serial port."
        ),
        default=None,
    )
    ap.add_argument(
        "--rtkuser",
        required=False,
        help="Username or ClientID for RTK service (if --cliinput = 1, 2 or 3).",
        default="anon",
    )
    ap.add_argument(
        "--rtkpassword",
        required=False,
        help="Password for RTK service (if --cliinput = 1, 2 or 3).",
        default="password",
    )
    ap.add_argument(
        "--rtkggaint",
        required=False,
        help=(
            "NMEA GGA sentence interval in seconds for RTK service "
            "(if --cliinput = 1 or 2) (-1 = None)."
        ),
        type=int,
        default=-1,
    )
    kwargs = set_common_args("gnssstreamer", ap)
    kwargs["outformat"] = kwargs.pop("format")  # avoid 'redefines format' warning
    _setup_output(**kwargs)


if __name__ == "__main__":
    main()
