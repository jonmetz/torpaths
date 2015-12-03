import re
import netlib
from multiprocessing import Process, Queue
import threading
from libmproxy import controller, proxy
from libmproxy.proxy.server import ProxyServer

BLACKLIST = {
    'search.services.mozilla.com',
    'tiles.services.mozilla.com',
    'tiles-cloudfront.cdn.mozilla.net',
    'tracking-protection.cdn.mozilla.net',
    'shavar.services.mozilla.com',
}

class RecordMaster(controller.Master):
    def __init__(self, q, server):
        controller.Master.__init__(self, server)
        self.q = q
        self.started = False

    def __del__(self):
        if self.started:
            self.shutdown()

    def run(self):
        try:
            r = controller.Master.run(self)
            self.started = True
            return r
        except KeyboardInterrupt:
            self.shutdown()

    def handle_request(self, flow):
        # hack around mitmdump weirdness
        if isinstance(flow.server_conn.address, netlib.tcp.Address):
            addr = flow.server_conn.address.host
        else:
            addr = flow.server_conn.address.split(':')[0]

        # store the host in the queue with the title output_queue[0]
        if addr not in BLACKLIST and re.match('aus[1-9].mozilla.org', addr) is None:
            self.q.put(addr)

        return flow.reply()


def __run(q, port):
    config = proxy.ProxyConfig(port=port)
    server = ProxyServer(config)
    m = RecordMaster(q, server)
    m.run()

def run(port=8000):
    q = Queue()
    p = threading.Thread(target=__run, args=(q, port))
    p.start()
    return p, q
