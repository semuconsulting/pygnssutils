"""
rawnav.py

Raw navigation data container and reader classes.

The RawNavReader class implements methods to facilitate acquisition
of NAV subframe data from UBX RXM-SFRBX messages.

The RawNav class parses and stores the individual attributes
(ephemerides, ionospheric & clock corrections, etc.) of one
or more raw GNSS NAV subframes, e.g. as a precursor to RINEX
conversion.

Once a RawNav object is instantiated, the `parse` function can
be invoked repeatedly to collate data from separate sequential
subframes e.g. for GPS LNAV, subframe 1 contains clock corrections,
subframes 2 & 3 contain ephemerides and subframe 4 page 18 contains
ionospheric corrections.

An `subframeacq` bitfield signifies which subframe/page IDs have
been acquired, and hence whether or not the RawNav frame contains
sufficient information to be converted to a NAV record.

A boolean `sequence` argument determines whether subframes are
processed as a contiguous sequence e.g. for GNSS where MSB and LSB
attributes are held in separate, sequential subframes.

The objective is to handle any GNSS subframe format for which:

 - data is available as a raw, unpadded little-endian integer.
 - data definition dictionary has been transcribed from the relevant
   GNSS ICD (Interface Control Document) with standardized ascii
   field names e.g. `omegadot`, `sqrta`, `cus`, etc.

Format of data definition dictionary::

   dict[field_name, tuple[offset, length, encoding, scaling]

where offset and length are in bits (see, for example,
`rinex_subframes_gps.py`).

MSB and LSB field names MUST be suffixed "_msb" and "_lsb"
respectively - the `parse` function will automatically combine them.

RXM-SFRBX structures for each GNSS are documented in section 3.15.1 Broadcast
navigation data:

https://www.u-blox.com/sites/default/files/ZED-F9P_IntegrationManual_UBX-18010802.pdf

NB: Alpha Support currently limited to:
    - GPS LNAV, CNAV
    - GAL FNAV, INAV
    - BDS D1
... pending transcription of other GNSS ICDs.

Created on 20 Apr 2026

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2026
:license: BSD 3-Clause
"""

# pylint: disable=unused-argument, unused-variable, too-many-arguments, too-many-positional-arguments

import struct
from logging import getLogger
from types import NoneType
from typing import Literal

from pyubx2 import UBXMessage

