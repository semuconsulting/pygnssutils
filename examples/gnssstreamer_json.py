"""
gnssstreamer_json.py

This simple example illustrates how to use GNSSStreamer in
conjunction with a Text File as an external output handler
to create a file containing a JSON file containing an array
of GNSS messages.

The file will be written to the user's HOME directory 
by default.

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
with open(JSONFILE, "w") as jfile:
    print(f"Creating GNSSStreamer with serial port {INPORT}...")
    with GNSSStreamer(
        port=INPORT, format=FORMAT_JSON, limit=LIMIT, allhandler=jfile
    ) as gns:
        print("Streaming GNSS data into JSON file...")
        gns.run()
print("Streaming ended")
