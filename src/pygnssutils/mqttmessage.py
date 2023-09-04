"""
mqttmessage.py

MQTTMessage container class for MQTT topics with json payloads.

Created on 1 Sep 2023

:author: semuadmin
:copyright: SEMU Consulting © 2020
:license: BSD 3-Clause
"""

from io import BytesIO
from json import JSONDecodeError, load


class MQTTMessage:
    """
    Container class for MQTT topics with json payloads.
    """

    def __init__(self, topic: str, payload: bytes):
        """
        Constructor

        :param str topic: MQTT topic e.g. "\\\\pp\\\\frequencies\\\\Lb"
        :param bytes payload: MQTT topic json payload as bytes
        :raises: ValueError if payload is invalid json
        """

        self.identity = topic.upper()
        try:
            payjson = load(BytesIO(payload))
            self._parse_payload(payjson)
        except JSONDecodeError as err:
            raise ValueError(
                f"Topic {topic} payload was not valid json - {err}"
            ) from err

    def __str__(self) -> str:
        """
        Human readable representation.

        :return: human readable representation
        :rtype: str
        """

        stg = f"<MQTT({self.identity}, "
        for i, att in enumerate(self.__dict__):
            if att[0] != "_" and att != "identity":  # only show public attributes
                dlm = ", " if i < len(self.__dict__) - 1 else ""
                stg += f"{att}={self.__dict__[att]}{dlm}"
        stg += ")>"
        return stg

    def _parse_payload(self, pay: dict, att: str = ""):
        """
        Recursively traverse json payload structure and set
        attribute for each element value.

        :param dict pay: json payload as dict
        :param str att: attribute name
        """

        tmp = att
        if isinstance(pay, dict):  # nested elements
            for key, val in pay.items():
                if len(pay) > 1:  # element group
                    att = tmp + key + "_"
                else:
                    att += key + "_"
                self._parse_payload(val, att)
        else:  # value
            setattr(self, att[:-1], pay)
