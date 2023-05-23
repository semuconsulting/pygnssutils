# pygnssutils Release Notes

### RELEASE CANDIDATE 1.0.9

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
