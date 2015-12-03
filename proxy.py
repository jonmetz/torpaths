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
        print 'myid is', id(self.q)
        from time import sleep
        sleep(5)
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
            print "putting", addr, str(id(self.q))
            self.q.put(addr)
            # print self.q
            # print self.q.empty()

        return flow.reply()


def __run(q, port):
    # print 'port ' + str(port)
    config = proxy.ProxyConfig(port=port)
    server = ProxyServer(config)
    m = RecordMaster(q, server)
    m.run()

def run(q, port=8000):
    p = threading.Thread(target=__run, args=(q, port))
    p.start()
    return p, q
