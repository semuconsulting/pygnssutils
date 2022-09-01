# pygnssutils Release Notes

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
