"""
rawnav.py

Raw navigation data container class.

This is provided as the basis of a capability to parse and store
the individual attributes (ephemerides, ionospheric corrections,
etc.) of one or more raw GNSS NAV subframe messages, as a
precursor to RINEX conversion.

The objective is to handle any GNSS subframe format for which:

 - data is available as a raw, unpadded little-endian integer.
 - data definition dictionary has been transcribed from the relevant
   GNSS ICD (Interface Control Document) with standardized ascii
   field names e.g. `omegadot`, `sqrta`, `cus`, etc.
 - any bit encodings (other than basic unsigned int, 2's complement
   signed int and IEEE 754 float) have been defined and implemented
   in `bits2val`.

Once a RawNav object is instantiated, the `parse` function can
be invoked repeatedly to collate data from separate sequential
subframes e.g. for GPS LNAV, subframe 1 contains clock corrections,
subframes 2 & 3 contain ephemerides and subframe 4 page 18 contains
ionospheric corrections. An `sfracq` bitfield signifies which
subframe IDs have been acquired.

Format of data definition dictionary::

   dict[field_name, tuple[offset, length, encoding, scaling]

where offset and length are in bits (see, for example,
`rinex_subframes_gps.py`).

MSB and LSB field names MUST be suffixed "_msb" and "_lsb"
respectively - the `parse` function will automatically combine them.

A boolean `sequence` argument determines whether subframes are
processed as a sequence e.g. for GNSS where MSB and LSB attributes
are in separate, sequential (but not necessarily contiguous) subframes.

Static methods are provided to facilitate acquisition of NAV subframe data
from UBX RXM-SFRBX messages (currently for GPS LNAV only).

Created on 20 Apr 2026

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2026
:license: BSD 3-Clause
"""

import struct
from datetime import datetime, timezone
from types import NoneType
from typing import Literal

from pynmeagps import utc2wnotow, wnotow2utc
from pyubx2 import UBXMessage

from pygnssutils.exceptions import RINEXProcessingError
from pygnssutils.rinex_globals import GPS, UBXRINEXGNSS, UBXRINEXOBSCODE

LSB = "_lsb"
"""MSB field name suffix"""
MSB = "_msb"
"""LSB field name suffix"""
TOC = "toc"
"""TOC (time of clock) field name - used to establish epoch"""
TOW = "tow"
"""HOW TOW field name"""
SFR = "subframeid"
"""subframe id field name"""
WN = "wn"
"""WN (week number) field name - used to establish epoch"""

PREAMBLE = "preamble"
VALPREAMBLE = "_valid_preamble"
D = "D"  # IEEE 754 64-bit double float
F = "F"  # IEEE 754 32-bit float
S = "S"  # 2's complement signed integer
U = "U"  # unsiged integer


