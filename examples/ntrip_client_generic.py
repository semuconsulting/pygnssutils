"""
ntrip_client_generic.py

Illustration of a threaded NTRIP client using the GNSSNTRIPClient
class from pygnssutils. This example is intended to serve as a
generic pattern for any user application requiring an NTRIP data
stream.

Implements 2 daemon threads:

- ntripthread, runs the NTRIP client
- datathread, processes the output data

Data is passed between the threads using queues.

Usage (run from /examples folder):

python3 ntrip_client_generic.py server="yourcaster" https=0 port=2101 datatype="RTCM" \
    user="youruser" password="yourpassword" mountpoint="yourmountpoint" ggainterval=-1 \
    reflat=12.34567 reflon=12.34567 reflat=12.34567 refsep=12.34567

NB: If your NTRIP caster requires GGA position sentences, ggainterval MUST be set to > 0
(typically 10-60 seconds) and valid fixed reference coordinates MUST be provided.

Created on 12 Feb 2023

:author: semuadmin
:copyright: SEMU Consulting © 2023
:license: BSD 3-Clause
"""

# pylint: disable=invalid-name, global-statement

from logging import getLogger
from queue import Queue
from sys import argv
from threading import Event, Thread
from time import sleep

from pygnssutils import VERBOSITY_MEDIUM, GNSSNTRIPClient, set_logging

globalcount = 0


def ntripthread(outqueue: Queue, stopevent: Event, **kwargs):
    """
    NTRIP client thread.

    :param Queue outqueue: output queue
    :param Event stopevent: stop event
    :param dict kwargs: user-defined keyword arguments
    """

    gnc = GNSSNTRIPClient()
    gnc.run(
        server=kwargs.get("server", "rtk2go.com"),
        port=kwargs.get("port", 2101),
        https=kwargs.get("https", 0),
        mountpoint=kwargs.get("mountpoint", ""),
        datatype=kwargs.get("datatype", "RTCM"),
        ntripuser=kwargs.get("user", "myuser@mydomain.com"),
        ntrippassword=kwargs.get("password", "mypassword"),
        ggainterval=kwargs.get("ggainterval", -1),
        ggamode=1,  # fixed reference coordinates
        reflat=kwargs.get("reflat", 0.0),
        reflon=kwargs.get("reflon", 0.0),
        refalt=kwargs.get("refalt", 0.0),
        refsep=kwargs.get("refsep", 0.0),
        output=outqueue,
    )
    while not stopevent.is_set():
        sleep(3)


def datathread(outqueue: Queue, stopevent: Event, **kwargs):
    """
    Data processing thread.

    :param Queue outqueue: output queue
    :param Event stopevent: stop event
    :param dict kwargs: user-defined keyword arguments
    """

    global globalcount
    while not stopevent.is_set():
        while not outqueue.empty():
            raw, parsed = outqueue.get()

            # do whatever you want to do with the raw or parsed data here...
            print(f"\n{kwargs.get("datatype","RTCM")} data received: {parsed.identity}")
            print(parsed)

            # when finished, mark queued task as done...
            globalcount += 1
            outqueue.task_done()


def main(**kwargs):
    """
    Main routine.
    """

    global globalcount
    globalcount = 0
    logger = getLogger("pygnssutils.gnssntripclient")
    set_logging(logger, VERBOSITY_MEDIUM)
    outqueue = Queue()
    stopevent = Event()

    # define the threads which will run in the background until terminated by user
    dt = Thread(
        target=datathread, args=(outqueue, stopevent), kwargs=kwargs, daemon=True
    )
    nt = Thread(
        target=ntripthread,
        args=(outqueue, stopevent),
        kwargs=kwargs,
        daemon=True,
    )
    # start the threads
    dt.start()
    nt.start()

    print("NTRIP client and processor threads started - press CTRL-C to terminate...")
    try:
        while True:
            sleep(3)
    except KeyboardInterrupt:
        # stop the threads
        stopevent.set()
        print(
            "NTRIP client terminated by user, waiting for data processing to complete..."
        )

    # wait for final queued tasks to complete
    nt.join()
    dt.join()

    print(f"Data processing complete, {globalcount} records processed")


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
