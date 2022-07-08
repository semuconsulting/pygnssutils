pygnssutils
=======

[Current Status](#currentstatus) |
[Installation](#installation) |
[gnssdump CLI](#gnssdump) |
[gnssserver CLI](#gnssserver) |
[gnssntripclient CLI](#gnssntripclient) |
[Graphical Client](#gui) |
[Author & License](#author)

pygnssutils is an original Python 3 utility built around three core GNSS protocol libraries from the same stable:

1. [pyubx2 (UBX Protocol)](https://github.com/semuconsulting/pyubx2) - UBX parsing and generation library, which in turn utilises:
1. [pynmeagps (NMEA Protocol)](https://github.com/semuconsulting/pynmeagps) - NMEA parsing and generation library
1. [pyrtcm (RTCM3 Protocol)](https://github.com/semuconsulting/pyrtcm) - RTCM3 parsing library

The capabilities supported by this Beta release of pygnssutils include:

1. `GNSSStreamer` class and its associated [`gnssdump`](#gnssdump) CLI utility, which enhances the [`pyubx2.UBXReader`](https://github.com/semuconsulting/pyubx2#reading) class with a range of configurable input and output media types (e.g. serial, file, socket and queue) and protocol/message filtering options.
1. `GNSSSocketServer` class and its associated [`gnssserver`](#gnssserver) CLI utility. This implements a TCP Socket Server for GNSS data streams which is also capable of being run as a simple NTRIP Server.
1. `GNSSNTRIPClient` class and its associated [`gnssntripclient`](#gnssntripclient) CLI utility. This implements
a simple NTRIP Client which receives RTCM3 correction data from an NTRIP Server and (optionally) sends this to a
designated output stream.

The pygnssutils homepage is located at [https://github.com/semuconsulting/pygnssutils](https://github.com/semuconsulting/pygnssutils).

## <a name="currentstatus">Current Status</a>

![Status](https://img.shields.io/pypi/status/pygnssutils)
![Release](https://img.shields.io/github/v/release/semuconsulting/pygnssutils?include_prereleases)
![Build](https://img.shields.io/github/workflow/status/semuconsulting/pygnssutils/pygnssutils)
![Release Date](https://img.shields.io/github/release-date-pre/semuconsulting/pygnssutils)
![Last Commit](https://img.shields.io/github/last-commit/semuconsulting/pygnssutils)
![Contributors](https://img.shields.io/github/contributors/semuconsulting/pygnssutils.svg)
![Open Issues](https://img.shields.io/github/issues-raw/semuconsulting/pygnssutils)

Sphinx API Documentation in HTML format is available at [https://www.semuconsulting.com/pygnssutils](https://www.semuconsulting.com/pygnssutils).

Contributions welcome - please refer to [CONTRIBUTING.MD](https://github.com/semuconsulting/pygnssutils/blob/master/CONTRIBUTING.md).

[Bug reports](https://github.com/semuconsulting/pygnssutils/blob/master/.github/ISSUE_TEMPLATE/bug_report.md) and [Feature requests](https://github.com/semuconsulting/pygnssutils/blob/master/.github/ISSUE_TEMPLATE/feature_request.md) - please use the templates provided.

---
## <a name="installation">Installation</a>

![Python version](https://img.shields.io/pypi/pyversions/pygnssutils.svg?style=flat)
[![PyPI version](https://img.shields.io/pypi/v/pygnssutils.svg?style=flat)](https://pypi.org/project/pygnssutils/)
![PyPI downloads](https://img.shields.io/pypi/dm/pygnssutils.svg?style=flat)

`pygnssutils` is compatible with Python >=3.7. See [requirements](https://github.com/semuconsulting/pygnssutils/blob/master/requirements.txt) for dependencies. It is recommended that the Python 3 scripts (bin) folder is in your PATH.

In the following, `python3` & `pip` refer to the Python 3 executables. You may need to type 
`python` or `pip3`, depending on your particular environment.

The recommended way to install the latest version of `pygnssutils` is with
[pip](http://pypi.python.org/pypi/pip/):

```shell
python3 -m pip install --upgrade pygnssutils
```

If required, `pygnssutils` can also be installed into a virtual environment, e.g.:

```shell
python3 -m pip install --user --upgrade virtualenv
python3 -m virtualenv env
source env/bin/activate (or env\Scripts\activate on Windows)
(env) python3 -m pip install --upgrade pygnssutils
...
deactivate
```

---
## <a name="gnssdump">GNSSStreamer and gnssdump CLI</a>

```
class pygnssutils.gnssdump.GNSSStreamer(**kwargs)
```

`GNSSStreamer` is essentially a configurable input/output wrapper around the [`pyubx2.UBXReader`](https://github.com/semuconsulting/pyubx2#reading) class. It supports a variety of input streams (including serial, file and socket) and outputs either to stdout (terminal), to an output file or to a custom output handler. The custom output handler can be a writeable output medium (serial, file, socket or queue) or an evaluable Python expression (e.g. lambda function).

The utility can output data in a variety of formats; parsed (1), raw binary (2), hexadecimal string (4), tabulated hexadecimal (8), parsed as string (16), JSON (32), or any combination thereof. You could, for example, output the parsed version of a UBX message alongside its tabular hexadecimal representation.

Any one of the following data stream specifiers must be provided:
- `port`: serial port e.g. `COM3` or `/dev/ttyACM1`
- `filename`: fully qualified path to binary input file e.g. `/logs/logfile.bin`
- `socket`: socket e.g. `192.168.0.72:50007` (port must be specified)
- `stream`: any other instance of a stream class which implements a read(n) -> bytes method

For help and full list of optional arguments, type:

```shell
> gnssdump -h
```

Refer to the [Sphinx API documentation](https://www.semuconsulting.com/pygnssutils/pygnssutils.html#module-pygnssutils.gnssdump) for further details.

### CLI Usage:

Assuming the Python 3 scripts (bin) directory is in your PATH, the CLI utility may be invoked from the shell thus:

Serial input example (with simple external output handler):

```shell
> gnssdump port=/dev/ttyACM1 baud=9600 timeout=5 quitonerror=1 protfilter=2 msgfilter=NAV-PVT outputhandler="lambda msg: print(f'lat: {msg.lat}, lon: {msg.lon}')"

2022-06-23 19:23:12.052109: Parsing GNSS data stream from serial: Serial<id=0x10fe8f100, open=True>(port='/dev/ttyACM1', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=5, xonxoff=False, rtscts=False, dsrdtr=False)...

lat: 51.352179, lon: -2.130762
lat: 51.352155, lon: -2.130751
```

File input example (in parsed and tabulated hexadecimal formats):

```shell
> gnssdump filename=pygpsdata.log quitonerror=2 format=9

2022-07-01 10:47:28.097706: Parsing GNSS data stream from file: <_io.BufferedReader name='pygpsdata.log'>...

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

Socket input example (in JSON format):

```shell
> gnssdump socket=192.168.0.20:50010 format=32 msgfilter=1087

2022-06-23 19:27:10.103332: Parsing GNSS data stream from: <socket.socket fd=3, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 57399), raddr=('127.0.0.1', 50010)>...

{"GNSS_Messages: [{"class": "<class 'pyrtcm.rtcmmessage.RTCMMessage'>", "identity": "1087", "payload": {"DF002": 1087, "DF003": 0, "GNSSEpoch": 738154640, "DF393": 1, "DF409": 0, "DF001_7": 0, "DF411": 0, "DF412": 0, "DF417": 0, "DF418": 0, "DF394": 1152921504606846976, "NSat": 1, "DF395": 1073741824, "NSig": 1, "DF396": 1, "DF405_01": 0.00050994, "DF406_01": 0.00194752, "DF407_01": 102, "DF420_01": 0, "DF408_01": 0, "DF404_01": 0.5118}},...]}
```

Output file example (this filters unwanted UBX config & debug messages from a u-center .ubx file):

```shell
> gnssdump filename=COM6__9600_220623_093412.ubx protfilter=1 format=2 verbosity=0 outfile=COM6__9600_220623_093412_filtered.ubx
```

## <a name="gnssserver">GNSSSocketServer and gnssserver CLI</a>

```
class pygnssutils.gnssserver.GNSSSocketServer(**kwargs)
```

`GNSSSocketServer` is essentially a wrapper around the `GNSSStreamer` and `SocketServer` classes (the latter based on the native Python `ThreadingTCPServer` framework) which uses queues to transport data between the two classes.

### CLI Usage - Default Mode:

In its default configuration (`ntripmode=0`) `gnssserver` acts as an open, unauthenticated CLI TCP socket server, reading the binary data stream from a host-connected GNSS receiver and broadcasting the data to any local or remote TCP socket client capable of parsing binary GNSS data.

It supports most of `gnssdump`'s formatting capabilities and could be configured to output a variety of non-binary formats (including, for example, JSON or hexadecimal), but the client software would need to be capable of parsing data in such formats.

Assuming the Python 3 scripts (bin) directory is in your PATH, the CLI utility may be invoked from the shell thus:

```shell
> gnssserver inport="/dev/tty.usbmodem14301" baudrate=115200 hostip=192.168.0.20 outport=6000
Starting server (type CTRL-C to stop)...
Starting input thread, reading from /dev/tty.usbmodem141301...

Parsing GNSS data stream from: Serial<id=0x1063647f0, open=True>(port='/dev/tty.usbmodem141301', baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=3, xonxoff=False, rtscts=False, dsrdtr=False)...

Starting output thread, broadcasting on 192.168.0.20:6000...
Client ('192.168.0.56', 59565) has connected. Total clients: 1
Client ('192.168.0.34', 59566) has connected. Total clients: 2
Client ('192.168.0.41', 59567) has connected. Total clients: 3
Client ('192.168.0.56', 59565) has disconnected. Total clients: 2
```

`gnssserver` can be run as a daemon process (or even a service) but note that abrupt termination (i.e. without invoking the internal `server.shutdown()` method) may result in the designated TCP socket port being unavailable for a short period - this is operating system dependant.

For help and full list of optional arguments, type:

```shell
> gnssserver -h
```

Refer to the [Sphinx API documentation](https://www.semuconsulting.com/pygnssutils/pygnssutils.html#module-pygnssutils.gnssserver) for further details.

### CLI Usage - NTRIP Mode:

`gnssserver` can also be configured to act as a single-mountpoint NTRIP Server (`ntripmode=1`), broadcasting RTCM3 RTK correction data to any authenticated NTRIP client on the standard 2101 port: 

```shell
> gnssserver inport="/dev/tty.usbmodem14101" hostip=192.168.0.20 outport=2101 ntripmode=1 protfilter=4
```

**NOTE THAT** this configuration is predicated on the host-connected receiver being an RTK-capable device (e.g. the u-blox ZED-F9P) operating in 'Base Station' mode (either 'SURVEY_IN' or 'FIXED') and outputting the requisite RTCM3 RTK correction messages (1005, 1077, 1087, 1097, 1127, 1230). NTRIP server login credentials are set via environment variables `PYGPSCLIENT_USER` and `PYGPSCLIENT_PASSWORD`. 

### Clients

`gnssserver` will work with any client capable of parsing binary GNSS data from a TCP socket. Suitable clients include, *but are not limited to*:

1) pygnssutils's `gnssdump` cli utility invoked thus:
```shell
> gnssdump socket=hostip:outport
```
2) The PyGPSClient GUI application.

---
## <a name="gnssntripclient">GNSSNTRIPClient and gnssntripclient CLI</a>

```
class pygnssutils.gnssntripclient.GNSSNTRIPClient(app=None, **kwargs)
```

The `GNSSNTRIPClient` class provides a basic NTRIP Client capability and forms the basis of a [`gnssntripclient`](#gnssntripclient) CLI utility. It receives RTCM3 correction data from an NTRIP server and (optionally) sends this to a
designated output stream.

### CLI Usage:

Assuming the Python 3 scripts (bin) directory is in your PATH, the CLI utility may be invoked from the shell thus:

To retrieve the sourcetable and determine the closest available mountpoint to the reference lat/lon, leave the
mountpoint argument blank (the port defaults to 2101):

```shell
> gnssntripclient server=rtk2go.com reflat=37.23 reflon=-115.81 verbosity=2
2022-06-03 20:15:54.510294: Closest mountpoint to reference location 37.23,-115.81 = WW6RY, 351.51 km

Complete sourcetable follows...

['AGSSIAAP', 'Acheres', 'RTCM 3.0', '1004(1),1006(13),1012(1),1033(31)', '2', 'GPS+GLO', 'SNIP', 'FRA', '48.97', '2.17', '1', '0', 'sNTRIP', 'none', 'N', 'N', '2540', '']
...
```

To retrieve correction data from a designated mountpoint (this will send NMEA GGA position sentences to the server at intervals of 60 seconds, based on the supplied reference lat/lon):

```shell
> gnssntripclient server=rtk2go.com reflat=37.23 reflon=-115.81 mountpoint=UFOSRUS ggainterval=60 verbosity=2
2022-06-03 11:55:10.305870: <RTCM(1077, DF002=1077, DF003=0, GNSSEpoch=471328000, DF393=1, ...
```

For help and full list of optional arguments, type:

```shell
> gnssntripclient -h
```

Refer to the [Sphinx API documentation](https://www.semuconsulting.com/pygnssutils/pygnssutils.html#module-pygnssutils.gnssntripclient) for further details.


---
## <a name="gui">Graphical Client</a>

A python/tkinter graphical GPS client which supports NMEA, UBX and RTCM3 protocols is available at: 

[https://github.com/semuconsulting/PyGPSClient](https://github.com/semuconsulting/PyGPSClient)

---
## <a name="author">Author & License Information</a>

semuadmin@semuconsulting.com

![License](https://img.shields.io/github/license/semuconsulting/pygnssutils.svg)

`pygnssutils` is maintained entirely by unpaid volunteers. If you find it useful, a small donation would be greatly appreciated!

[![Donations](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_LG.gif)](https://www.paypal.com/donate/?hosted_button_id=4TG5HGBNAM7YJ)
