pygnssutils
=======

[Current Status](#currentstatus) |
[Installation](#installation) |
[GNSSReader](#reading) |
[Command Line Utilities](#cli) |
[Troubleshooting](#troubleshoot) |
[Graphical Client](#gui) |
[Author & License](#author)

`pygnssutils` is an original Python 3 library which reads, parses and broadcasts the NMEA, UBX or RTCM3 output of any GNSS receiver. 

It consolidates the common capabilities of three existing GNSS protocol libraries from the same stable:

1. [pynmeagps (NMEA Protocol)](https://github.com/semuconsulting/pygnssutils)
1. [pyubx2 (UBX Protocol)](https://github.com/semuconsulting/pygnssutils)
1. [pyrtcm (RTCM3 Protocol)](https://github.com/semuconsulting/pygnssutils)

**NB:** pygnssutils does *not* replace these libraries. `pynmeagps`, `pyubx2` and `pyrtcm` will continue to be developed as independent libraries for their specific protocol parsing and generation capabilities, but functionality which is common to all three (such as reading from a GNSS data stream, and certain helper functions) will be incorporated into pygnssutils. The intention is to reduce code duplication between these libraries, reduce maintenance and testing overheads, and act as a framework for future generic GNSS capabilities.

The common capabilities supported by pygnssutils include:

1. **GNSSReader** class which reads and parses the NMEA, UBX or RTCM3 output of a GNSS device. This consolidates (and will in due course replace) the UBXReader, NMEAReader and RTCMReader classes in the original libraries.
1. **gnssdump** command line utility (incorporating **GNSSStreamer** class) which streams the NMEA, UBX or RTCM3 output of a GNSS device to stdout (terminal) or to designated protocol handlers / output media (including Serial, File (text or binary), socket or Queue). This will in due course replace the equivalent command line utilities in the original libraries.
1. **gnssserver** command line utility (incorporating **GNSSServer** class) which acts as a TCP Socket Server or NTRIP Server for GNSS data streams.

The pygnssutils homepage is located at [https://github.com/semuconsulting/pygnssutils](https://github.com/semuconsulting/pygnssutils).

## <a name="currentstatus">Current Status</a>

![Status](https://img.shields.io/pypi/status/pygnssutils)
![Release](https://img.shields.io/github/v/release/semuconsulting/pygnssutils)
![Build](https://img.shields.io/github/workflow/status/semuconsulting/pygnssutils/pygnssutils)
<!--![Codecov](https://img.shields.io/codecov/c/github/semuconsulting/pygnssutils)-->
![Release Date](https://img.shields.io/github/release-date-pre/semuconsulting/pygnssutils)
![Last Commit](https://img.shields.io/github/last-commit/semuconsulting/pygnssutils)
![Contributors](https://img.shields.io/github/contributors/semuconsulting/pygnssutils.svg)
![Open Issues](https://img.shields.io/github/issues-raw/semuconsulting/pygnssutils)

Sphinx API Documentation in HTML format is available at [https://www.semuconsulting.com/pygnssutils](https://www.semuconsulting.com/pygnssutils).

Contributions welcome - please refer to [CONTRIBUTING.MD](https://github.com/semuconsulting/pygnssutils/blob/master/CONTRIBUTING.md).

[Bug reports](https://github.com/semuconsulting/pygnssutils/blob/master/.github/ISSUE_TEMPLATE/bug_report.md) and [Feature requests](https://github.com/semuconsulting/pygnssutils/blob/master/.github/ISSUE_TEMPLATE/feature_request.md) - please use the templates provided.

---
## <a name="installation">Installation</a>

`pygnssutils` is compatible with Python >=3.7. See [requirements](https://github.com/semuconsulting/pygnssutils/blob/master/requirements.txt) for dependencies. It is recommended that the Python 3 scripts (bin) folder is in your PATH.

In the following, `python3` & `pip` refer to the Python 3 executables. You may need to type 
`python` or `pip3`, depending on your particular environment.

![Python version](https://img.shields.io/pypi/pyversions/pygnssutils.svg?style=flat)
[![PyPI version](https://img.shields.io/pypi/v/pygnssutils.svg?style=flat)](https://pypi.org/project/pygnssutils/)
![PyPI downloads](https://img.shields.io/pypi/dm/pygnssutils.svg?style=flat)

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
## <a name="reading">GNSSReader</a>

```
class pygnssutils.gnssreader.GNSSReader(stream, *args, **kwargs)
```

You can create a `GNSSReader` object by calling the constructor with an active stream object. 
The stream object can be any data stream which supports a `read(n) -> bytes` method (e.g. File or Serial, with 
or without a buffer wrapper). `GNSSReader` implements an internal `SocketStream` class to allow sockets to be read in the same way as other streams (see example below).

Individual input NMEA, UBX, or RTCM3 messages can then be read using the `GNSSReader.read()` function, which returns both the raw binary data (as bytes) and the parsed data (as a `UBXMessage`, `NMEAMessage` or `RTCMMessage` object). The function is thread-safe in so far as the incoming data stream object is thread-safe. `GNSSReader` also implements an iterator.

The constructor accepts the following optional keyword arguments:

* `protfilter`: 1 = NMEA, 2 = UBX, 4 = RTCM3 (can be OR'd. default is 7 - NMEA & UBX & RTCM3)
* `quitonerror`: 0 = ignore errors, 1 = log errors and continue (default), 2 = (re)raise errors and terminate
* `validate`: VALCKSUM (0x01) = validate checksum (default), VALNONE (0x00) = ignore invalid checksum or length
* `parsebitfield`: 1 = parse bitfields (UBX 'X' type properties) as individual bit flags, where defined (default), 0 = leave bitfields as byte sequences
* `msgmode`: 0 = GET (default), 1 = SET, 2 = POLL

Example -  Serial input. This example will output both UBX and NMEA messages:
```python
>>> from serial import Serial
>>> from pygnssutils import GNSSReader
>>> stream = Serial('/dev/tty.usbmodem14101', 9600, timeout=3)
>>> gnr = GNSSReader(stream)
>>> (raw_data, parsed_data) = gnr.read()
>>> print(parsed_data)
```

Example - File input (using iterator). This will only output UBX data:
```python
>>> from pygnssutils import GNSSReader
>>> stream = open('ubxdata.bin', 'rb')
>>> gnr = GNSSReader(stream, protfilter=2)
>>> for (raw_data, parsed_data) in gnr: print(parsed_data)
...
```

Example - Socket input (using enhanced iterator). This will output UBX, NMEA and RTCM3 data:
```python
>>> import socket
>>> from pygnssutils import GNSSReader
>>> stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM):
>>> stream.connect(("localhost", 50007))
>>> gnr = GNSSReader(stream, protfilter=7)
>>> for (raw_data, parsed_data) in gnr.iterate(): print(parsed_data)
...
```

---
## <a name="cli">Command Line Utilities</a>

If `pygnssutils` is installed using pip, the following command line utilities are automatically installed into the Python 3 scripts (bin) directory:

1. **gnssdump** - streams the NMEA, UBX or RTCM3 output of any GNSS device to stdout (terminal) or to designated protocol handlers / output media (including Serial, File socket or Queue) in a variety of formats.
1. **gnssserver** - acts as a TCP Socket Server or NTRIP Server for GNSS data streams.

### <a name="gnssdump">gnssdump (GNSSStreamer)</a>

This utility is capable of streaming and parsing NMEA, UBX and RTCM3 data from any data stream (including Serial and File) to the terminal or to designated NMEA, UBX or RTCM3 protocol handlers. A protocol handler could be a 
writeable output media (e.g. File or socket) or an evaluable Python expression.

The utility can output data in a variety of formats; parsed (1), raw binary (2), hexadecimal string (4), tabulated hexadecimal (8) or any combination thereof.

Any one of the following data stream specifiers must be provided:
- `stream`: any instance of a stream class which implements a read(n) -> bytes method
- `filename`: name of binary input file e.g. `logfile.bin`
- `port`: serial port e.g. `COM3` or `/dev/ttyACM1`
- `socket`: socket e.g. `192.168.0.72:50007` (port must be specified)

For help and full list of optional arguments, type:

```shell
> gnssdump -h
```

Assuming the Python 3 scripts (bin) directory is in your PATH, the CLI utility may be invoked from the shell thus:

Serial input example (with simple external UBX protocol handler):

```shell
> gnssdump port=/dev/ttyACM1 baud=9600 timeout=5 quitonerror=1 protfilter=2 msgfilter=NAV-PVT ubxhandler="lambda msg: print(f'lat: {msg.lat}, lon: {msg.lon}')"

Parsing GNSS data stream from serial: Serial<id=0x10fe8f100, open=True>(port='/dev/ttyACM1', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=5, xonxoff=False, rtscts=False, dsrdtr=False)...

lat: 51.352179, lon: -2.130762
lat: 51.352155, lon: -2.130751
```

File input example (in tabulated hexadecimal format):

```shell
> gnssdump filename=pygpsdata.log quitonerror=2 format=8 protfilter=1 msgfilter=GPGGA,GPGSA

Parsing GNSS data stream from file: <_io.BufferedReader name='pygpsdata.log'>...

000: 2447 5047 4741 2c30 3830 3234 372e 3030  | b'$GPGGA,080247.00' |
016: 2c35 3332 372e 3034 3330 302c 4e2c 3030  | b',5327.04300,N,00' |
032: 3231 342e 3431 3338 352c 572c 312c 3037  | b'214.41385,W,1,07' |
048: 2c31 2e36 332c 3336 2e37 2c4d 2c34 382e  | b',1.63,36.7,M,48.' |
064: 352c 4d2c 2c2a 3737 0d0a                 | b'5,M,,*77\r\n' |

000: 2447 5047 5341 2c41 2c33 2c30 322c 3133  | b'$GPGSA,A,3,02,13' |
016: 2c32 302c 3037 2c30 352c 3330 2c30 392c  | b',20,07,05,30,09,' |
032: 2c2c 2c2c 2c32 2e34 342c 312e 3633 2c31  | b',,,,,2.44,1.63,1' |
048: 2e38 322a 3035 0d0a                      | b'.82*05\r\n' |
```

The `gnssdump` utility implements a new `GNSSStreamer` class which may be used directly within Python application code via:

```python
>>> from pygnssutils import GNSSStreamer
```

### <a name="gnssserver">gnssserver (GNSSServer)</a>

This is a simple but fully-functional example of a TCP Socket Server or NTRIP Server which reads the binary data stream from a connected GNSS receiver and broadcasts the data to any TCP socket or NTRIP client running on a local or remote
machine (*firewalls permitting*).

Assuming the Python 3 scripts (bin) directory is in your PATH, the CLI utility may be invoked from the shell thus:

```shell
> gnssserver inport="/dev/tty.usbmodem14101" hostip=192.168.0.20 outport=6000
```

Any arguments not provided will be defaulted;
- default hostip = 0.0.0.0 (i.e. binds to all available host IP address)
- default inport = "/dev/ttyACM1"
- default outport = 50010

For help and full list of optional arguments, type:

```shell
> gnssserver -h
```

In the default output format onfiguration (`format=FORMAT_BINARY`), the clients must be capable of parsing binary GNSS data. Suitable clients include (*but are not limited to*):
1) pygnssutils's gnssdump cli utility invoked thus:
```shell
> gnssdump socket=hostip:outport
```

2) The PyGPSClient GUI application, invoked thus:
```shell
> pygpsclient
```

To run in NTRIP Server mode, set `ntripmode=1`. For this mode to function properly, the receiver must be an RTK-capable receiver (e.g. u-blox ZED-F9P) running in "Base Station" mode (either SURVEY_IN or FIXED). The clients must be NTRIP clients (e.g. PyGPSClient's NTRIP Client facility). NTRIP server login credentials are set via environment variables `PYGPSCLIENT_USER` and `PYGPSCLIENT_PASSWORD`.

---
## <a name="troubleshoot">Troubleshooting</a>

#### 1. `Unknown Protocol` errors.
These are usually due to corruption of the serial data stream, either because the serial port configuration is incorrect (baud rate, parity, etc.) or because another process is attempting to use the same data stream. 
- Check that your UBX receiver UART1 or UART2 ports are configured for the desired baud rate - remember the factory default is 38400 (*not* 9600).
- Check that no other process is attempting to use the same serial port, including daemon processes like gpsd.
#### 2. `Serial Permission` errors. 
These are usually caused by inadequate user privileges or contention with another process. 
- On Linux platforms, check that the user is a member of the `tty` and/or `dialout` groups.
- Check that no other process is attempting to use the same serial port, including daemon processes like gpsd.
#### 3. `UnicodeDecode` errors.
- If reading UBX data from a log file, check that the file.open() procedure is using the `rb` (read binary) setting e.g.
`stream = open('ubxdatalog.log', 'rb')`.
#### 4. Reading from NMEA log file returns no results.
- If reading from a binary log file containing NMEA messages, ensure that the message terminator is `CRLF` (`\r\n` or `x0d0a`) rather than just `LF` (`\n` or `0x0a`). Some standard text editors may replace a `CRLF` with `LF` - use a dedicated hex editor instead.


---
## <a name="gui">Graphical Client</a>

A python/tkinter graphical GPS client which supports both NMEA and UBX protocols (via pynmeagps and pygnssutils 
respectively) is available at: 

[https://github.com/semuconsulting/PyGPSClient](https://github.com/semuconsulting/PyGPSClient)

---
## <a name="author">Author & License Information</a>

semuadmin@semuconsulting.com

![License](https://img.shields.io/github/license/semuconsulting/pygnssutils.svg)

`pygnssutils` is maintained entirely by volunteers. If you find it useful, a small donation would be greatly appreciated!

[![Donations](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_LG.gif)](https://www.paypal.com/donate/?hosted_button_id=4TG5HGBNAM7YJ)
