"""
rawnav.py

The RawNav class parses and stores the individual attributes
(ephemerides, ionospheric & clock corrections, etc.) of one
or more raw GNSS NAV subframes.

Once a RawNav object is instantiated, the `parse` function can
be invoked repeatedly to collate data from separate sequential
subframes e.g. for GPS LNAV, subframe 1 contains clock corrections,
subframes 2 & 3 contain ephemerides and subframe 4 page 18 contains
ionospheric corrections.

An `subframeacq` bitfield signifies which subframe/page IDs have
been acquired, and hence whether or not the RawNav frame contains
sufficient information to be converted to a NAV record e.g. as a
precursor to RINEX conversion.

The objective is to handle any GNSS subframe format for which:

 - the complete, unpadded subframe is represented as an unsigned little-endian
   integer.
 - the subframe definition dictionary has been transcribed from the relevant
   GNSS ICD (Interface Control Document) with standardized ascii
   field names e.g. `omegadot`, `sqrta`, `cus`, `tauc`, etc.

Format of subframe definition dictionary::

   dict[field_name, tuple[offset, length, encoding, scaling]

where offset and length are in bits (see, for example,
`rawnav_subframes_gps.py`).

MSB, ISB (intermediate bits) and LSB field names MUST be suffixed "_msb",
"_isb" and "_lsb" respectively - the `parse` function will automatically
combine them.

Created on 20 Apr 2026

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2026
:license: BSD 3-Clause
"""

# pylint: disable=too-many-arguments, too-many-positional-arguments

import struct
from logging import getLogger
from typing import Literal

from pygnssutils.exceptions import RINEXProcessingError
from pygnssutils.rinex_globals import GLO
from pygnssutils.rinex_helpers import get_svcode

IS1 = "_is1"
"""IS1 field name suffix (between MSB and ISB)"""
ISB = "_isb"
"""ISB field name suffix (between MSB/IS1 and LSB)"""
LSB = "_lsb"
"""LSB field name suffix"""
MSB = "_msb"
"""MSB field name suffix"""
TOC = "toc"
"""TOC (time of clock) field name - used to establish epoch"""
TOW = "tow"
"""HOW TOW field name"""
SID = "sid"
"""subframe id field name"""
SPID = "spid"
"""subframe page id field name"""
WN = "wn"
"""WN (week number) field name - used to establish epoch"""

