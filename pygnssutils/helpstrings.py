"""
Help text strings for pygnssutils CLI utilities

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""
# pylint: disable=line-too-long

from platform import system

# console escape sequences don't work on standard Windows terminal
if system() == "Windows":
    RED = ""
    GREEN = ""
    BLUE = ""
    YELLOW = ""
    MAGENTA = ""
    CYAN = ""
    BOLD = ""
    NORMAL = ""
else:
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    NORMAL = "\033[0m"

GNSSDUMP_HELP = (
    f"\n\n{RED}{BOLD}GNSSDUMP\n"
    + f"========{NORMAL}\n\n"
    + f"{BOLD}gnssdump{NORMAL} is a command line utility, provided with the"
    + f" {MAGENTA}{BOLD}pygnssutils{NORMAL} Python library, which parses the output"
    + " of a GNSS receiver to stdout (e.g. terminal) or to designated external protocol handlers.\n\n"
    + "gnssdump is capable of parsing NMEA, UBX and RTCM3 protocols.\n\n"
    + f"{GREEN}Usage (either stream, port, socket or filename must be specified):{NORMAL}\n\n"
    + "  Serial stream: gnssdump port=/dev/ttyACM0 baudrate=9600 timeout=3, **kwargs\n"
    + "  File stream: gnssdump filename=gpslog.bin, **kwargs\n"
    + "  Socket stream: gnssdump socket=192.168.0.72:50007, **kwargs\n"
    + "  Other stream object: gnssdump stream=stream, **kwargs\n"
    + "  Help: gnssdump -h\n\n"
    + f"{GREEN}Optional keyword arguments (default):{NORMAL}\n\n"
    + "  protfilter - 1 = NMEA, 2 = UBX, 4 = RTCM3 (7 - ALL)\n"
    + "  msgfilter - comma-separated list of required message identities e.g. NAV-PVT,GNGSA (None)\n"
    + "  limit - maximum number of messages to read (0 = unlimited)\n"
    + "  format - output format; 1 = parsed, 2 = binary (raw), 4 = hex, 8 = tabular hex, 16 = parsed as string (can be OR'd) (1)\n"
    + "  quitonerror - 0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors (1)\n"
    + "  validate - 1 = validate message checksum, 0 = ignore invalid checksum (1)\n"
    + "  msgmode - 0 = GET, 1 = SET, 2 = POLL (0)\n"
    + "  parsebitfield - boolean True = parse UBX 'X' type attributes as bitfields, False = leave as bytes (True)\n"
    + "  verbosity - log message verbosity 0 = low, 1 = medium, 2 = high (1)\n\n"
    + f"{GREEN}The following optional protocol handlers can either be instances of writeable output"
    + f" media (serial, file, socket or queue), or evaluable Python expressions{NORMAL}:\n\n"
    + "  nmeahandler - NMEA handler (None)\n"
    + "  ubxhandler - UBX handler (None)\n"
    + "  rtcmhandler - RTCM3 handler (None)\n"
    + "  errorhandler - error message handler (None)\n\n"
    + f"{GREEN}Type Ctrl-C to terminate.{NORMAL}\n\n"
    + f"{CYAN}© 2022 SEMU Consulting BSD 3-Clause license\n"
    + "https://github.com/semuconsulting/pygnssutils/\n\n"
)

GNSSSERVER_HELP = (
    f"\n\n{RED}{BOLD}GNSSSERVER\n"
    + f"=========={NORMAL}\n\n"
    + f"{BOLD}gnssserver{NORMAL} is a command line utility, provided with the"
    + f" {MAGENTA}{BOLD}pygnssutils{NORMAL} Python library, which acts as a TCP"
    + " Socket Server or NTRIP Server for GNSS data streams.\n\n"
    + "gnssserver is capable of broadcasting NMEA, UBX and RTCM3 protocols.\n\n"
    + f"{GREEN}Usage examples:{NORMAL}\n\n"
    + "Normal Mode:\n"
    + "  gnssserver inport=/dev/ttyACM0 hostip=192.168.0.20 outport=50010\n\n"
    + "NTRIP Server Mode:\n"
    + "  gnssserver inport=COM3 hostip=192.168.0.56 outport=2101 ntripmode=1 protfilter=4\n\n"
    + "Help:\n  gnssserver -h\n\n"
    + f"{GREEN}Optional keyword arguments (default):{NORMAL}\n\n"
    + "  inport - GNSS device input serial port (/dev/ttyACM0)\n"
    + "  hostip - IP address of host (0.0.0.0 - i.e. binds to all available IP addresses)\n"
    + "  outport - TCP port of server (50010) - should be an available non-privileged port\n"
    + "  ntripmode - 0 = TCP Socket Server, 1 = NTRIP server (0)\n"
    + "  protfilter - 1 = NMEA, 2 = UBX, 4 = RTCM3 (7 - ALL)\n"
    + "  msgfilter - comma-separated list of required message identities e.g. NAV-PVT,GNGSA (None)\n"
    + "  limit - maximum number of messages to read (0 = unlimited)\n"
    + "  format - output format; 1 = parsed, 2 = binary (raw), 4 = hex, 8 = tabular hex, 16 = parsed as string (can be OR'd) (2)\n"
    + f"  ({RED}NB{NORMAL}: if you use anything other than the default binary, a bespoke TCP client may be required)\n"
    + "  quitonerror - 0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors (1)\n"
    + "  parsebitfield - boolean True = parse UBX 'X' type attributes as bitfields, False = leave as bytes (True)\n"
    + "  verbosity - log message verbosity 0 = low, 1 = medium, 2 = high (1)\n\n"
    + "Client login credentials for NTRIP Server mode are set via host environment variables "
    + f"{MAGENTA}PYGPSCLIENT_USER{NORMAL} and {MAGENTA}PYGPSCLIENT_PASSWORD{NORMAL}\n\n"
    + f"{GREEN}Type Ctrl-C to terminate.{NORMAL}\n\n"
    + f"{CYAN}© 2022 SEMU Consulting BSD 3-Clause license\n"
    + f"https://github.com/semuconsulting/pygnssutils/{NORMAL}\n\n"
)
