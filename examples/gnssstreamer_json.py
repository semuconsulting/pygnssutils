"""
pygnssutils - gnssstreamer_json.py

This example illustrates how to use GNSSStreamer in
conjunction with a text File as an external output handler
to create an array of GNSS messages in JSON format.

Usage:

python3 gnssstreamer_json.py jsonfile="jsonfile.json" inport="/dev/ttyACM0" limit=50

The file will be written to the user's HOME directory
by default, and can be read by any JSON parser.

Created on 28 May 2022

@author: semuadmin
"""

import os
from sys import argv

from pygnssutils import FORMAT_JSON, GNSSStreamer


def main(**kwargs):
    """
    Main routine.
    """

    jsonfile = kwargs.get(
        "jsonfile", os.path.join(os.path.expanduser("~"), "jsonfile.json")
    )
    inport = kwargs.get("inport", "/dev/ttyACM0")
    limit = int(kwargs.get("limit", 50))  # 0 = unlimited, CRTL-C to terminate

    print(f"Opening text file {jsonfile} for write...")
    with open(jsonfile, "w", encoding="UTF-8") as jfile:
        print(f"Creating GNSSStreamer with serial port {inport}...")
        with GNSSStreamer(
            port=inport, format=FORMAT_JSON, limit=limit, outputhandler=jfile
        ) as gns:
            print("Streaming GNSS data into JSON file...")
            gns.run()
    print("Streaming ended")


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
