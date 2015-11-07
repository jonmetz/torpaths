"""
mitmdump extension that coordinates with browser.py to save all the hosts that were
contacted when a webpage is loaded
Usage: mitmdump -s proxy.py -p 8000
"""

from libmproxy.script import concurrent
import netlib
import redis

PROXY_INPUT_QUEUE = 'proxy_queue'
REDIS_CONN = redis.Redis()

@concurrent
def request(context, flow):
    """
    Intercept a request from the browser through mitmdump and store the host the
    request is going to in the queue specified in the first (and hopefully only)
    item in the PROXY_INPUT_QUEUE.

    """
    # hack around mitmdump weirdness
    if isinstance(flow.server_conn.address, netlib.tcp.Address):
        addr = flow.server_conn.address.host
    else:
        addr = flow.server_conn.address.split(':')[0]

    output_queue = REDIS_CONN.lrange('proxy_queue', 0, -1)  # get the whole queue
    assert len(output_queue) == 1  # make sure browser.py didn't mess up
    # store the host in the queue with the title output_queue[0]
    REDIS_CONN.rpush(output_queue[0], addr)