class RawNav:
    """
    Raw Navigation Class.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        gnss: Literal["G", "R", "E", "C", "J", "S", "I"],
        svid: int,
        sigid: str,
        **kwargs,  # pylint: disable=unused-argument
    ):
        """
        Constructor.

        :param Literal["G","R","E","C","J","S","I"] gnss: GNSS code
        :param int svid: RINEX SV id e.g. 14
        :param str sigid: RINEX signal id e.g. "1C"
        :param dict kwargs: optional keyword arguments
        """

        self._gnss = gnss
        self._svid = svid
        self._sigid = sigid
        self._epoch = datetime.now(timezone.utc)
        wno, tow, _ = utc2wnotow(self._epoch, gnss)
        self.wn = wno
        self.toc = int(tow / 1000)
        self._sfracq = 0
        self._msb = {}
        self._firsttoc = 999999999
        self._lasttoc = 0
        self._firstwn = 999999999
        self._lastwn = 0

    def parse(
        self,
        data: int,
        definition: dict[str, tuple[int, int, str, int]],
        sequence: bool = False,
    ):
        """
        Parse raw subframe data into its constituent attributes.

        :param int data: raw, unpadded input data
        :param dict[str, tuple[int, int, str, int]] def: subframe definition dictionary \
            (from GNSS ICD)
        :param bool sequence: process subframe as part of a contiguous sequence (False)
        :raises: RINEXProcessingError
        """
        # pylint: disable=too-many-locals

        try:

            # get exemplary preamble value if one is available
            valpre = definition.pop(VALPREAMBLE, 0)

            # validate subframe length in bits
            offset, bitlen, _, _ = list(definition.values())[-1]
            sfrlen = offset + bitlen
            datlen = len(bin(data)) - 2
            if datlen != sfrlen:
                raise RINEXProcessingError(
                    f"Data bit size {datlen} does not match defined subframe bit size {sfrlen}"
                )

            # parse each attribute in subframe, combining MSB and LSB fields
            # where appropriate
            for att, (offset, length, encoding, scaling) in definition.items():

                if att[0:1] == "_":  # ignore non-data bits
                    continue
                bits = data >> (sfrlen - offset - length) & (2**length - 1)

                # validate preamble if an exemplary value is available
                if valpre and att == PREAMBLE and bits != valpre:
                    raise RINEXProcessingError(
                        f"Invalid preamble - expected 0b{valpre:b}, got 0b{bits:b}"
                    )

                # recombine MSB and LSB where possible
                if att[-4:].lower() == MSB:
                    self._msb[att] = (bits, length, encoding, scaling)
                    continue
                if att[-4:].lower() == LSB:
                    msbbits, msblen, _, _ = self._msb.pop(
                        f"{att[:-4]}{MSB}", (0, 0, 0, 0)
                    )
                    bits = (msbbits << length) + bits
                    if msblen:
                        att = att[:-4]
                    length += msblen

                val = self._bits2val(bits, length, encoding, scaling)
                setattr(self, att, val)

                if att == SFR:  # update subframe acquisition status
                    self._sfracq |= int(2 ** (val - 1))

            # update epoch with last acquisition timestamp
            # TODO is toc the correction value to use here?
            # doesn't seem to reflect actual UTC time and
            # doesn't appear to increment by seconds like
            # the tow in HOW???
            self._epoch = wnotow2utc(
                int(getattr(self, WN)),
                int(getattr(self, TOC) * 1000),
                None,
                self._gnss,
                True,
            )

            if not sequence:
                self._store_orphaned_msb()

        except (ValueError, TypeError, KeyError) as err:
            raise RINEXProcessingError(
                "Invalid subframe definition dictionary."
            ) from err

    def _store_orphaned_msb(self):
        """
        If not processing sequentially, store any 'orphaned' MSB now rather
        than waiting for associated LSB from next subframe in sequence.
        """

        for att, (bits, length, encoding, scaling) in self._msb.items():
            val = self._bits2val(bits, length, encoding, scaling)
            setattr(self, att, val)
        self._msb = {}

    def _bits2val(
        self, vali: int, length: int, encoding: str, scaling: int
    ) -> int | float:
        """
        Convert encoded bits to value.

        :param int vali: value as raw integer
        :param int length: length in bits
        :param str encoding: bit encoding e.g. U, S, F
        :param int scaling: scaling factor (0 = no scaling)
        :return: decoded value
        :rtype: int | float
        :raises: RINEXProcessingError
        """

        val = vali
        if encoding == "U":  # unsigned integer
            pass
        elif encoding == "S":  # 2's complement signed integer
            if vali >= (1 << (length - 1)):
                val = vali - (1 << length)
        elif encoding == "F":  # IEEE 754 32 bit floating point
            valb = int.to_bytes(vali, 4, "little")
            val = struct.unpack("<f", valb)[0]
        elif encoding == "D":  # IEEE 754 64 bit double floating point
            valb = int.to_bytes(vali, 8, "little")
            val = struct.unpack("<d", valb)[0]
        # add any additional bit encodings here...
        # elif encoding == "?":  # additional encoding
        #     # do stuff here or call helper function
        else:
            raise RINEXProcessingError(f"Unknown attribute type {encoding}")
        if scaling not in (0, 1):
            val *= scaling
        return val

    def __str__(self) -> str:
        """
        Human readable representation.

        :return: human readable representation
        :rtype: str
        """

        ep = self._epoch.strftime("%Y-%m-%d-%H:%M:%S.%f%z")
        stg = (
            f"<RAWNAV({self.identity}, gnss={self._gnss}, svid={self._svid}, "
            f"sigid={self._sigid}, epoch={ep}, sfracq={self._sfracq}, "
        )
        for i, att in enumerate(self.__dict__):
            if att[0] != "_":  # only show public attributes
                val = self.__dict__[att]
                stg += att + "=" + str(val)
                if i < len(self.__dict__) - 1:
                    stg += ", "
        stg += ")>"
        return stg

    @property
    def identity(self) -> str:
        """
        Getter for identity.

        :return: identity
        :rtype: str
        """

        return f"{self._gnss}{self._svid:02d}{self._sigid}"

    @property
    def gnss(self) -> str:
        """
        Getter for GNSS code.

        :return: gnss
        :rtype: str
        """

        return self._gnss

    @property
    def svid(self) -> int:
        """
        Getter for SV id.

        :return: svid
        :rtype: int
        """

        return self._svid

    @property
    def sigid(self) -> str:
        """
        Getter for signal id in RINEX format.

        :return: signal id
        :rtype: str
        """

        return self._sigid

    @property
    def epoch(self) -> datetime:
        """
        Getter for epoch.

        :return: gnss
        :rtype: datetime
        """

        return self._epoch

    @property
    def sfracq(self) -> int:
        """
        Getter for subframe acquisition status.

        Bitfield signifying which subframe IDs have been acquired:

        - sfracq & 0b001 => subframe 1
        - sfracq & 0b010 => subframe 2,
        - sfracq & 0b100 => subframe 3, etc.

        :return: subframe acquisition status.
        :rtype: int
        """

        return self._sfracq

    @staticmethod
    def process_rxm_sfrbx(data: UBXMessage) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble individual subframe from UBX RXM-SFRBX dwrds.

        :param UBXMessage data: parsed UBX RXM-SFRBX message
        :return: dict of subframe attributes
        :rtype: dict[str, str | int | float | NoneType]
        :raises: RINEXProcessingError
        """

        valid = False
        if isinstance(data, UBXMessage):
            if data.identity == "RXM-SFRBX":
                valid = True
        if not valid:
            raise RINEXProcessingError(
                f"Data must be UBX RXM-SFRBX message - got {type(data)}"
            )

        output = {}
        try:
            gnss = UBXRINEXGNSS[data.gnssId]
            svid = data.svId
            numw = data.numWords
            sigid = UBXRINEXOBSCODE[(data.gnssId, data.sigId)]
        except KeyError as err:
            raise RINEXProcessingError(
                f"Unrecognised GNSS or Signal code: {data.gnssId=}, {data.sigId=}"
            ) from err

        subframe = 0
        tow = None
        subframeid = 0

        # for GPS LNAV, words are 30 bits each, padded with 2 bits at end
        if gnss == GPS and sigid == "1C":
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}") & 0xFFFFFFFC >> 2
                subframe += wrd << (30 * (numw - 1 - i))
            # tow in HOW is 17 MSB of Z-count; full tow is 19 bits.
            # rolls over at 100,799
            # tow = (subframe >> 251) & 0x7FFFC  # << 2 to make 19 bits
            tow = (subframe >> 253) & 0b11111111111111111  # << 2 to make 19 bits
            subframeid = (subframe >> 248) & 0x7
            output = {
                "gnss": gnss,
                "svid": svid,
                "sigid": sigid,
                "subframeid": subframeid,
                "tow": tow,
                "subframe": subframe,
            }
            if subframeid in (4, 5):
                output["dataid"] = subframe >> 234 & 0x3
                output["svcode"] = subframe >> 232 & 0x3F
        # elif gnss == x and sigid == x:
        # TODO add other subframe processing algorithms here...
        # (would need 'tow equivalent' for GLONASS time system
        # for use as nominal epoch?)
        return output
