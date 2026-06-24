"""
rawnav.py

The RawNav class parses and stores the individual attributes
(ephemerides, ionospheric & clock corrections, etc.) of one
or more raw GNSS NAV subframes.

Once a RawNav object is instantiated, the `parse` function can
be invoked repeatedly to collate data from separate sequential
subframes e.g. for GPS LNAV:

 - subframe 1 contains clock corrections.
 - subframes 2 & 3 contain ephemerides.
 - subframe 4 page 56 contains ionospheric corrections.
 - subframes 5 pages 1-24 and 4 pages 25-32 contain almanac data.
 - etc.

A `subframeacq` bitfield signifies which subframe/page IDs have
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

   dict[attribute_name, tuple[length, encoding, scaling]

where

 - length = attribute length in bits
 - encoding = U (unsigned integer) or S (two's complement signed integer)
 - scaling = scaling factor (resolution) as integer or float (0 = no scaling)

See, for example, `rawnav_subframes_gps.py`.

MSB, ISB (intermediate bits) and LSB field names MUST be suffixed "_msb",
"_is1"/"_isb" and "_lsb" respectively - the `parse` function will automatically
combine them.

Created on 20 Apr 2026

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2026
:license: BSD 3-Clause
"""

# pylint: disable=too-many-arguments, too-many-positional-arguments

from logging import getLogger
from typing import Literal

from pygnssutils.exceptions import RINEXProcessingError
from pygnssutils.rinex_globals import GLO, GPS, SBA
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
SVIDALM = "svidalm#"
"""current satellite number (slot) in almanac message"""

