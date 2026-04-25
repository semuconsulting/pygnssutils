"""
UBX Custom Exception Types

Created on 27 Sep 2020

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2020
:license: BSD 3-Clause
"""


class ParameterError(Exception):
    """Parameter Error Class."""


class GNSSError(Exception):
    """
    Master GNSS Error Class.

    Any other GNSS exceptions defined here should inherit from this.
    """


class RINEXError(Exception):
    """
    Master RINEX Error Class.

    Any other RINEX conversion exceptions defined here should inherit from this.
    """


class GNSSStreamError(GNSSError):
    """Generic GNSS Stream Error Class."""


class RINEXProcessingError(RINEXError):
    """Generic RINEX Conversion Error Class."""
