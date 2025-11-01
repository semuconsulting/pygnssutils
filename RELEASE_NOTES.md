# pygnssutils

### RELEASE 1.1.19

ENHANCEMENTS:

1. Add support for TLS connections in SocketServer. Introduces two alternative client request handler classes - ClientHandler (HTTP) or ClientHandlerTLS (HTTPS). TLS operation requires a suitable TLS certificate/key pair (in pem format) to be located at a path designated by
environment variable `PYGNSSUTILS_PEMPATH` - the default path is $HOME/pygnssutils.pem. See Sphinx documentation for details.

   A self-signed pem file suitable for test and demonstration purposes can be created thus:
   ```shell
   openssl req -x509 -newkey rsa:4096 -keyout pygnssutils.pem -out pygnssutils.pem -sha256 -days 3650 -nodes
   ```
 
### RELEASE 1.1.18

ENHANCEMENTS:

1. Add gnssreader class.
1. Add support for Quectel QGC protocol.

### RELEASE 1.1.17

1. Update minimum versions of pyubx2 and pynmeagps to cater for various fixes and new message types.

### RELEASE 1.1.16

FIXES:

1. Fix gnssntripclient inappropriate critical error for socket.timeout in Python<3.9 Fixes #118

CHANGES:

1. Min versions of pyubx2 and pysbf2 updated. 

### RELEASE 1.1.15

FIXES:

1. gnssstreamer Fix allow_reuse_addr setting Fixes #115

### RELEASE 1.1.14

ENHANCEMENTS:

1. Add support for SBF (Septentrio Binary Format) protocol in GNSSStreamer.

### RELEASE 1.1.13

FIXES:

1. Fix issue in GNSSNTRIPClient with parsing some NTRIP responses (missing sourcetable elements).

CHANGES:

1. GNSSMQTTClient add explicit LBand Frequencies topic (`"/pp/frequencies/Lb"`) argument (rather than defaulting to yes if mode is LBand).
1. New global variable `RTCMTYPES` listing message types and rates output in NTRIP caster mode.

### RELEASE 1.1.12

FIXES:

