pygnssutils
=======

[Current Status](#currentstatus) |
[Installation](#installation) |
[gnssstreamer CLI](#gnssstreamer) |
[gnssserver CLI](#gnssserver) |
[gnssntripclient CLI](#gnssntripclient) |
[gnssmqttclient CLI](#gnssmqttclient) |
[RTK Demonstration](#rtkdemo) |
[Troubleshooting](#troubleshooting) |
[Graphical Client](#gui) |
[Author & License](#author)

pygnssutils is an original series of Python GNSS utility classes and CLI tools built around the following core libraries from the same stable:

- [pyubx2](https://github.com/semuconsulting/pyubx2) - UBX parsing and generation library
- [pysbf2](https://github.com/semuconsulting/pysbf2) - SBF parsing and generation library
- [pynmeagps](https://github.com/semuconsulting/pynmeagps) - NMEA parsing and generation library
- [pyrtcm](https://github.com/semuconsulting/pyrtcm) - RTCM3 parsing library
- [pyspartn](https://github.com/semuconsulting/pyspartn) - SPARTN parsing library

Originally developed in support of the [PyGPSClient](https://github.com/semuconsulting/PyGPSClient) GUI GNSS application, the utilities provided by pygnssutils can also be used in their own right:

1. `GNSSStreamer` class and its associated [`gnssstreamer`](#gnssstreamer) (*formerly `gnssdump`*) CLI utility. This is essentially a configurable bidirectional input/output wrapper around the [`pyubx2.UBXReader`](https://github.com/semuconsulting/pyubx2#reading) class with flexible message formatting, filtering and output handling options for NMEA, UBX, SBF and RTCM3 protocols (**NB:** UBX and SBF protocols are mutually exclusive).
1. `GNSSSocketServer` class and its associated [`gnssserver`](#gnssserver) CLI utility. This implements a TCP Socket Server for GNSS data streams which is also capable of being run as a simple NTRIP Server/Caster.
1. `GNSSNTRIPClient` class and its associated [`gnssntripclient`](#gnssntripclient) CLI utility. This implements
a simple NTRIP Client which receives RTCM3 or SPARTN correction data from an NTRIP Server and (optionally) sends this to a
designated output stream.
1. `GNSSMQTTClient` class and its associated [`gnssmqttclient`](#gnssmqttclient) CLI utility. This implements
a simple SPARTN IP (MQTT) Client which receives SPARTN correction data from an SPARTN IP location service and (optionally) sends this to a
designated output stream.

The pygnssutils homepage is located at [https://github.com/semuconsulting/pygnssutils](https://github.com/semuconsulting/pygnssutils).

## <a name="currentstatus">Current Status</a>

![Status](https://img.shields.io/pypi/status/pygnssutils)
![Release](https://img.shields.io/github/v/release/semuconsulting/pygnssutils?include_prereleases)
![Build](https://img.shields.io/github/actions/workflow/status/semuconsulting/pygnssutils/main.yml?branch=main)
![Release Date](https://img.shields.io/github/release-date-pre/semuconsulting/pygnssutils)
![Last Commit](https://img.shields.io/github/last-commit/semuconsulting/pygnssutils)
![Contributors](https://img.shields.io/github/contributors/semuconsulting/pygnssutils.svg)
![Open Issues](https://img.shields.io/github/issues-raw/semuconsulting/pygnssutils)

Sphinx API Documentation in HTML format is available at [https://www.semuconsulting.com/pygnssutils](https://www.semuconsulting.com/pygnssutils).

Contributions welcome - please refer to [CONTRIBUTING.MD](https://github.com/semuconsulting/pygnssutils/blob/master/CONTRIBUTING.md).

[Bug reports](https://github.com/semuconsulting/pygnssutils/blob/master/.github/ISSUE_TEMPLATE/bug_report.md) and [Feature requests](https://github.com/semuconsulting/pygnssutils/blob/master/.github/ISSUE_TEMPLATE/feature_request.md) - please use the templates provided. For general queries and advice, post a message to one of the [pygnssutils Discussions](https://github.com/semuconsulting/pygnssutils/discussions) channels.

---
## <a name="installation">Installation</a>

![Python version](https://img.shields.io/pypi/pyversions/pygnssutils.svg?style=flat)
[![PyPI version](https://img.shields.io/pypi/v/pygnssutils.svg?style=flat)](https://pypi.org/project/pygnssutils/)
[![PyPI downloads](https://github.com/semuconsulting/pygpsclient/blob/master/images/clickpy_top10.svg?raw=true)](https://clickpy.clickhouse.com/dashboard/pygnssutils)

`pygnssutils` is compatible with Python 3.9-3.13.

In the following, `python3` & `pip` refer to the Python 3 executables. You may need to substitute `python` for `python3`, depending on your particular environment (*on Windows it's generally `python`*). **It is strongly recommended that** the Python 3 binaries (\Scripts or /bin) and site_packages directories are included in your PATH (*most standard Python 3 installation packages will do this automatically if you select the 'Add to PATH' option during installation*).

The recommended way to install the latest version of `pygnssutils` is with [pip](http://pypi.python.org/pypi/pip/):

```shell
python3 -m pip install --upgrade pygnssutils
```

If required, `pygnssutils` can also be installed into a virtual environment, e.g.:

```shell
python3 -m venv env
source env/bin/activate # (or env\Scripts\activate on Windows)
python3 -m pip install --upgrade pygnssutils
```

For [Conda](https://docs.conda.io/en/latest/) users, `pygnssutils` is also available from [conda forge](https://github.com/conda-forge/pygnssutils-feedstock):

[![Anaconda-Server Badge](https://anaconda.org/conda-forge/pygnssutils/badges/version.svg)](https://anaconda.org/conda-forge/pygnssutils)
[![Anaconda-Server Badge](https://img.shields.io/conda/dn/conda-forge/pygnssutils)](https://anaconda.org/conda-forge/pygnssutils)

```shell
conda install -c conda-forge pygnssutils
```

---
## <a name="gnssstreamer">GNSSStreamer and gnssstreamer CLI (*formerly gnssdump*)</a>

```
class pygnssutils.gnssstreamer.GNSSStreamer(**kwargs)
```

`gnssstreamer` (*formerly `gnssdump`*) is a command line utility for concurrent bidirectional communication with a GNSS datastream - typically a GNSS receiver. It supports NMEA, UBX, SBF, RTCM3, SPARTN, NTRIP and MQTT protocols.

**NB:** Currently, `gnsssstreamer` can parse data streams containing *either* UBX *or* SBF messages, but not both at the same time. If both are included in `protfilter`, UBX will take precedence over SBF.

- The CLI utility can acquire data from any one of the following sources:
   - `port`: serial port e.g. `COM3` or `/dev/ttyACM1` (can specify `--baudrate` and `--timeout`)
   - `filename`: fully qualified path to binary input file e.g. `/logs/logfile.bin`
   - `socket`: socket e.g. `192.168.0.72:50007` (port must be specified)
   - `stream`: any other instance of a stream class which implements a `read(n) -> bytes` method
- It offers a variety of data filtering options based on message protocol, identity and periodicity via the `--protfilter` and `--msgfilter` arguments e.g. `--protfilter 2 --msgfilter NAV-PVT(10)` will filter output to the UBX protocol and NAV-PVT message type and will limit NAV-PVT periodicity to 1 every 10 seconds. 
- It can format the filtered data via the `--format` argument:
   - 1 = parsed as object (e.g. `NMEAMessage`, `UBXMessage`) (default)
   - 2 = raw binary
   - 4 = hexadecimal string
   - 8 = tabulated hexadecimal
   - 16 = parsed as string
   - 32 = JSON

  or any OR'd combination thereof - e.g. `--format 9` outputs the parsed version of a UBX message alongside its tabular hexadecimal representation. 
- It can output the formatted and filtered data to a variety of output channels via the `--clioutput` and `--output` arguments:
   - 0 = stdout (terminal) (default)
   - 1 = file
   - 2 = serial
   - 3 = TCP socket server
   - 4 = Python lambda expression (*which could, for example, be used to format the output into a user-defined f-string*).
- It can also support a variety of concurrent input data sources via the `--cliinput` and `--input` arguments:
   - 0 = none (default)
   - 1 = RTK NTRIP RTCM caster
   - 2 = RTK NTRIP SPARTN caster
   - 3 = RTK MQTT SPARTN source (see [gnssmqttclient](#gnssmqttclient) for MQTT client configuration details)
   - 4 = serial port
   - 5 = binary file. 
  
  Data from these sources will be uploaded to the GNSS datastream *provided* this datastream supports `write()` operations. A principal use case for this input facility is to monitor a GNSS receiver's output while processing incoming RTK correction data via pygnssutil's in-built NTRIP or MQTT (SPARTN IP) clients or a RXM-PMP (SPARTN L-Band) serial stream. Alternatively, binary file input could, for example, contain a series of UBX CFG-* configuration commands to be applied to a u-blox receiver.

For help and full list of optional arguments, type:

```shell
gnssstreamer -h
```

Command line arguments can be stored in a configuration file and invoked using the `-C` or `--config` argument. The location of the configuration file can be set in environment variable `GNSSSTREAMER_CONF`.

`gnssstreamer` can be run as a systemd service on Linux servers - see [Install gnssstreamer as service](#gnssstreamerservice).

`GNSSStreamer` - the underlying Python class of `gnssstreamer` - is essentially a configurable input/output wrapper around the [`pyubx2.UBXReader`](https://github.com/semuconsulting/pyubx2#reading) class which can be used within Python scripts. It supports custom input and output handlers via user-defined callback functions.

Refer to the [Sphinx API documentation](https://www.semuconsulting.com/pygnssutils/pygnssutils.html#module-pygnssutils.gnssstreamer) for further details.

### CLI Examples:

Assuming the Python 3 scripts (bin) directory is in your PATH, the CLI utility may be invoked from the shell thus:

### 1. Serial input from receiver with output passed to Python lambda expression:

```shell
gnssstreamer --port /dev/ttyACM1 --baudrate 9600 --timeout 5 --quitonerror 1 --protfilter 1 --msgfilter GNGGA --clioutput 4 --output "lambda msg: print(f'lat: {msg.lat}, lon: {msg.lon}')"
```
```
lat: 37.23345, lon: -115.81512
lat: 37.23347, lon: -115.81515
lat: 37.23343, lon: -115.81513
```

### 2. File input with output to terminal in parsed and tabulated hexadecimal formats:

(`--clioutput 0` is the default, so this argument could be omitted):

```shell
gnssstreamer --filename pygpsdata.log --quitonerror 2 --format 9 --clioutput 0 --verbosity 2
```
```
2024-08-15 09:31:48.68 - INFO - pygnssutils.gnssstreamer - Parsing GNSS data stream from file: <_io.BufferedReader name='pygpsdata.log'>...

<UBX(NAV-STATUS, iTOW=09:47:37, gpsFix=3, gpsFixOk=1, diffSoln=0, wknSet=1, towSet=1, diffCorr=0, carrSolnValid=1, mapMatching=0, psmState=0, spoofDetState=1, carrSoln=0, ttff=33377, msss=1912382)>
000: b562 0103 1000 f80c da1b 03dd 0208 6182  | b'\xb5b\x01\x03\x10\x00\xf8\x0c\xda\x1b\x03\xdd\x02\x08a\x82' |
016: 0000 3e2e 1d00 633d                      | b'\x00\x00>.\x1d\x00c=' |

<UBX(NAV-DOP, iTOW=09:47:37, gDOP=1.55, pDOP=1.32, tDOP=0.8, vDOP=1.11, hDOP=0.72, nDOP=0.59, eDOP=0.42)>
000: b562 0104 1200 f80c da1b 9b00 8400 5000  | b'\xb5b\x01\x04\x12\x00\xf8\x0c\xda\x1b\x9b\x00\x84\x00P\x00' |
016: 6f00 4800 3b00 2a00 9b75                 | b'o\x00H\x00;\x00*\x00\x9bu' |

<UBX(NAV-TIMEGPS, iTOW=09:47:37, fTOW=422082, week=2216, leapS=18, towValid=1, weekValid=1, leapSValid=1, tAcc=10)>
000: b562 0120 1000 f80c da1b c270 0600 a808  | b'\xb5b\x01 \x10\x00\xf8\x0c\xda\x1b\xc2p\x06\x00\xa8\x08' |
016: 1207 0a00 0000 3566                      | b'\x12\x07\n\x00\x00\x005f' |
```

### 3. Socket input with output to terminal in JSON format:

```shell
gnssstreamer --socket 192.168.0.20:50010 --format 32 --msgfilter 1087 --verbosity 2
```
```
2024-08-15 09:31:48.68 - INFO - pygnssutils.gnssstreamer - Parsing GNSS data stream from: <socket.socket fd=3, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 57399), raddr=('127.0.0.1', 50010)>...

{"class": "<class 'pyrtcm.rtcmmessage.RTCMMessage'>", "identity": "1087", "payload": {"DF002": 1087, "DF003": 0, "GNSSEpoch": 738154640, "DF393": 1, "DF409": 0, "DF001_7": 0, "DF411": 0, "DF412": 0, "DF417": 0, "DF418": 0, "DF394": 1152921504606846976, "NSat": 1, "DF395": 1073741824, "NSig": 1, "DF396": 1, "DF405_01": 0.00050994, "DF406_01": 0.00194752, "DF407_01": 102, "DF420_01": 0, "DF408_01": 0, "DF404_01": 0.5118}},...]
```

### 4. Serial input with output to socket server using remote instances of gnssstreamer as socket clients:

**gnssstreamer as socket server:**

```shell
gnssstreamer --port /dev/tty.usbmodem101 --clioutput 3 --output 192.168.0.27:50011 --format 2 --verbosity 2
```
```
2024-08-15 09:00:04.769 - INFO - pygnssutils.gnssstreamer - Parsing GNSS data stream from: Serial<id=0x1016467a0, open=True>(port='/dev/tty.usbmodem101', baudrate=38400, bytesize=8, parity='N', stopbits=1, timeout=3, xonxoff=False, rtscts=False, dsrdtr=False)...
2024-08-15 09:00:09.952 - INFO - pygnssutils.socket_server - client ('192.168.0.58', 57964) has connected
2024-08-15 09:00:23.839 - INFO - pygnssutils.socket_server - client ('192.168.0.36', 57968) has connected
2024-08-15 09:00:34.29 - INFO - pygnssutils.socket_server - client ('192.168.0.36', 57968) has disconnected
2024-08-15 09:00:36.37 - INFO - pygnssutils.socket_server - client ('192.168.0.58', 57964) has disconnected
^C2024-08-15 09:00:35.196 - INFO - pygnssutils.gnssstreamer - Messages input:    {'NAV-DOP': 8, 'NAV-PVT': 31, 'NAV-SAT': 8}
2024-08-15 09:00:35.197 - INFO - pygnssutils.gnssstreamer - Messages filtered: {}
2024-08-15 09:00:35.197 - INFO - pygnssutils.gnssstreamer - Messages output:   {'NAV-DOP': 8, 'NAV-PVT': 31, 'NAV-SAT': 8}
2024-08-15 09:00:35.197 - INFO - pygnssutils.gnssstreamer - Streaming terminated, 47 messages processed with 0 errors.
```

**gnssstreamer as socket client:**

```shell
gnssstreamer -S 192.168.0.27:50011
```
```
<UBX(NAV-PVT, iTOW=07:56:45, year=2024, month=8, day=15, hour=7, min=56, second=45, validDate=1, validTime=1, fullyResolved=1, validMag=0, tAcc=27, nano=376074, fixType=3, gnssFixOk=1, diffSoln=0, psmState=0, headVehValid=0, carrSoln=0, confirmedAvai=1, confirmedDate=1, confirmedTime=1, numSV=30, lon=-115.81512, lat=37.23345, height=5278, hMSL=5264, hAcc=2840, vAcc=2527, velN=-5, velE=-7, velD=8, gSpeed=8, headMot=0.0, sAcc=223, headAcc=180.0, pDOP=0.91, invalidLlh=0, lastCorrectionAge=0, reserved0=1044570318, headVeh=0.0, magDec=0.0, magAcc=0.0)>
...
```

### 5. Serial input with concurrent NTRIP RTK input, outputting to Python lambda expression:

(in this example, `gnssstreamer` will pass NMEA GGA data back to the NTRIP caster every 10 seconds)

```shell
gnssstreamer --port /dev/tty.usbmodem101 --msgfilter "GNGGA" --cliinput 1 --input "http://rtk2go.com:2101/MYMOUNTPOINT" --rtkuser myusername@mydomain.com --rtkpassword mypassword --rtkggaint 10 --clioutput 4 --output "lambda msg: print(f'lat: {msg.lat}, lon: {msg.lon}, alt: {msg.alt}, fix: {['NO FIX','2D','3D','N/A','RTK FIXED','RTK FLOAT'][msg.quality]}, corr age: {msg.diffAge}')"
```
```
lat: 37.2306465, lon: -115.8102969, alt: 2.505, fix: 3D, corr age:
lat: 37.2306464, lon: -115.8102969, alt: 2.502, fix: 3D, corr age:
...
lat: 37.2306447, lon: -115.8102895, alt: 2.929, fix: 3D, corr age: 2.0
lat: 37.2306462, lon: -115.8102946, alt: 1.373, fix: RTK FLOAT, corr age: 3.0
lat: 37.2306465, lon: -115.8102957, alt: 1.022, fix: RTK FLOAT, corr age: 2.0
...
lat: 37.2306502, lon: -115.8102974, alt: 1.025, fix: RTK FLOAT, corr age: 2.0
lat: 37.2306763, lon: -115.8103495, alt: 1.027, fix: RTK FIXED, corr age: 2.0
lat: 37.2306762, lon: -115.8103495, alt: 1.026, fix: RTK FIXED, corr age: 2.0
```

### 6. Serial input with concurrent binary configuration file input:

(in this example the `f9pconfig.ubx` file contains a series of UBX CFG-MSG commands which disable NMEA messages and enable UBX messages)

```shell
gnssstreamer --port /dev/tty.usbmodem101 --cliinput 5 --input f9pconfig.ubx --verbosity 2
```
```
2024-09-05 07:39:33.886 - INFO - pygnssutils.gnssstreamer - Starting GNSS reader/writer using Serial<id=0x104cddb70, open=True>(port='/dev/tty.usbmodem101', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=3, xonxoff=False, rtscts=False, dsrdtr=False)...
<NMEA(GNRMC, time=06:39:34, status=A, lat=37.2306246667, NS=N, lon=-115.8103376667, EW=W, spd=0.055, cog=, date=2024-09-05, mv=, mvEW=, posMode=A, navStatus=V)>
2024-09-05 07:39:34.32 - INFO - pygnssutils.gnssstreamer - Data input: b'\xb5b\x06\x01\x08\x00\xf0\n\x00\x00\x00\x00\x00\x00\ti'
...
2024-09-05 07:39:34.35 - INFO - pygnssutils.gnssstreamer - Data input: b'\xb5b\x06\x01\x08\x00\x01\x11\x00\x00\x00\x00\x00\x00!"'
<NMEA(GNGLL, lat=37.2306246667, NS=N, lon=-115.8103376667, EW=W, time=06:39:34, status=A, posMode=A)>
<UBX(ACK-ACK, clsID=CFG, msgID=CFG-MSG)>
<UBX(ACK-NAK, clsID=CFG, msgID=CFG-MSG)>
...
<UBX(ACK-ACK, clsID=CFG, msgID=CFG-MSG)>
<UBX(NAV-PVT, iTOW=06:39:35, year=2024, month=9, day=5, hour=6, min=39, second=35, validDate=1, validTime=1, fullyResolved=1, validMag=0, tAcc=32, nano=386888, fixType=3, gnssFixOk=1, diffSoln=0, psmState=0, headVehValid=0, carrSoln=0, confirmedAvai=1, confirmedDate=1, confirmedTime=1, numSV=10, lon=-115.8103373, lat=37.8106243, height=101139, hMSL=52655, hAcc=3317, vAcc=3070, velN=10, velE=20, velD=62, gSpeed=22, headMot=0.0, sAcc=300, headAcc=180.0, pDOP=1.89, invalidLlh=0, lastCorrectionAge=0, reserved0=1044570318, headVeh=0.0, magDec=0.0, magAcc=0.0)>
...
Messages input:    {'ACK-ACK': 46, 'ACK-NAK': 24, 'GAGSV': 1, 'GBGSV': 1, 'GLGSV': 3, 'GNGGA': 1, 'GNGLL': 1, 'GNGSA': 5, 'GNRMC': 1, 'GNVTG': 1, 'GPGSV': 3, 'GQGSV': 1, 'NAV-DOP': 1, 'NAV-PVT': 3, 'NAV-SAT': 1}
Messages filtered: {}
Messages output:   {'ACK-ACK': 46, 'ACK-NAK': 24, 'GAGSV': 1, 'GBGSV': 1, 'GLGSV': 3, 'GNGGA': 1, 'GNGLL': 1, 'GNGSA': 5, 'GNRMC': 1, 'GNVTG': 1, 'GPGSV': 3, 'GQGSV': 1, 'NAV-DOP': 1, 'NAV-PVT': 3, 'NAV-SAT': 1}
Streaming terminated, 93 messages processed with 0 errors.
```

### <a name="gnssstreamerservice">Installing gnssstreamer as a systemd service on Linux</a>

This example should work for most Linux distributions running `systemd` and `python3>=3.8`, including Raspberry Pi OS (*substitute `dnf` for `apt` as necessary*).

The example `gnssstreamer.conf` file will set up `gnssstreamer` as a multi-client TCP socket server accessible on `hostip:50012` (*check TCP port 50012 is allowed through any active firewall*).

1. Install `pygnssutils` into a virtual environment as follows:

```shell
cd ~ # or a base directory of your choice
sudo apt install python3-virtualenv # if not already installed
python3 -m virtualenv pygnssutils
source pygnssutils/bin/activate
python3 -m pip install --upgrade pygnssutils
deactivate
```

2. Copy the example [`gnssstreamer.conf`](https://github.com/semuconsulting/pygnssutils/tree/main/examples/gnssstreamer.conf) and [`gnssstreamer.service`](https://github.com/semuconsulting/pygnssutils/tree/main/examples/gnssstreamer.service) files to the host machine and edit them according to your preferred configuration. If installed as above, `Environment=GNSSSTREAMER_CONF=/home/username/gnssstreamer.conf` and `ExecStart=/home/username/pygnssutils/bin/gnssstreamer`.
3. Run the following shell commands and verify the status:

```shell
sudo cp gnssstreamer.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable gnssstreamer.service
sudo systemctl start gnssstreamer.service
systemctl status gnssstreamer.service # look for 'enabled' and 'active (running)'
```

## <a name="gnssserver">GNSSSocketServer and gnssserver CLI</a>

```
class pygnssutils.gnssserver.GNSSSocketServer(**kwargs)
```

`GNSSSocketServer` is essentially a wrapper around the `GNSSStreamer` and `SocketServer` classes (the latter based on the native Python `ThreadingTCPServer` framework) which uses queues to transport data between the two classes.

### CLI Usage - Default Mode:

In its default configuration (`ntripmode=0`) `gnssserver` acts as an open, unauthenticated CLI TCP socket server, reading the binary data stream from a host-connected GNSS receiver and broadcasting the data to any local or remote TCP socket client capable of parsing binary GNSS data.

It supports most of `gnssstreamer`'s formatting capabilities and could be configured to output a variety of non-binary formats (including, for example, JSON or hexadecimal), but the client software would need to be capable of parsing data in such formats.

Assuming the Python 3 scripts (bin) directory is in your PATH, the CLI utility may be invoked from the shell thus:

```shell
gnssserver --inport "/dev/tty.usbmodem101" --baudrate 115200 --hostip 192.168.0.27 --outport 50012 --verbosity 2
```
```
2024-08-15 09:12:25.443 - INFO - pygnssutils.gnssserver - Starting server (type CTRL-C to stop)...
2024-08-15 09:12:25.443 - INFO - pygnssutils.gnssserver - Starting input thread, reading from /dev/tty.usbmodem101...
2024-08-15 09:12:25.461 - INFO - pygnssutils.gnssstreamer - Parsing GNSS data stream from: Serial<id=0x103966e60, open=True>(port='/dev/tty.usbmodem101', baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=3, xonxoff=False, rtscts=False, dsrdtr=False)...
2024-08-15 09:12:25.949 - INFO - pygnssutils.gnssserver - Starting output thread, broadcasting on 192.168.0.27:50012...
2024-08-15 09:12:36.953 - INFO - pygnssutils.gnssserver - Client ('192.168.0.34', 58207) has connected. Total clients: 1
2024-08-15 09:12:43.35 - INFO - pygnssutils.gnssserver - Client ('192.168.0.34', 58207) has disconnected. Total clients: 0
```

`gnssserver` can be run as a daemon process (or even a service) but note that abrupt termination (i.e. without invoking the internal `server.shutdown()` method) may result in the designated TCP socket port being unavailable for a short period - this is operating system dependant.

Command line arguments can be stored in a configuration file and invoked using the `-C` or `--config` argument. The location of the configuration file can be set in environment variable `GNSSSERVER_CONF`.

For help and full list of optional arguments, type:

```shell
gnssserver -h
```

Refer to the [Sphinx API documentation](https://www.semuconsulting.com/pygnssutils/pygnssutils.html#module-pygnssutils.gnssserver) for further details.

### CLI Usage - NTRIP Mode:

`gnssserver` can also be configured to act as a single-mountpoint NTRIP Server/Caster (`ntripmode=1`), broadcasting RTCM3 RTK correction data to any authenticated NTRIP client on the standard 2101 port using the mountpoint name `pygnssutils` (**NB**: to use with standard NTRIP clients, output format must be set to binary (2) - this is the default, so the argument can be omitted): 

```shell
gnssserver --inport "/dev/tty.usbmodem14101" --hostip 192.168.0.27 --outport 2101 --ntripmode 1 --protfilter 4 --format 2 --ntripuser myuser --ntrippassword mypassword --verbosity 2
```

**NOTE THAT** this configuration is predicated on the host-connected receiver being an RTK-capable device (e.g. the u-blox ZED-F9P) operating in 'Base Station' mode (either 'SURVEY_IN' or 'FIXED') and outputting the requisite RTCM3 RTK correction messages (1005, 1077, 1087, 1097, 1127, 1230). NTRIP server login credentials are set via command line arguments or environment variables `PYGPSCLIENT_USER` and `PYGPSCLIENT_PASSWORD`. 

### Clients

`gnssserver` will work with any client capable of parsing binary GNSS data from a TCP socket. Suitable clients include, *but are not limited to*:

1) (in default mode) pygnssutils's `gnssstreamer` cli utility invoked thus:

```shell
gnssstreamer --socket hostip:outport
```

2) (in NTRIP mode) Any standard NTRIP client, including BKG's [NTRIP client (BNC)](https://igs.bkg.bund.de/ntrip/download), ublox's [legacy ucenter NTRIP client](https://www.u-blox.com/en/product/u-center), or pygnssutil's `gnssntripclient` cli utility invoked thus:

```shell
gnssntripclient -S hostip -P 2101 -M pygnssutils --ntripuser myuser --ntrippassword mypassword --verbosity 2
```

3) The [PyGPSClient GUI](https://github.com/semuconsulting/PyGPSClient?tab=readme-ov-file#ntripconfig) application.

---
## <a name="gnssntripclient">GNSSNTRIPClient and gnssntripclient CLI</a>
 
```
class pygnssutils.gnssntripclient.GNSSNTRIPClient(app=None, **kwargs)
```

The `GNSSNTRIPClient` class provides a basic NTRIP Client capability and forms the basis of a [`gnssntripclient`](#gnssntripclient) CLI utility. It receives RTCM3 or SPARTN correction data from an NTRIP server and (optionally) sends this to a designated output stream. NTRIP server login credentials are set via command line arguments or environment variables `PYGPSCLIENT_USER` and `PYGPSCLIENT_PASSWORD`.

### CLI Usage:

Assuming the Python 3 scripts (bin) directory is in your PATH, the CLI utility may be invoked from the shell thus:

To retrieve the sourcetable and determine the closest available mountpoint to the reference lat/lon, leave the mountpoint argument blank (the port defaults to 2101):

```shell
gnssntripclient --server rtk2go.com --port 2101 --https 0 --datatype RTCM --ntripversion 2.0 --ggainterval -1 --reflat 37.23 --reflon 115.81 --ntripuser myuser --ntrippassword mypassword --verbosity 2
```
```
2024-08-15 09:22:21.174 - INFO - pygnssutils.gnssntripclient - Closest mountpoint to reference location(37.23, 115.81) = MYBASE, 313.65 km.
2024-08-15 09:22:21.176 - INFO - pygnssutils.gnssntripclient - Complete sourcetable follows...
[['ACAKO', 'Kovin', 'RTCM 3.2', '1005(30),1074(1),1084(1),1094(1)', '2', 'GPS+GLO+GAL', 'SNIP', 'SRB', '44.75', '21.01', '1', '0', 'sNTRIP', 'none', 'B', 'N', '3200', ''], ['ACASU', 'Subotica', 'RTCM 3.2', '1005(30),1074(1),1084(1),1094(1)', '2', 'GPS+GLO+GAL', 'SNIP', 'SRB', '46.06', '19.52', '1', '0', 'sNTRIP', 'none', 'B', 'N', '3360', ''], ['ADS-SAH', 'Ciudad Real', 'RTCM 3.2', '1005(1),1074(1),1084(1),1094(1),1230(1)', '', 'GPS+GLO+GAL', 'SNIP', 'ESP', '39.05', '-4.06', '1', '0', 'sNTRIP', 'none', 'B', 'N', '0', ''], [['AGSSIAAP', 'Acheres', 'RTCM 3.0', '1004(1),1006(13),1012(1),1033(31)', '2', 'GPS+GLO', 'SNIP', 'FRA', '48.97', '2.17', '1', '0', 'sNTRIP', 'none', 'N', 'N', '2540', '']
...
```

To retrieve correction data from a designated mountpoint (this will send NMEA GGA position sentences to the server at intervals of 60 seconds, based on the supplied reference lat/lon):

```shell
gnssntripclient --server rtk2go.com --port 2101 --https 0 --mountpoint MYBASE --datatype RTCM --ggainterval 60 --reflat 37.23 --reflon 115.81 --ntripuser myuser --ntrippassword mypassword --verbosity 2
```
```
2024-08-15 09:24:34.872 - INFO - pygnssutils.gnssntripclient - Streaming RTCM data from rtk2go.com:2101/MYBASE ...
2024-08-15 09:24:35.897 - INFO - pygnssutils.gnssntripclient - RTCMMessage received: 1019
2024-08-15 09:24:35.898 - INFO - pygnssutils.gnssntripclient - RTCMMessage received: 1020
2024-08-15 09:24:35.898 - INFO - pygnssutils.gnssntripclient - RTCMMessage received: 1042
...
```

Command line arguments can be stored in a configuration file and invoked using the `-C` or `--config` argument. The location of the configuration file can be set in environment variable `GNSSNTRIPCLIENT_CONF`.

For help and full list of optional arguments, type:

```shell
gnssntripclient -h
```

Refer to the [Sphinx API documentation](https://www.semuconsulting.com/pygnssutils/pygnssutils.html#module-pygnssutils.gnssntripclient) for further details.

---
## <a name="gnssmqttclient">GNSSMQTTClient and gnssmqttclient CLI</a>
```
class pygnssutils.gnssmqttclient.GNSSMQTTClient(app=None, **kwargs)
```

The `GNSSMQTTClient` class provides a basic SPARTN IP (MQTT) Client capability and forms the basis of a [`gnssmqttclient`](#gnssmqttclient) CLI utility. It receives RTK correction data from a SPARTN IP (MQTT) location service (e.g. the u-blox / Thingstream PointPerfect service) and (optionally) sends this to a designated output stream.

### CLI Usage:

The `clientid` provided by the location service may be set as environment variable `MQTTCLIENTID`. If this environment variable is set and the TLS certificate (\*.crt) and key (\*.pem) files provided by the location service are placed in the user's `HOME` directory, the utility can use these as default settings and may be invoked without any arguments.

Assuming the Python 3 scripts (bin) directory is in your PATH, the CLI utility may be invoked from the shell thus (press CTRL-C to terminate):

```shell
gnssmqttclient --clientid yourclientid --server pp.services.u-blox.com --port 8883 --region eu --mode 0 --topic_ip 1 --topic_mga 1 --topic_key 1 --tlscrt '/Users/{your-user}/device-{your-clientid}-pp-cert.crt' --tlskey '/Users/{your-user}/device-{your-client-id}-pp-key.pem'} --spartndecode 0 --clioutput 0 --verbosity 2
```
```
2024-08-15 09:14:50.544 - INFO - pygnssutils.gnssmqttclient - Starting MQTT client with arguments {'server': 'pp.services.u-blox.com', 'port': 8883, 'clientid': 'your-client-id', 'region': 'eu', 'mode': 0, 'topic_ip': 1, 'topic_mga': 1, 'topic_key': 1, 'tlscrt': '/Users/myuser/device-your-client-id-pp-cert.crt', 'tlskey': '/Users/myuser/device-your-client-id-pp-key.pem', 'spartndecode': 0, 'output': None}.
2024-08-15 09:14:50.840 - INFO - pygnssutils.gnssmqttclient - RXM-SPARTN-KEY
2024-08-15 09:14:50.854 - INFO - pygnssutils.gnssmqttclient - MGA-INI-TIME-UTC
2024-08-15 09:14:50.858 - INFO - pygnssutils.gnssmqttclient - MGA-GPS-EPH
...
```

Command line arguments can be stored in a configuration file and invoked using the `-C` or `--config` argument. The location of the configuration file can be set in environment variable `GNSSMQTTCLIENT_CONF`.

For help and full list of optional arguments, type:

```shell
gnssmqttclient -h
```

Refer to the [pyspartn documentation](https://github.com/semuconsulting/pyspartn?tab=readme-ov-file#reading) for further details on decrypting encrypted (`eaf=1`) SPARTN payloads.

---
## <a name="rtkdemo">NTRIP RTK demonstration using `gnssserver` and `gnssntripclient`</a>

Assuming your host is connected to an RTK-capable receiver (e.g. ZED-F9P) operating in Base Station mode (see [configuring base station](https://github.com/semuconsulting/pyubx2/blob/master/examples/f9p_basestation.py)), you can run `gnssserver` as a local NTRIP caster and `gnssntripclient` as a remote NTRIP client. You may have to amend your firewall settings to make the caster available outside your local LAN. *This configuration is only recommended for personal testing and diagnostic purposes and not for production use*.

### NTRIP Caster - `gnssserver`
```shell
gnssserver --inport /dev/ttyACM1 --baudrate 38400 --format 2 --protfilter 4 --hostip 192.168.0.27 --outport 2101 --ntripmode 1 --ntripversion 2.0 --ntripuser youruser --ntrippassword yourpassword --verbosity 2
```
```
2024-08-23 10:12:00.239 - INFO - pygnssutils.gnssserver - Starting server (type CTRL-C to stop)...
2024-08-23 10:12:00.239 - INFO - pygnssutils.gnssserver - Starting input thread, reading from /dev/ttyACM1...
2024-08-23 10:12:00.256 - INFO - pygnssutils.gnssstreamer - Parsing GNSS data stream from: Serial<id=0x1016039d0, open=True>(port='/dev/ttyACM1', baudrate=38400, bytesize=8, parity='N', stopbits=1, timeout=3, xonxoff=False, rtscts=False, dsrdtr=False)...
2024-08-23 10:12:00.744 - INFO - pygnssutils.gnssserver - Starting output thread, broadcasting on 192.168.0.27:2101...
2024-08-23 10:12:45.7 - INFO - pygnssutils.gnssserver - Client ('192.168.0.54', 60783) has connected. Total clients: 1
2024-08-23 10:12:48.10 - INFO - pygnssutils.gnssserver - Client ('192.168.0.54', 60783) has disconnected. Total clients: 0
...etc.
^C2024-08-23 10:14:12.834 - INFO - pygnssutils.gnssserver - Stopping server...
2024-08-23 10:14:12.835 - INFO - pygnssutils.gnssstreamer - Messages input:    {'1005': 132, '1077': 132, '1087': 132, '1097': 132, '1127': 132, '1230': 132, '4072': 132, 'NAV-DOP': 132, 'NAV-PVT': 132, 'NAV-SAT': 33, 'NAV-SVIN': 132}
2024-08-23 10:14:12.835 - INFO - pygnssutils.gnssstreamer - Messages filtered: {'NAV-DOP': 132, 'NAV-PVT': 132, 'NAV-SAT': 33, 'NAV-SVIN': 132}
2024-08-23 10:14:12.835 - INFO - pygnssutils.gnssstreamer - Messages output:   {'1005': 132, '1077': 132, '1087': 132, '1097': 132, '1127': 132, '1230': 132, '4072': 132}
2024-08-23 10:14:12.835 - INFO - pygnssutils.gnssstreamer - Streaming terminated, 924 messages processed with 0 errors.
2024-08-23 10:14:13.204 - INFO - pygnssutils.gnssserver - Server shutdown.
```

### NTRIP Client - `gnssntripclient`
```shell
gnssntripclient --server 192.168.0.27 --port 2101 --https 0 --mountpoint pygnssutils --ntripversion 2.0 --ntripuser youruser --ntrippassword yourpassword --verbosity 2
```
```
2024-08-23 10:12:45.8 - INFO - pygnssutils.gnssntripclient - Streaming rtcm data from 192.168.0.27:2101/pygnssutils ...
2024-08-23 10:12:45.8 - INFO - pygnssutils.gnssntripclient - Message received: 1097
2024-08-23 10:12:45.9 - INFO - pygnssutils.gnssntripclient - Message received: 1127
2024-08-23 10:12:45.9 - INFO - pygnssutils.gnssntripclient - Message received: 1230
2024-08-23 10:12:45.47 - INFO - pygnssutils.gnssntripclient - Message received: 1005
2024-08-23 10:12:46.8 - INFO - pygnssutils.gnssntripclient - Message received: 4072
2024-08-23 10:12:46.12 - INFO - pygnssutils.gnssntripclient - Message received: 1077
2024-08-23 10:12:46.13 - INFO - pygnssutils.gnssntripclient - Message received: 1087
2024-08-23 10:12:46.13 - INFO - pygnssutils.gnssntripclient - Message received: 1097
2024-08-23 10:12:46.13 - INFO - pygnssutils.gnssntripclient - Message received: 1127
...etc.
^C2024-08-23 10:12:47.480 - INFO - pygnssutils.gnssntripclient - Disconnected
```

---
## <a name="troubleshooting">Troubleshooting</a>

1. `SPARTNTypeError` or `SPARTNParseError` when parsing encrypted messages with 16-bit gnssTimetags (`timeTagtype=0`), e.g. GAD or some OCB messages:

   ```
   pyspartn.exceptions.SPARTNTypeError: Error processing attribute 'group' in message type SPARTN-1X-GAD
   ```

   This is almost certainly due to an invalid decryption key and/or basedate. Remember that keys are only valid for a 4 week period, and basedates are valid for no more than half a day. Note also that different GNSS constellations use different UTC datums e.g. GLONASS timestamps are based on UTC+3. Check with your SPARTN service provider for the latest decryption key(s), and check the original creation date of your SPARTN datasource.

1. `SSL: CERTIFICATE_VERIFY_FAILED` error when attempting to connect to SPARTN MQTT service using `gnssmqttclient` on MacOS:

   ```
   [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1000)
   ```

   This is because `gnssmqttclient` is unable to locate the RootCA certificate for the MQTT Broker. This can normally be resolved as follows:
   - Install the latest version of certifi: ```python3 -m pip install --upgrade certifi```
   - Run the following command from the terminal (_substituting your Python path and version as required_): ```/Applications/Python\ 3.12/Install\ Certificates.command```


1. Unable to install `cryptography` library required by `pyspartn` on 32-bit Linux platforms:

   ```
   Building wheel for cryptography (PEP 517): started
   Building wheel for cryptography (PEP 517): finished with status 'error'
   ```

   Refer to [cryptography installation README.md](https://github.com/semuconsulting/pyspartn/blob/main/cryptography_installation/README.md).


---
## <a name="gui">Graphical Client</a>

A python/tkinter graphical GPS client which utilises the `pygnssutils` library and supports NMEA, UBX, RTCM3 and NTRIP protocols is available at: 

[https://github.com/semuconsulting/PyGPSClient](https://github.com/semuconsulting/PyGPSClient)


---
## <a name="author">Author & License Information</a>

semuadmin@semuconsulting.com

![License](https://img.shields.io/github/license/semuconsulting/pygnssutils.svg)

`pygnssutils` is maintained entirely by unpaid volunteers. It receives no funding from advertising or corporate sponsorship. If you find the utility useful, please consider sponsoring the project with the price of a coffee...

[![Sponsor](https://github.com/semuconsulting/pyubx2/blob/master/images/sponsor.png?raw=true)](https://buymeacoffee.com/semuconsulting)

[![Freedom for Ukraine](https://github.com/semuadmin/sandpit/blob/main/src/sandpit/resources/ukraine200.jpg?raw=true)](https://u24.gov.ua/)