from pygnssutils.exceptions import RINEXProcessingError
from pygnssutils.rinex_globals import (
    BDS,
    GAL,
    GLO,
    GPS,
    IRN,
    QZS,
    SBA,
    UBXRINEXGNSS,
)
from pygnssutils.rinex_helpers import get_obscode_ubx

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
        :param bool sequence: process subframe as part of a contiguous sequence (False)
        :raises: RINEXProcessingError
        """
        # pylint: disable=too-many-locals

        try:

            # get exemplary preamble value if one is available
            valpre = subframedef.pop(VALPREAMBLE, 0)

            # validate subframe length in bits
            offset, bitlen, _, _ = list(subframedef.values())[-1]
            sfrlen = offset + bitlen

            # parse each attribute in subframe, combining MSB and LSB fields
            # where appropriate
            for att, (offset, length, encoding, scaling) in subframedef.items():

                if att[0:1] == "_":  # ignore non-data bits
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
                    msbbits, msblen, _, _ = self._msb.pop(
                        f"{att[:-4]}{MSB}", (0, 0, 0, 0)
                    )
                    is1bits, is1len, _, _ = self._is1.pop(
                        f"{att[:-4]}{IS1}", (0, 0, 0, 0)
                    )
                    isbbits, isblen, _, _ = self._isb.pop(
                        f"{att[:-4]}{ISB}", (0, 0, 0, 0)
                    )
                    bits = (
                        (msbbits << (is1len + isblen + length))
                        + (is1bits << isblen + length)
                        + (isbbits << length)
                        + bits
                    )
                    if msblen:
                        att = att[:-4]
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

        return f"{self._gnss}{self._svid:02d}{self._sigcode}"

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
    def svcode(self) -> str:
        """
        Getter for SV code (gnss & prn).

        :return: svcode e.g. "G14"
        :rtype: str
        """

        return f"{self._gnss}{self._svid:>2}"  # no leading zero

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


class RawNavReader:
    """
    Raw Navigation Reader Class.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, **kwargs):  # pylint: disable=unused-argument
        """
        Constructor.

        :param dict kwargs: optional keyword arguments
        """

    def process_rxm_sfrbx(
        self, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble subframe from individual UBX RXM-SFRBX dwrds.

        :param UBXMessage data: parsed UBX RXM-SFRBX message
        :return: dict of subframe attributes
        :rtype: dict[str, str | int | float | NoneType]
        :raises: RINEXProcessingError
        """

        if isinstance(data, UBXMessage):
            if data.identity != "RXM-SFRBX":
                raise RINEXProcessingError(
                    f"Data must be UBX RXM-SFRBX message - got {type(data)}"
                )

        sfrdata = {}
        try:
            gnss = UBXRINEXGNSS[data.gnssId]
            svid = data.svId
            numw = data.numWords
            sigcode = get_obscode_ubx(data.gnssId, data.sigId)
        except KeyError as err:
            raise RINEXProcessingError(
                f"Unrecognised GNSS or Signal code: {data.gnssId=}, {data.sigId=}"
            ) from err

        if gnss == GPS:
            sfrdata = self._process_rxm_sfrbx_gps(gnss, svid, sigcode, numw, data)
        elif gnss == GAL:
            sfrdata = self._process_rxm_sfrbx_gal(gnss, svid, sigcode, numw, data)
        elif gnss == BDS:
            sfrdata = self._process_rxm_sfrbx_bds(gnss, svid, sigcode, numw, data)
        elif gnss == GLO:
            sfrdata = self._process_rxm_sfrbx_glo(gnss, svid, sigcode, numw, data)
        elif gnss == SBA:
            sfrdata = self._process_rxm_sfrbx_sba(gnss, svid, sigcode, numw, data)
        elif gnss == QZS:
            sfrdata = self._process_rxm_sfrbx_qzs(gnss, svid, sigcode, numw, data)
        elif gnss == IRN:
            sfrdata = self._process_rxm_sfrbx_irn(gnss, svid, sigcode, numw, data)
        return sfrdata

    def _process_rxm_sfrbx_gps(
        self, gnss: str, svid: int, sigcode: str, numw: int, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble GPS subframe from individual UBX RXM-SFRBX dwrds.

        :param str gnss: RINEX gnss code
        :param int svid: SV
        :param str sigcode: RINEX sig code e.g. '1C'
        :param UBXMessage data: parsed UBX RXM-SFRBX message
        :return: dict of subframe attributes
        :rtype: dict[str, str | int | float | NoneType]
        :raises: RINEXProcessingError
        """

        subframe = 0
        subframeid = 0
        subframepageid = 0

        # for GPS LNAV, subframe = 10 * 30 bits, with each 32-bit dwrd padded with 2 bits at end
        if sigcode == "1C":  # GPS LNAV
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}") & 0xFFFFFFFC >> 2
                subframe += wrd << (30 * (numw - 1 - i))
            subframeid = (subframe >> 248) & 0b111
            if subframeid in (4, 5):
                subframepageid = subframe >> 232 & 0b111111

        # for GPS CNAV, subframe = 3 * 100 bits, final 20 bits of 320 bit dwrd is padding
        elif sigcode in ("2L", "2S", "5I", "5Q"):  # GPS CNAV
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframe = (
                (subframe >> 20)
                & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
            )  # (2**300 - 1)
            subframeid = (subframe >> 280) & 0b111111

        return {
            "gnss": gnss,
            "svid": svid,
            "sigcode": sigcode,
            "subframeid": subframeid,
            "subframepageid": subframepageid,
            "subframe": subframe,
        }

    def _process_rxm_sfrbx_gal(
        self, gnss: str, svid: int, sigcode: str, numw: int, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble GALILEO subframe from individual UBX RXM-SFRBX dwrds.

        :param str gnss: RINEX gnss code
        :param int svid: SV
        :param str sigcode: RINEX sigid e.g. '5I'
        :param UBXMessage data: parsed UBX RXM-SFRBX message
        :return: dict of subframe attributes
        :rtype: dict[str, str | int | float | NoneType]
        :raises: RINEXProcessingError
        """

        subframe = 0
        subframeid = 0
        subframepageid = 0

        # for GAL FNAV, subframe = 244 bits,
        # 8 * 32 bit dwrds with 12 bits padding at end
        if sigcode == "5I":  # GAL FNAV
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframe = (
                subframe >> 12
            ) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF  # (2**244 - 1)
            subframeid = (subframe >> 238) & 0b111111

        # for GAL INAV, subframe = 256 bits, 8 * 32 bit dwrds,
        # with word data separated into 112 msb and 16 lsb
        # (see GAL_INAV_SUBFRAME)
        elif sigcode in ("1B", "7I"):  # GAL INAV
            supsubframe = 0
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                supsubframe += wrd << (32 * (numw - 1 - i))
            subframe_msb = (
                supsubframe >> 142
            ) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFF  # (2**112 - 1)
            subframe_lsb = (supsubframe >> 110) & 0xFFFF  # (2**16 - 1)
            subframe = (subframe_msb << 16) | subframe_lsb
            subframeid = (subframe >> 122) & 0b111111

        return {
            "gnss": gnss,
            "svid": svid,
            "sigcode": sigcode,
            "subframeid": subframeid,
            "subframepageid": subframepageid,
            "subframe": subframe,
        }

    def _process_rxm_sfrbx_bds(
        self, gnss: str, svid: int, sigcode: str, numw: int, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble BEIDOU subframe from individual UBX RXM-SFRBX dwrds.

        :param str gnss: RINEX gnss code
        :param int svid: SV
        :param str sigcode: RINEX sig code e.g. '2I'
        :param UBXMessage data: parsed UBX RXM-SFRBX message
        :return: dict of subframe attributes
        :rtype: dict[str, str | int | float | NoneType]
        :raises: RINEXProcessingError
        """

        subframe = 0
        subframeid = 0
        subframepageid = 0
        d1d2 = 0

        if sigcode in ("2I", "6I", "7I"):  # BDS D1/D2
            if data.sigId in (1, 3, 10):  # D2
                d1d2 = 2
            else:  # D1
                d1d2 = 1
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}") & 0xFFFFFFFC >> 2
                subframe += wrd << (30 * (numw - 1 - i))
            subframeid = (subframe >> 282) & 0b111
            if d1d2 == 1 and subframeid in (4, 5):
                subframepageid = subframe >> 250 & 0b1111111
            elif d1d2 == 2 and subframeid in (1,):
                subframepageid = subframe >> 254 & 0b1111

        elif sigcode == "1D":  # BDS CNV1
            pass  # TODO

        elif sigcode == "5D":  # BDS CNV2
            pass  # TODO

        return {
            "gnss": gnss,
            "svid": svid,
            "sigcode": sigcode,
            "d1d2": d1d2,
            "subframeid": subframeid,
            "subframepageid": subframepageid,
            "subframe": subframe,
        }

    def _process_rxm_sfrbx_glo(
        self, gnss: str, svid: int, sigcode: str, numw: int, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble GLONASS subframe from individual UBX RXM-SFRBX dwrds.

        :param str gnss: RINEX gnss code
        :param int svid: SV
        :param str sigcode: RINEX sigid e.g. '1C'
        :param UBXMessage data: parsed UBX RXM-SFRBX message
        :return: dict of subframe attributes
        :rtype: dict[str, str | int | float | NoneType]
        :raises: RINEXProcessingError
        """

        subframe = 0
        subframeid = 0
        subframepageid = 0

        # for GLO, subframe = 85 bits, 3 * 32 bit dwrds, plus
        # a receiver-generated 4th 32 dwrd containing subframe and page ids
        if sigcode in ("1C", "2C"):  # GLO L1,L2
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframepageid = (subframe >> 16) & 0xFFFF
            subframeid = subframe & 0b11111111
            subframe = (subframe >> 43) & 0x1FFFFFFFFFFFFFFFFFFFFF  # strip 4th dwrd

        return {
            "gnss": gnss,
            "svid": svid,
            "sigcode": sigcode,
            "subframeid": subframeid,
            "subframepageid": subframepageid,
            "subframe": subframe,
        }

    def _process_rxm_sfrbx_sba(
        self, gnss: str, svid: int, sigcode: str, numw: int, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble SBAS subframe from individual UBX RXM-SFRBX dwrds.

        :param str gnss: RINEX gnss code
        :param int svid: SV
        :param str sigcode: RINEX sigcode e.g. '1C'
        :param UBXMessage data: parsed UBX RXM-SFRBX message
        :return: dict of subframe attributes
        :rtype: dict[str, str | int | float | NoneType]
        :raises: RINEXProcessingError
        """

        subframe = 0
        subframeid = 0
        subframepageid = 0
        svid -= 100  # adjust SV ID range

        # for SBAS, subframe = 250 bits,
        # 8 * 32 bit dwrds with 6 bits padding at end
        if sigcode == "1C":  # SBAS L1C/A
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframe = (
                subframe >> 12
            ) & 0x3FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF  # (2**250 - 1)
            subframeid = (subframe >> 236) & 0b111111

        return {
            "gnss": gnss,
            "svid": svid,
            "sigcode": sigcode,
            "subframeid": subframeid,
            "subframepageid": subframepageid,
            "subframe": subframe,
        }

    def _process_rxm_sfrbx_qzs(
        self, gnss: str, svid: int, sigcode: str, numw: int, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble QZSS subframe from individual UBX RXM-SFRBX dwrds.

        :param str gnss: RINEX gnss code
        :param int svid: SV
        :param str sigcode: RINEX sigcode e.g. '1C'
        :param UBXMessage data: parsed UBX RXM-SFRBX message
        :return: dict of subframe attributes
        :rtype: dict[str, str | int | float | NoneType]
        :raises: RINEXProcessingError
        """

        subframe = 0
        subframeid = 0
        subframepageid = 0
        svid -= 192  # adjust SV ID range

        # for QZSS L1C/A, subframe = 10 * 30 bits, with each 32-bit dwrd padded with 2 bits at end
        # same as GPS LNAV
        if sigcode == "1C":  # QZSS L1C/A
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}") & 0xFFFFFFFC >> 2
                subframe += wrd << (30 * (numw - 1 - i))
            subframeid = (subframe >> 248) & 0b111
            if subframeid in (4, 5):
                subframepageid = subframe >> 232 & 0b111111

        # for QZSS L1S, subframe = 250 bits, 8 * 32 bit dwrds with 6 bits padding at end
        # same as SBAS L1C/A
        if sigcode == "1Z":  # QZSS L1S
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframe = (
                subframe >> 12
            ) & 0x3FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF  # (2**250 - 1)
            subframeid = (subframe >> 236) & 0b111111

        # for QZSS L2C, L5I, subframe = 3 * 100 bits, final 20 bits of 320 bit dwrd is padding
        # same as GPS CNAV
        elif sigcode in (
            "2L",
            "2S",
            "5I",
        ):  # QZSS L2C, L5I
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframe = (
                (subframe >> 20)
                & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
            )  # (2**300 - 1)
            subframeid = (subframe >> 280) & 0b111111

        return {
            "gnss": gnss,
            "svid": svid,
            "sigcode": sigcode,
            "subframeid": subframeid,
            "subframepageid": subframepageid,
            "subframe": subframe,
        }

    def _process_rxm_sfrbx_irn(
        self, gnss: str, svid: int, sigcode: str, numw: int, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble IRNSS (NAVIC) subframe from individual UBX RXM-SFRBX dwrds.

        :param str gnss: RINEX gnss code
        :param int svid: SV
        :param str sigcode: RINEX sigcode e.g. '5A'
        :param UBXMessage data: parsed UBX RXM-SFRBX message
        :return: dict of subframe attributes
        :rtype: dict[str, str | int | float | NoneType]
        :raises: RINEXProcessingError
        """

        subframe = 0
        subframeid = 0
        subframepageid = 0

        # for IRN L5A, subframe = 3 * 100 bits, final 20 bits of 320 bit dwrd is padding
        # same as GPS CNAV
        if sigcode in ("5A",):  # IRN L5A
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframe = (
                (subframe >> 20)
                & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
            )  # (2**300 - 1)
            subframeid = (subframe >> 280) & 0b111111

        return {
            "gnss": gnss,
            "svid": svid,
            "sigcode": sigcode,
            "subframeid": subframeid,
            "subframepageid": subframepageid,
            "subframe": subframe,
        }