PREAMBLE = "_preamble"
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
        sigcode: str,
        **kwargs,  # pylint: disable=unused-argument
    ):
        """
        Constructor.

        :param Literal["G","R","E","C","J","S","I"] gnss: GNSS code
        :param int svid: RINEX SV id e.g. 14
        :param str sigcode: RINEX signal code e.g. "1C"
        :param dict kwargs: optional keyword arguments
        """

        self._logger = getLogger(__name__)
        self._gnss = gnss
        self._svid = svid
        self._sigcode = sigcode
        if gnss != GLO:
            self.wn = -1
            self.toc = -1
            self.tow = -1
        self._subframeacq = 0
        self._msb = {}
        self._isb = {}
        self._is1 = {}
        self._lsb = {}
        self._firsttoc = 999999999
        self._lasttoc = 0
        self._firstwn = 999999999
        self._lastwn = 0

    def parse(
        self,
        data: int,
        subframedef: dict[str, tuple[int, int, str, int]],
        subframeacq: int,
        sequence: bool = True,
    ):
        """
        Parse raw subframe data into its constituent attributes.

        :param int data: raw, unpadded input data
        :param dict[str, tuple[int, int, str, int]] subframedef: subframe \
           definition dictionary (from GNSS ICD)
        :param int subframeacq: subframe acquisition bitmask
        :param bool sequence: process subframe as part of a contiguous sequence (True)
        :raises: RINEXProcessingError
        """

        try:

            # get exemplary preamble value if one is available
            valpre = subframedef.pop(VALPREAMBLE, 0)

            # get total subframe length in bits
            offset, bitlen, _, _ = list(subframedef.values())[-1]
            sfrlen = offset + bitlen

            # parse each attribute in subframe, combining MSB, ISB and
            # LSB fields where appropriate
            for att, (offset, length, encoding, scaling) in subframedef.items():

                if att[0:1] == "_":  # ignore non-data attributes
                    continue
                bits = data >> (sfrlen - offset - length) & (2**length - 1)

                # validate preamble if an exemplary value is available
                if valpre and att == PREAMBLE and bits != valpre:
                    raise RINEXProcessingError(
                        f"Invalid preamble - expected 0b{valpre:b}, got 0b{bits:b}"
                    )

                # recombine MSB, IS1, ISB and LSB bits
                if att[-4:].lower() == MSB:  # most significant bits
                    self._msb[att] = (bits, length, encoding, scaling)
                    continue
                if att[-4:].lower() == IS1:  # intermediate bits 1 (BDS)
                    self._is1[att] = (bits, length, encoding, scaling)
                    continue
                if att[-4:].lower() == ISB:  # intermediate bits (BDS)
                    self._isb[att] = (bits, length, encoding, scaling)
                    continue
                if att[-4:].lower() == LSB:  # least significant bits
                    attns = att[:-4]
                    msbbits, msblen, _, _ = self._msb.pop(f"{attns}{MSB}", (0, 0, 0, 0))
                    is1bits, is1len, _, _ = self._is1.pop(f"{attns}{IS1}", (0, 0, 0, 0))
                    isbbits, isblen, _, _ = self._isb.pop(f"{attns}{ISB}", (0, 0, 0, 0))
                    bits = (
                        (msbbits << (is1len + isblen + length))
                        + (is1bits << (isblen + length))
                        + (isbbits << length)
                        + bits
                    )
                    if msblen:  # if combining with msb...
                        att = attns  # strip "_lsb" suffix
                    length += msblen + is1len + isblen

                val = self._bits2val(bits, length, encoding, scaling)
                setattr(self, att, val)

                if att in (SID, SPID):  # update subframe acquisition status
                    self._subframeacq |= subframeacq

            if not sequence:
                self._store_orphaned_msb()

        except (ValueError, TypeError, KeyError) as err:
            raise RINEXProcessingError(
                "Invalid subframe definition dictionary."
            ) from err

    def _store_orphaned_msb(self):
        """
        If not processing sequentially, store any 'orphaned' MSB/IS1 now rather
        than waiting for associated ISB/LSB from next subframe in sequence.
        """

        for msb in (self._msb, self._is1):
            for att, (bits, length, encoding, scaling) in msb.items():
                val = self._bits2val(bits, length, encoding, scaling)
                setattr(self, att, val)
            msb = {}

    def _bits2val(
        self, vali: int, length: int, encoding: str, scaling: int
    ) -> int | float:
        """
        Convert encoded bits to value.

        :param int vali: value as raw integer
        :param int length: length in bits
        :param str encoding: bit encoding e.g. U, S, N, F
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

        stg = (
            f"<RAWNAV({self.identity}, gnss={self._gnss}, svid={self._svid}, "
            f"sigid={self._sigcode}, sfracq={self._subframeacq}, "
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

        svcode = get_svcode(self._gnss, self._svid, leadzero=True)
        return f"{svcode}{self._sigcode}"

    @property
    def gnss(self) -> str:
        """
        Getter for GNSS code e.g. "G"

        :return: gnss
        :rtype: str
        """

        return self._gnss

    @property
    def svid(self) -> int:
        """
        Getter for SV id e.g. 14

        :return: svid
        :rtype: int
        """

        return self._svid

    @property
    def svcode(self) -> str:
        """
        Getter for SV code (gnss & prn).

        :return: svcode e.g. "G14"
        :rtype: str
        """

        return get_svcode(self._gnss, self._svid, leadzero=False)

    @property
    def sigcode(self) -> str:
        """
        Getter for signal code in RINEX format.

        :return: signal code e.g. '1C'
        :rtype: str
        """

        return self._sigcode

    @property
    def subframeacq(self) -> int:
        """
        Getter for subframe acquisition status.

        Bitfield signifying which subframe IDs have been acquired:

        - subframeacq & 0b001 => page 1
        - subframeacq & 0b010 => page 2,
        - subframeacq & 0b100 => page 3, etc.

        :return: subframe acquisition status.
        :rtype: int
        """

        return self._subframeacq