1. GNSSStreamer default input handler updated - Fixes [#111](https://github.com/semuconsulting/pygnssutils/issues/111)

CHANGES:

1. Inherit SocketWrapper from pynmeagps.

### RELEASE 1.1.11

ENHANCEMENTS:

1. Minor improvements to SSLError exception handling in gnssmqttclient.

### RELEASE 1.1.10

CHANGES:

1. Update minimum versions of pyubx2 (1.2.51), pynmeagps (1.0.49), pyrtcm (1.1.5) and certifi (2025.*.*) to ensure latest fixes and enhancements are included in UBX,  NMEA and RTCM3 processing.
1. No other functional changes.

### RELEASE 1.1.9

FIXES:

1. Fix `IndexError: list index out of range` error in `format_conn` on platforms with no IP6 support.

CHANGES:

1. ubx CLI utilities moved to `pyubxutils` - `ubxsave`, `ubxload`, `ubxcompare`, `ubxsetrate`, `ubxsimulator`. For the time being, `pyubxutils` will remain a dependency of `pygnssutils` and will be installed alongside it via pip, and `from pygnssutils import UBXSimulator` will still work as an import statement, but these will be removed altogether in v1.2.0.

### RELEASE 1.1.8

ENHANCEMENTS:

1. gnssmqttclient updated to support `pyspartn>=1.0.5` (see [pyspartn Release Notes](https://github.com/semuconsulting/pyspartn/blob/main/RELEASE_NOTES.md) for new functionality).

### RELEASE 1.1.7

ENHANCEMENTS:

1. gnssntripclient will now tolerate an NTRIP 1.0 response to an NTRIP 2.0 request if the caster only supports NTRIP 1.0, or vice versa.
1. gnssstreamer now supports both NTRIP 1.0 and NTRIP 2.0 clients via the `-rtkntripversion` flag (previously it assumed NTRIP 2.0).

### RELEASE 1.1.6

FIXES:

1. Remove print() statement.

### RELEASE 1.1.5

ENHANCEMENTS:

1. Enhance gnssntripclient exit and exception handling - Fixes #98.

### RELEASE 1.1.4

ENHANCEMENTS:

1. Fix UnicodeDecodeError in gnssntripclient - Fixes [#93](https://github.com/semuconsulting/pygnssutils/issues/93).
1. Fix occasional `ubxload` 'lockups' - Fixes [#48](https://github.com/semuconsulting/pygnssutils/issues/48).
1. Update `ubx...` utilities to use common logging provisions.
1. Drop active support for Python 3.8 - End of Life as at October 2024.
1. Update min pyubx2 version to 1.2.47.

### RELEASE 1.1.3

ENHANCEMENTS:

1. Refactor gnssserver keyword arguments to facilitate code completion hints.

### RELEASE 1.1.2

FIXES:

1. Fix [#90](https://github.com/semuconsulting/pygnssutils/issues/90)
1. Minor fix to verbosity setting passthrough to lower modules e.g. `pyubx2`.
1. Minor fix to stream validation in gnssstreamer.

### RELEASE 1.1.1

ENHANCEMENTS:

1. `gnssstreamer` (aka `gnssdump`) completely refactored to support bidirectional communications with GNSS datastream via args `--cliinput`, `--input` and `--clioutput`, `--output`. CLI utility is now named `gnssstreamer` but the deprecated `gnssdump` will continue to work until at least v1.1.3.

  Supported `--clioutput` values are:
  - 0 = terminal (default)
  - 1 = binary file
  - 2 = serial port
  - 3 = TCP socket server
  - 4 = evaluable Python (lamba) expression
  - 5 = text file
  
  Supported `--cliinput` values are:
  - 0 = none (default)
  - 1 = RTK NTRIP RTCM
  - 2 = RTK NTRIP SPARTN
  - 3 = RTK MQTT SPARTN
  - 4 = serial port (e.g. SPARTN RTK data from D9S L-Band receiver)
  - 5 = binary file (e.g file containing UBX configuration commands)

2. Improved test coverage.

### RELEASE 1.1.0

ENHANCEMENTS:

1. gnssntripclient now supports chunked transfer-encoded NTRIP datastreams.
1. gnssntripclient improved handling of NTRIP 1.0 casters.
1. gnssserver now supports NTRIP version 1.0 or 2.0 in NTRIP mode via arg `--ntripversion`.

### RELEASE 1.0.32

ENHANCEMENTS:

1. Add configuration file option to all CLI utilities via `-C` or `--config` argument. Default location of configuration file can be specified in environment variable `{utility}_CONF` e.g. `gnssstreamer_CONF`, `GNSSNTRIPCLIENT_CONF`, etc. Config files are text files containing key-value pairs which mirror the existing CLI arguments, e.g.
```shell
gnssstreamer -C gnssstreamer.conf
```
where gnssstreamer.conf contains...

    filename=pygpsdata-MIXED3.log
    verbosity=3
    format=2
    clioutput=1
    output=testfile.bin

is equivalent to: 
```shell
gnssstreamer --filename pygpsdata-MIXED3.log --verbosity 3 --format 2 --clioutput 1 --output testfile.bin
```
2. Streamline logging. CLI usage unchanged; to use pygnssutils logging within calling application, invoke `logging.getLogger("pygnssutils")` in calling module.
3. Internal enhancements to experimental UBXSimulator to add close() and in_waiting() methods; recognise incoming RTCM data.
4. GGA message sent to NTRIP Caster in GGALIVE mode will include additional live attributes (siv, hdop, quality, diffage, diffstation). Thanks to @yydgis for contribution.

FIXES:

1. gnssntripclient - update HTTP GET request for better NTRIP 2.0 compliance
1. issue with delay on gnssntripclient retry limit

### RELEASE 1.0.31

ENHANCEMENTS:

1. Minor internal enhancements to logging support - add explicit CRITICAL log level (verbosity = -1).
1. Add logging to socket_server.py module.

### RELEASE 1.0.30

ENHANCEMENTS:

1. Add automated network connection timeout and retry to gnssntripclient - new CLI arguments --retries, --retryinterval, --timeout. See gnssntripclient -h for help.
1. Add multi-client TCP socket server output option to gnssntripclient and gnssmqttclient - new CLI argument --cliout 3.
1. Refactor utilties to use standard Python logging module - --verbosity arguments are now mapped to logging levels (0 low => error, critical; 1 medium => warning; 2 high => info; 3 debug => debug). `--logtofile` CLI argument now contains fully qualified path to logfile, or "" to log to stderr; `--logpath` argument removed.
1. Refactor utilities to use separate *_cli.py module for command line argument parsing.

Use `-h` for help.

### RELEASE 1.0.29

ENHANCEMENTS:

1. Add --clioutput CLI option to gnssntripclient - supports output types of binary file or Serial port

### RELEASE 1.0.28

ENHANCEMENTS:

1. Fix waittime in ubxload - thanks to @hugokernel for contribution.

### RELEASE 1.0.27

ENHANCEMENTS:

1. Add `ubxcompare` CLI utility.

### RELEASE 1.0.26

FIXES:

1. Update SPARTN decryption argument names - Fixes no `decode` setting error.

### RELEASE 1.0.25

ENHANCEMENTS:

1. Add SPARTN payload decrypt option to gnssnmqqclient.
1. Minor internal streamlining.

### RELEASE 1.0.24

FIXES:

1. Further fixes to socket_server NTRIP caster to return properly formatted HTTP header with RTCM3 data stream.

### RELEASE 1.0.23

FIXES:

1. Fix to socket_server NTRIP caster source table HTTP response which was causing some NTRIP clients to timeout. Fixes [#60](https://github.com/semuconsulting/pygnssutils/issues/60)

### RELEASE 1.0.22

ENHANCEMENTS: 

1. Add support for u-blox PointPerfect NTRIP SPARTN service in gnssntripclient.

### RELEASE 1.0.21

ENHANCEMENTS: 

1. Add SSL support to gnssntripclient.

### RELEASE 1.0.20

FIXES:

1. Fix simvector function in ubxsimulator.

### RELEASE 1.0.19

CHANGES:

1. Add support for paho-mqtt v2.0.0.
1. Update min pyubx2 version to 1.2.38.
1. Add support for pyubx2 SETPOLL msgmode (auto-detect input message mode SET or POLL)

ENHANCEMENTS:

1. Add experimental UBX Simulator.

### RELEASE 1.0.18

CHANGES:

1. Update min pyubx2 version to 1.2.37.

### RELEASE 1.0.17

CHANGES:

1. Internal enhancements to IP6 address handling.
1. Update min pyubx2 version to 1.2.35

### RELEASE 1.0.16

CHANGES:

1. Update min pyubx2 version to 1.2.32

### RELEASE 1.0.15

ENHANCEMENTS:

1. GNSSMQTTClient updated to support SPARTN MQTT L-Band Topics (including `/pp/frequencies/Lb`) in addition to IP.
1. Add MQTTMessage container class for any MQTT topics which contain JSON payloads, e.g.,
```
<MQTT(/PP/FREQUENCIES/LB, frequencies_us_current_value=1556.29, frequencies_eu_current_value=1545.26)>
```

### RELEASE 1.0.14

CHANGES:

1. GNSSNTRIPClient amended to output sourcetable and closest mountpoint to designated output medium, if `--output` argument is not `None` and `--mountpoint` argument is blank. Previously only output RTCM3 data.

### RELEASE 1.0.13

CHANGES:

1. Add settings.setter methods to GNSSNTRIPClient and GNSSMQTTClient (to support saving settings in `PyGPSClient>=1.4.1` json configuration file). No functional changes to command line clients.

### RELEASE 1.0.12

CHANGES:

1. Add `ntripuser` and `ntrippassword` keyword arguments to `SockerServer`, `GNSSSockerServer` and `GNSSNTRIPClient` classes for use in NTRIP Caster authentication. If not supplied, these will default to environment variables `PYGPSCLIENT_USER` and `PYGPSCLIENT_PASSWORD` or, failing that, "anon" and "password". **NB:** these arguments were previously named `user` and `password` in `GNSSSockerServer` and `GNSSNTRIPClient` classes - any scripts instantiating either of these classes will require updating.
1. Updated minimum version dependency for pyubx2 (1.2.29)

### RELEASE 1.0.11

CHANGES:

1. Updated minimum version dependencies for pyubx2 (1.2.28) and pyspartn (0.1.10). No functional changes.

### RELEASE 1.0.10

1. Python 3.7 is officially end of life on 27 June 2023. This change removes Python 3.7 from workflows and documentation.
1. No other functional changes.

### RELEASE 1.0.9

FIXES:

1. Fix error when cycling log files [#29](https://github.com/semuconsulting/pygnssutils/issues/29)

### RELEASE 1.0.8

ENHANCEMENTS:

1. Add IPv6 support in gnssserver, gnssstreamer and gnssntripclient.
1. Add `on_disconnect` callback to `gnssmqttclient.py` and enhance exception reporting back to calling app.
1. Minor enhancements to SPARTN and NTRIP client exception handling.

### RELEASE 1.0.7

CHANGES:


1. Add bandit security analysis to workflows.
1. Other internal updates to VSCode and GitHub Actions workflows
1. Update min pyubx2 and pyspartn versions.
1. imports sorted using isort and black.

No functional changes.

### RELEASE 1.0.6

CHANGES:

1. superfluous haversine helper, latlon2dms and latlon2dmm methods removed - use pynmeagps helpers instead
1. Minimum pyubx2 version updated to 1.2.23
1. Minimum pyspartn version updated to 0.1.4
1. Minor updates to VSCode tasks and GitHub actions for pyproject.toml build framework

### RELEASE 1.0.5

FIXES:

1. Fix gnssserver crash - Fixes [#17](https://github.com/semuconsulting/pygnssutils/issues/17)

ENHANCEMENTS:

1. Enhance gnssstreamer.py msgfilter functionality to include periodic filtering = thanks to @acottuli for contribution.

### RELEASE 1.0.4

FIXES:

1. Add omitted dependency for paho-mqtt.

### RELEASE 1.0.3

ENHANCEMENTS:

1. `GNSSMQTTClient` SPARTN MQTT client class and command line utility added - see README for details

### RELEASE 1.0.2

CHANGES:

1. All CLI utilities amended to use standard Python `argparse` library for parsing input arguments. For example:

    - Previously: ```gnssstreamer port=/dev/tty.usbmodem1101 baud=115200 timeout=5```
    - Now: ```gnssstreamer --port /dev/tty.usbmodem1101 --baudrate 115200 --timeout 5```
    - For all CLI utilities, type ```-h``` for help. Refer to README for other examples.
    - The `kwargs` for the underlying Class constructors are unchanged.

### RELEASE 1.0.1

ENHANCEMENTS:

1. Add two new CLI utilities `ubxload` and `ubxsave` which allow user to save and reload the current configuration of a Gen 9+ UBX GNSS device. The `ubxsave`utility works by polling a complete set of CFG-VALGET keys from the UBX Configuration Database, converting the responses to CFG-VALSET commands and saving these as binary UBXMessages. The `ubxload` utility loads these CFG-VALSET messages from a file and uploads them to the receiver's volatile memory (RAM) memory layer. The two utilities provide an easy way to copy configurations between compatible devices.

### RELEASE 1.0.0

CHANGES:

1. First post-beta release; some internal streamlining.
2. Add `ubxsetrate` CLI utility to set message rates on u-blox receivers.

### RELEASE 0.3.4-beta

FIXES:

1. Fix error in `gnssntripclient` which was causing `HTTP 403 Forbidden` errors from some NTRIP casters (e.g. UNAVCO).

### RELEASE 0.3.3-beta

FIXES:

1. Fix gnssntripclient issue #6 arising from blank lines in HTTP sourcetable responses.

### RELEASE 0.3.2-beta

ENHANCEMENTS:

1. NTRIP client enhancement. `ggamode` keyword argument added to `gnssntripclient` - allows user to select GGA position source; 0 = live position from receiver, 1 = fixed reference position. Default is 0.

### RELEASE 0.3.1-beta

FIXES:

1. Fix to NTRIP V2 HTTP GET Header - thanks to @polytopes-design for contribution.

### RELEASE 0.3.0-beta

CHANGES:

1. `pyubx2.UBXReader` class used in place of `pygnssutils.GNSSReader` to eliminate code and test duplication.

### RELEASE 0.2.3-beta

ENHANCEMENTS:

1. Outfile option added to gnssstreamer. See README and `gnssstreamer -h` for details.

### RELEASE 0.2.2-beta

FIXES:

1. Fix typo error in formatGGA routine in gnssntripclient.py.
2. Fix \examples\rtk_example.py.

CHANGES:

1. Min versions of pyubx2 and pynmeagps updated to 1.2.14 and 1.0.14 respectively.

### RELEASE 0.2.1-beta

ENHANCEMENTS:

1. NTRIP Client class `GNSSNTRIPClient` and CLI utility `gnssntripclient` added. See README for details.

### RELEASE 0.2.0-beta

CHANGES

1. Output handler processing simplified.
1. Documentation updated.

FIXES:

1. JSON output now correct for all output handler types (not just stdout and File)

### RELEASE 0.1.2-alpha

ENHANCEMENTS:

1. JSON added to range of available output formats in gnssstreamer.
2. 'allhandler' protocol handler option added to gnssstreamer; Use same external protocol handler for all protocols. Will override any individual protocol handlers (ubxhandler etc.)
3. Context management added to GNSSStreamer and GNSSServer modules.
4. Documentation updated.

### RELEASE 0.1.1-alpha

CHANGES:

1. `GNSSServer` class renamed to `GNSSSocketServer` for clarity.
2. Test coverage extended.
3. Cosmetic documentation tidy up.

### RELEASE 0.1.0-alpha

1. Initial public release of combined Python 3 GNSS utility library which consolidates the common capabilities of three existing GNSS libraries: `pynmeagps` (NMEA), `pyubx2` (UBX) and `pyrtcm` (RTCM3)
2. `pynmeagps`, `pyubx2` and `pyrtcm` will continue to be developed as independent libraries for their respective GNSS protocols, but functionality which is common to all three - as well as other useful generic GNSS functions - will be incorporated into `pygnssutils`.
