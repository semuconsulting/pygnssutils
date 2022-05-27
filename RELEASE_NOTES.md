# pygnssutils Release Notes

### RELEASE CANDIDATE 0.1.2-alpha

ENHANCEMENTS:

1. JSON added to range of available output formats in gnssdump.

### RELEASE 0.1.1-alpha

CHANGES:

1. `GNSSServer` class renamed to `GNSSSocketServer` for clarity.
2. Test coverage extended.
3. Cosmetic documentation tidy up.

### RELEASE 0.1.0-alpha

1. Initial public release of combined Python 3 GNSS utility library which consolidates the common capabilities of three existing GNSS libraries: `pynmeagps` (NMEA), `pyubx2` (UBX) and `pyrtcm` (RTCM3)
2. `pynmeagps`, `pyubx2` and `pyrtcm` will continue to be developed as independent libraries for their respective GNSS protocols, but functionality which is common to all three - as well as other useful generic GNSS functions - will be incorporated into `pygnssutils`.
