"""
gnssjson.py

This simple example illustrates how to use a Text File as
an external protocol handler to create a file containing a 
JSON array of GNSS messages.

Created on 28 May 2022

@author: semuadmin
"""

PORT = "/dev/tty.usbmodem141101"  # amend as required
LIMIT = 50  # amend as required, 0 = unlimited

from pygnssutils import GNSSStreamer, FORMAT_JSON

with open("jsonfile.json", "w") as jfile:
    gns = GNSSStreamer(port=PORT, format=FORMAT_JSON, limit=LIMIT, allhandler=jfile)
    gns.run()
