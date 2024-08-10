# pygnssutils Release Notes

### RELEASE 1.0.32

ENHANCEMENTS:

1. Add configuration file option to all CLI utilities via `-C` or `--config` argument. Config files are text files containing key-value pairs which mirror the existing CLI arguments, e.g. 
```shell
gnssdump -C gnssdump.conf
```
where gnssdump.conf contains...

    filename=pygpsdata-MIXED3.log
    verbosity=3
    format=2
    clioutput=1
    output=testfile.bin

is equivalent to: 
```shell
gnssdump --filename pygpsdata-MIXED3.log --verbosity 3 --format 2 --clioutput 1 --output testfile.bin
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

1. Add IPv6 support in gnssserver, gnssdump and gnssntripclient.
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

1. Enhance gnssdump.py msgfilter functionality to include periodic filtering = thanks to @acottuli for contribution.

### RELEASE 1.0.4

FIXES:

1. Add omitted dependency for paho-mqtt.

### RELEASE 1.0.3

ENHANCEMENTS:

1. `GNSSMQTTClient` SPARTN MQTT client class and command line utility added - see README for details

### RELEASE 1.0.2

CHANGES:

1. All CLI utilities amended to use standard Python `argparse` library for parsing input arguments. For example:

    - Previously: ```gnssdump port=/dev/tty.usbmodem1101 baud=115200 timeout=5```
    - Now: ```gnssdump --port /dev/tty.usbmodem1101 --baudrate 115200 --timeout 5```
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

1. Outfile option added to gnssdump. See README and `gnssdump -h` for details.

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

1. JSON added to range of available output formats in gnssdump.
2. 'allhandler' protocol handler option added to gnssdump; Use same external protocol handler for all protocols. Will override any individual protocol handlers (ubxhandler etc.)
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
