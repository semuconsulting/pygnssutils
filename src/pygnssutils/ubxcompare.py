"""
ubxcompare.py

Parse and compare contents of two or more u-blox config files. Can accept either
*.txt (text) or *.ubx (binary) formatted input files - the default is *.txt.

Usage:

   ubxcompare --infiles "config1.txt, config2.txt" --format 0 --diffsonly 1

Outputs dictionary of config keys and their values for each file e.g.

- CFG_RATE_MEAS (None): {1: '1000', 2: '1000'} signifies both files have same value
- CFG_RATE_MEAS (DIFFS!): {1: '1000', 2: '100'} signifies differences between values
- CFG_RATE_MEAS (DIFFS!): {1: '1000'} signifies the value was missing from the second
  or subsequent file(s)

:author: semuadmin
:copyright: SEMU Consulting © 2024
:license: BSD 3-Clause
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

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

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import EPILOG

CFG = b"\x06"
VALGET = b"\x8b"
VALSET = b"\x8a"
FORMAT_UBX = 1
FORMAT_TXT = 0


class UBXCompare:
    """UBX Compare Configuration Class."""

    def __init__(self, infiles: str, form: int = FORMAT_TXT, diffsonly: bool = True):
        """
        Constructor.

        :param str infiles: comma-separated list of fully-qualified filenames
        :param int format: 0 = text, 1 = binary (0)
        :param bool diffsonly: True = show diffs only, False = show entire config (True)
        """

        if infiles in ("", None):
            raise ValueError("--infiles parameter must not be blank")

        infiles = infiles.split(",")
        cfgdict = {}
        fcount = 0
        dcount = 0
        kcount = 0

        for file in infiles:
            fcount += 1
            self.parse_file(cfgdict, file.strip(), fcount, form)

        print(
            f"\n{fcount} files processed, list of {'differences in' if diffsonly else 'all'}",
            "config keys and their values follows:\n",
        )

        for key, vals in dict(sorted(cfgdict.items())).items():
            kcount += 1
            totalvals = len(vals.values())  # check if config appears in all files
            uniquevals = len(set(vals.values()))  # check if all values are the same
            diff = totalvals != fcount or uniquevals != 1
            if diff:
                dcount += 1
            if (diffsonly and diff) or not diffsonly:
                print(f"{key} ({'DIFFS!' if diff else None}); {str(vals).strip('{}')}")

        print(f"\nTotal config keys: {kcount}. Total differences: {dcount}.")

    def parse_line(self, line: str) -> UBXMessage:
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

    def get_attrs(self, cfgdict: dict, parsed: str, fileno: int):
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

    def parse_file(self, cfgdict: dict, filename: str, fileno: int, form: int):
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
                            self.get_attrs(cfgdict, str(parsed), fileno)
                            i += 1
            else:  # txt (text) format
                with open(filename, "r", encoding="utf-8") as infile:
                    for line in infile:
                        parsed = self.parse_line(line)
                        if parsed is not None:
                            self.get_attrs(cfgdict, str(parsed), fileno)
                            i += 1
        except Exception as err:
            print(f"\nERROR parsing {filename}! \n{err}")

        print(f"\n{i} configuration commands processed in {filename}")


def main():
    """
    CLI Entry point.

    :param: as per UBXLoader constructor.
    """

    ap = ArgumentParser(epilog=EPILOG, formatter_class=ArgumentDefaultsHelpFormatter)
    ap.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    ap.add_argument(
        "-I",
        "--infiles",
        type=str,
        required=True,
        help="Comma-separated list of fully-qualified filenames",
    )
    ap.add_argument(
        "-F",
        "--format",
        required=False,
        help="Format 0 = txt (text), 1 = ubx (binary)",
        type=int,
        choices=[0, 1],
        default=0,
    )
    ap.add_argument(
        "-D",
        "--diffsonly",
        required=False,
        help="Diffs 0 = Show all config values, 1 = Show differences only",
        type=int,
        choices=[0, 1],
        default=1,
    )

    args = ap.parse_args()
    UBXCompare(args.infiles, args.format, args.diffsonly)


if __name__ == "__main__":

    main()