PREAMBLE = "_preamble"
SUBFRAMELENGTH = "_subframelength"
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
            self.wn = None
            self.toc = None
            self.tow = None
        self._subframeacq = 0
        self._msb = {}
        self._isb = {}
        self._is1 = {}
        self._lsb = {}
        self._firsttoc = 999999999
        self._lasttoc = 0
        self._firstwn = 999999999
        self._lastwn = 0
        self._svidalm = 0

    def parse(
        self,
        data: int,
        subframedef: dict[str, int | tuple[int, int, str, int]],
        subframeacq: int,
        sequence: bool = True,
    ):
        """
        Parse raw subframe data into its constituent attributes.

        :param int data: raw, unpadded input data
        :param dict[str, int | tuple[int, int, str, int]] subframedef: subframe \
           definition dictionary (from GNSS ICD)
        :param int subframeacq: subframe acquisition bitmask
        :param bool sequence: process subframe as part of a contiguous sequence (True)
        :raises: RINEXProcessingError
        """

        errstr = ""
        try:

            subframelen = subframedef[SUBFRAMELENGTH]
            if not isinstance(subframelen, int):
                errstr = f". Subframe length must be integer, not {subframelen}"
                raise TypeError("Invalid subframe length")

            offset = 0  # payload offset in bits
            index = []  # array of (nested) group indices
            for anam in subframedef:  # process each attribute in subframe definition
                errstr = f". Error processing `{anam}`"
                offset, index = self._set_attribute(
                    data, subframedef, subframelen, subframeacq, anam, offset, index
                )

            # check final offset is same as defined subframe length
            if offset != subframelen:
                errstr = f". Final offset {offset} does not match subframe length {subframelen}"
                raise ValueError("Invalid offset")

            if not sequence:
                self._store_orphaned_msb()

        except (ValueError, TypeError, KeyError) as err:
            raise RINEXProcessingError(
                f"Invalid subframe definition for {self.identity}{errstr}."
            ) from err

    def _set_attribute(
        self,
        data: int,
        subframedef: dict,
        subframelen: int,
        subframeacq: int,
        anam: str,
        offset: int,
        index: list,
    ) -> tuple:
        """
        Recursive routine to set individual, alternate or grouped subframe attributes.

        :param int data: raw, unpadded input data
        :param dict[str, int | tuple[int, int, str, int]] subframedef: subframe \
           definition dictionary (from GNSS ICD)
        :param int subframelen: subframe length in bits
        :param int subframeacq: subframe acquisition bitmask
        :param str anam: attribute name
        :param int offset: payload offset in bits
        :param list index: repeating group index array
        :return: (offset, index[])
        :rtype: tuple

        """

        adef = subframedef[anam]  # get attribute definition
        if isinstance(adef, int):  # non-parsable reference attribute
            return offset, index
        if "_grp" in anam:  # repeating attribute group
            offset, index = self._set_attribute_group(
                data, subframelen, subframeacq, adef, offset, index
            )
        elif "_alt" in anam:  # alternate attribute group
            offset, index = self._set_attribute_alternate(
                data, subframelen, subframeacq, adef, offset, index
            )
        else:  # single attribute
            offset = self._set_attribute_single(
                data,
                subframelen,
                subframeacq,
                offset,
                index,
                anam,
                adef,
            )

        return offset, index

    def _set_attribute_alternate(
        self,
        data: int,
        subframelen: int,
        subframeacq: int,
        adef: tuple[tuple[str, int], dict],
        offset: int,
        index: list[int],
    ) -> tuple:
        """
        Process alternate group of attributes - group is present if attribute value
        = specific value, otherwise absent.

        :param int data: raw, unpadded input data
        :param int subframelen: subframe length in bits
        :param int subframeacq: subframe acquisition bitmask
        :param tuple[tuple[str, int], dict] adef: attribute definition
        :param int offset: payload offset in bits
        :param list[int] index: repeating group index array
        :return: (offset, index[])
        :rtype: tuple
        """

        (anam, con), gdict = adef  # (attribute name, condition), group dictionary
        if getattr(self, anam) == con:  # if condition is met...
            # recursively process each group attribute,
            # incrementing the payload offset as we go
            for anamg in gdict:
                offset, index = self._set_attribute(
                    data, gdict, subframelen, subframeacq, anamg, offset, index
                )

        return offset, index

    def _set_attribute_group(
        self,
        data: int,
        subframelen: int,
        subframeacq: int,
        adef: tuple[str, dict],
        offset: int,
        index: list[int],
    ) -> tuple:
        """
        Process (nested) group of attributes.

        :param int data: raw, unpadded input data
        :param int subframelen: subframe length in bits
        :param int subframeacq: subframe acquisition bitmask
        :param tuple[str, dict] adef: attribute definition
        :param int offset: payload offset in bits
        :param list[int] index: repeating group index array
        :return: (offset, index[])
        :rtype: tuple

        """

        anam, gdict = adef  # attribute signifying group size, group dictionary
        # derive or retrieve number of items in group
        if isinstance(anam, int):  # fixed number of repeats
            gsiz = anam
        else:  # number of repeats is defined in named attribute
            gsiz = getattr(self, anam)

        index.append(0)  # add a (nested) group index level
        ic = self._get_index_continuation()
        # recursively process each group attribute,
        # incrementing the payload offset and index as we go
        for i in range(gsiz):
            index[-1] = i + ic + 1
            for anamg in gdict:
                offset, index = self._set_attribute(
                    data, gdict, subframelen, subframeacq, anamg, offset, index
                )

        index.pop()  # remove this (nested) group index

        return offset, index

    def _set_attribute_single(
        self,
        data: int,
        subframelen: int,
        subframeacq: int,
        offset: int,
        index: list[int],
        anam: str,
        adef: tuple[int, str, int | float],
    ) -> int:
        """
        Parse individual attribute.

        :param int data: raw, unpadded input data
        :param int subframelen: total subframe length
        :param int subframeacq: subframe acquisition bitmask
        :param int offset: subframe bit offset
        :param list[int] index: repeating group index array
        :param str anam: attribute name
        :param tuple[int, str, int | float] adef: attribute definition
        :return: new offset
        :rtype: int
        """

        length, encoding, scaling = adef
        clength = length  # combined length of MSB, ISB, LSB
        bits = data >> (subframelen - offset - length) & ((1 << length) - 1)

        # recombine MSB, IS1, ISB and LSB bits
        if anam[-4:].lower() == MSB:  # most significant bits
            self._msb[anam] = (bits, length, encoding, scaling)
            return offset + length
        if anam[-4:].lower() == IS1:  # intermediate bits 1 (BDS)
            self._is1[anam] = (bits, length, encoding, scaling)
            return offset + length
        if anam[-4:].lower() == ISB:  # intermediate bits (BDS)
            self._isb[anam] = (bits, length, encoding, scaling)
            return offset + length
        if anam[-4:].lower() == LSB:  # least significant bits
            attns = anam[:-4]
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
                anam = attns  # strip "_lsb" suffix
            clength += msblen + is1len + isblen

        # get value of attribute
        val = self._bits2val(bits, clength, encoding, scaling)

        # if attribute represents current almanac svid, store value
        if anam == SVIDALM:
            self._svidalm = val

        # if attribute is part of a (nested) repeating group, append name with index
        anami = anam
        for i in index:  # one index for each nested level
            if i > 0:
                anami += f"_{i:02d}"

        # if almanac attribute, append name with stored almanac svid
        # (GLO needs fudge as cna# & mna# precede svidalm#)
        svidalm = (
            self._svidalm + 1
            if self.gnss == GLO and anam in ("cna#", "mna#")
            else self._svidalm
        )
        anami = anami.replace("#", f"_{svidalm:03d}")

        # add attribute to RawNav instance
        if getattr(self, anami, None) is None:
            setattr(self, anami, val)

        # update subframe acquisition status
        acq = (
            (SID, SPID, SVIDALM)
            if (self.gnss == GPS and self.sigcode == "1C")
            else (SID, SPID)
        )
        if anam in acq:
            self._subframeacq |= subframeacq

        return offset + length

    def _get_index_continuation(self) -> int:
        """
        Special processing for messages with alternate repeating
        groups (e.g. SBAS MT25) to retain consistent index numbering.

        :return: index continuation
        :rtype: int
        """

        ic = 0
        if self.gnss == SBA and getattr(self, "velcode2", None) is not None:
            if getattr(self, "velcode1", None) == 0:
                ic = 2
            elif getattr(self, "velcode1", None) == 1:
                ic = 1
        return ic

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
        self, vali: int, length: int, encoding: str, scaling: int | float
    ) -> int | float:
        """
        Convert encoded bits to value.

        :param int vali: value as raw integer
        :param int length: length in bits
        :param str encoding: bit encoding e.g. U, S, N, F
        :param int | float scaling: scaling factor (0 = no scaling)
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
        # elif encoding == "F":  # IEEE 754 32 bit floating point
        #     valb = int.to_bytes(vali, 4, "little")
        #     val = struct.unpack("<f", valb)[0]
        # elif encoding == "D":  # IEEE 754 64 bit double floating point
        #     valb = int.to_bytes(vali, 8, "little")
        #     val = struct.unpack("<d", valb)[0]
        else:
            raise ValueError(f"Unknown attribute type {encoding}.")
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
            f"sigid={self._sigcode}, sfracq={self._subframeacq}"
        )
        for att, val in self.__dict__.items():
            if att[0] != "_":  # only show public attributes
                stg += f", {att}={val}"
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
