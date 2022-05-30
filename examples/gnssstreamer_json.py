"""
pygnssutils - gnssstreamer_json.py

This example illustrates how to use GNSSStreamer in
conjunction with a text File as an external output handler
to create an array of GNSS messages in JSON format.

The file will be written to the user's HOME directory
by default, and can be read by any JSON parser.

Created on 28 May 2022

@author: semuadmin
"""

import os
from pygnssutils import GNSSStreamer, FORMAT_JSON

# amend as required...
JSONFILE = os.path.join(os.path.expanduser("~"), "jsonfile.json")
INPORT = "/dev/tty.usbmodem141101"
LIMIT = 50  # 0 = unlimited, CRTL-C to terminate

print(f"Opening text file {JSONFILE} for write...")
with open(JSONFILE, "w", encoding="UTF-8") as jfile:
    print(f"Creating GNSSStreamer with serial port {INPORT}...")
    with GNSSStreamer(
        port=INPORT, format=FORMAT_JSON, limit=LIMIT, allhandler=jfile
    ) as gns:
        print("Streaming GNSS data into JSON file...")
        gns.run()
print("Streaming ended")
