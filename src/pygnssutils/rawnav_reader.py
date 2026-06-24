"""
rawnav_reader.py

The RawNavReader class implements methods to facilitate acquisition
of raw NAV subframe data from UBX RXM-SFRBX messages.

RXM-SFRBX structures for each GNSS are documented in the "Broadcast
navigation data" section of the receiver's Integration Manual e.g.

ZED-F9P:
https://www.u-blox.com/sites/default/files/ZED-F9P_IntegrationManual_UBX-18010802.pdf
ZED-X20P:
https://www.u-blox.com/sites/default/files/documents/ZED-X20P_IntegrationManual_UBXDOC-963802114-12901.pdf

Created on 20 Apr 2026

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2026
:license: BSD 3-Clause
"""

# pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-instance-attributes

from types import NoneType

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


class RawNavReader:
    """
    Raw Navigation Reader Class.
    """

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

        - GPS LNAV subframe = 300 bits; 10 * 32-bit dwrds with each dwrd padded
          with 2 bits at end

        - GPS CNAV subframe = 300 bits; 10 * 32-bit dwrds with 20 bits padding at end

        :param str gnss: RINEX gnss code e.g. "G"
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
        dataid = 0

        if sigcode == "1C":  # GPS LNAV
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}") & 0xFFFFFFFC >> 2
                subframe += wrd << (30 * (numw - 1 - i))
            subframeid = (subframe >> 248) & 0b111
            if subframeid in (4, 5):
                dataid = (subframe >> 238) & 0b11
                subframepageid = subframe >> 232 & 0b111111

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
            "dataid": dataid,
            "subframepageid": subframepageid,
            "subframe": subframe,
        }

    def _process_rxm_sfrbx_gal(
        self, gnss: str, svid: int, sigcode: str, numw: int, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble GALILEO subframe from individual UBX RXM-SFRBX dwrds.

        - GAL FNAV subframe = 244 bits; 8 * 32-bit dwrds with 12 bits padding at end

        - GAL INAV subframe = 256 bits; 8 * 32-bit dwrds with subframe data separated
          into 112 msb and 16 lsb (see GAL_INAV_SUBFRAME)

        :param str gnss: RINEX gnss code e.g. "E"
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

        if sigcode == "5I":  # GAL FNAV
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframe = (
                subframe >> 12
            ) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF  # (2**244 - 1)
            subframeid = (subframe >> 238) & 0b111111

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

        :param str gnss: RINEX gnss code e.g. "C"
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

        - GLO subframe = 85 bits; 3 * 32-bit dwrds with 11 bits padding at end,
          plus a receiver-generated 4th dwrd containing superframe and frame ids

        :param str gnss: RINEX gnss code e.g. "R"
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
        freqid = data.freqId

        if sigcode in ("1C",):  # GLO L1OF
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            # strip padding & 4th dwrd, leaving 85 bit subframe
            subframe = (subframe >> 43) & 0x1FFFFFFFFFFFFFFFFFFFFF  # 2**85-1
            subframeid = (subframe >> 80) & 0b01111

        return {
            "gnss": gnss,
            "svid": svid,
            "sigcode": sigcode,
            "subframeid": subframeid,
            "subframepageid": subframepageid,
            "subframe": subframe,
            "freqid": freqid,
        }

    def _process_rxm_sfrbx_sba(
        self, gnss: str, svid: int, sigcode: str, numw: int, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble SBAS subframe from individual UBX RXM-SFRBX dwrds.

        - SBAS subframe = 250 bits; 8 * 32-bit dwrds with 6 bits padding at end

        :param str gnss: RINEX gnss code e.g. "S"
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

        if sigcode == "1C":  # SBAS L1C/A
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframe = (
                subframe >> 6
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

        - QZSS LNAV L1C/A subframe = 300 bits; 10 * 32-bit dwrds with each
          dwrd padded with 2 bits at end (same as GPS LNAV)

        - QZSS CNAV L2C, L5I, subframe = 300 bits; 10 * 32-bit dwrds with 20 bits padding
          at end (same as GPS CNAV)

        - QZSS CNV2 L1S subframe = 250 bits; 8 * 32-bit dwrds with 6 bits padding
          at end (same as SBAS L1C/A)

        :param str gnss: RINEX gnss code e.g. "J"
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
        dataid = 0

        if sigcode == "1C":  # QZSS L1C/A - LNAV
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}") & 0xFFFFFFFC >> 2
                subframe += wrd << (30 * (numw - 1 - i))
            subframeid = (subframe >> 248) & 0b111
            if subframeid in (4, 5):
                dataid = (subframe >> 238) & 0b11
                subframepageid = (subframe >> 232) & 0b111111

        elif sigcode in (
            "2L",
            "2S",
            "5I",
        ):  # QZSS L2C, L5I - CNAV
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframe = (
                (subframe >> 20)
                & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
            )  # (2**300 - 1)
            subframeid = (subframe >> 280) & 0b111111

        elif sigcode == "1Z":  # QZSS L1C - CNV2
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
            "dataid": dataid,
            "subframepageid": subframepageid,
            "subframe": subframe,
        }

    def _process_rxm_sfrbx_irn(
        self, gnss: str, svid: int, sigcode: str, numw: int, data: UBXMessage
    ) -> dict[str, str | int | float | NoneType]:
        """
        Reassemble IRNSS (NAVIC) subframe from individual UBX RXM-SFRBX dwrds.

        - IRN L5A subframe = 292 bits; 10 * 32-bit dwrds with 28 bits padding
          at end

        :param str gnss: RINEX gnss code e.g. "I"
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

        if sigcode in ("5A",):  # IRN L5A
            for i in range(numw):
                wrd = getattr(data, f"dwrd_{i+1:02d}")
                subframe += wrd << (32 * (numw - 1 - i))
            subframe = (
                (subframe >> 28)
                & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
            )  # (2**292 - 1)
            subframeid = ((subframe >> 263) & 0b11) + 1  # remember to add 1
            if subframeid in (3, 4):
                subframepageid = (subframe >> 256) & 0b111111

        return {
            "gnss": gnss,
            "svid": svid,
            "sigcode": sigcode,
            "subframeid": subframeid,
            "subframepageid": subframepageid,
            "subframe": subframe,
        }
