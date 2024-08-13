"""
compareconfigs.py

Parse and compare contents of two or more u-blox config files. Can accept either
*.txt (text) or *.ubx (binary) formatted input files - the default is *.txt.

Usage:

   python3 compareconfigs.py infiles="config1.txt, config2.txt" format=0 onlydiffs=1

Outputs dictionary of config keys and their values for each file e.g.

- CFG_RATE_MEAS (None): {1: '1000', 2: '1000'} signifies both files have same value
- CFG_RATE_MEAS (DIFFS!): {1: '1000', 2: '100'} signifies differences between files
- CFG_RATE_MEAS (DIFFS!): {1: '1000'} signifies the value was missing from the second
  or subsequent file(s)

By default, only differences are listed. Set 'onlydiffs=0' to list all config keys.

:author: semuadmin
:copyright: SEMU Consulting © 2020
:license: BSD 3-Clause
"""

from sys import argv

from pyubx2 import (
    POLL_LAYER_BBR,
    POLL_LAYER_FLASH,
    SET,
    SET_LAYER_BBR,
    SET_LAYER_FLASH,
    SET_LAYER_RAM,
    TXN_NONE,
    U1,
    UBXMessage,
    UBXReader,
    bytes2val,
    val2bytes,
)
from pygnssutils.globals import UTF8

CFG = b"\x06"
VALGET = b"\x8b"
VALSET = b"\x8a"
FORMAT_UBX = 1
FORMAT_TXT = 0


def parse_line(line: str) -> UBXMessage:
    """
    Parse individual config line from txt file.

    Any messages other than CFG-MSG, CFG-PRT or CFG-VALGET are discarded.
    The CFG-VALGET messages are converted into CFG-VALSET.

    :param str line: config line
    :return: parsed config line as UBXMessage
    :rtype: UBXMessage
    """

    parts = line.replace(" ", "").split("-")
    data = bytes.fromhex(parts[-1])
    cls = data[0:1]
    mid = data[1:2]
    if cls != CFG:
        return None
    if mid == VALGET:  # config database command
        version = data[4:5]
        layer = bytes2val(data[5:6], U1)
        if layer == POLL_LAYER_BBR:
            layers = SET_LAYER_BBR
        elif layer == POLL_LAYER_FLASH:
            layers = SET_LAYER_FLASH
        else:
            layers = SET_LAYER_RAM
        layers = val2bytes(layers, U1)
        transaction = val2bytes(TXN_NONE, U1)
        reserved0 = b"\x00"
        cfgdata = data[8:]
        payload = version + layers + transaction + reserved0 + cfgdata
        parsed = UBXMessage(CFG, VALSET, SET, payload=payload)
    else:  # legacy CFG command
        parsed = UBXMessage(CFG, mid, SET, payload=data[4:])

    return parsed


def get_attrs(cfgdict: dict, parsed: str, fileno: int):
    """
    Get individual config keys and values from parsed line.

    :param dict cfgdict: dictionary of all config keys and values
    :param UBXMessage parsed: parsed config line
    :param int fileno: file number
    """

    attrs = parsed.split(",")
    for attr in attrs:
        attr = attr.strip('")> ')
        if attr[0:3] == "CFG":
            key, val = attr.split("=")
            diff = cfgdict.get(key, {})
            diff[fileno] = val
            cfgdict[key] = diff


def parse_file(cfgdict: dict, filename: str, fileno: int, form: int):
    """
    Load u-center format text configuration file.

    :param dict cfgdict: dictionary of all config keys and values
    :param str filename: fully qualified input file name
    :param int fileno: file number
    :param int form: 0 = TXT (text), 1 = UBX (binary)
    """

    # pylint: disable=broad-exception-caught

    i = 0
    try:
        if form == FORMAT_UBX:  # ubx (binary) format
            with open(filename, "rb") as infile:
                ubr = UBXReader(infile, msgmode=SET)
                for _, parsed in ubr:
                    if parsed is not None:
                        get_attrs(cfgdict, str(parsed), fileno)
                        i += 1
        else:  # txt (text) format
            with open(filename, "r", encoding=UTF8) as infile:
                for line in infile:
                    parsed = parse_line(line)
                    if parsed is not None:
                        get_attrs(cfgdict, str(parsed), fileno)
                        i += 1
    except Exception as err:
        print(f"\nERROR parsing {filename}! \n{err}")

    print(f"\n{i} configuration commands processed in {filename}")


def main(**kwargs):
    """
    Main routine.
    """

    infiles = kwargs.get(
        "infiles",
        "simpleRTK2B_FW132_Rover_1Hz-00.txt, simpleRTK2B_FW132_Rover_10Hz-00.txt",
    ).split(",")
    form = int(kwargs.get("format", FORMAT_TXT))
    onlydiffs = int(kwargs.get("onlydiffs", 1))

    cfgdict = {}
    fcount = 0
    dcount = 0
    kcount = 0

    for file in infiles:
        fcount += 1
        parse_file(cfgdict, file.strip(), fcount, form)

    print(
        f"\n{fcount} files processed, list of {"differences in" if onlydiffs else "all"}",
        "config keys and their values follows:\n",
    )

    for key, vals in dict(sorted(cfgdict.items())).items():
        kcount += 1
        totalvals = len(vals.values())  # check if config appears in all files
        uniquevals = len(set(vals.values()))  # check if all values are the same
        diff = totalvals != fcount or uniquevals != 1
        if diff:
            dcount += 1
        if (onlydiffs and diff) or not onlydiffs:
            print(f"{key} ({"DIFFS!" if diff else None}): {vals}")

    print(f"\nTotal config keys: {kcount}. Total differences: {dcount}.")


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
