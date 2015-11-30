import re
import netlib
from multiprocessing import Process, Queue

from libmproxy import controller, proxy
from libmproxy.proxy.server import ProxyServer

BLACKLIST = {
    'search.services.mozilla.com',
    'tiles.services.mozilla.com',
    'tiles-cloudfront.cdn.mozilla.net',
}


class RecordMaster(controller.Master):
    def __init__(self, server, q):
        controller.Master.__init__(self, server)
        self.q = q

    def run(self):
        try:
            return controller.Master.run(self)
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


def __run(q, port=8000):
    config = proxy.ProxyConfig(port=port)
    server = ProxyServer(config)
    m = RecordMaster(server, q)
    m.run()

def run():
    q = Queue()
    p = Process(target=__run, args=(q,))
    p.start()
    return p, q

def main():
    return run()

if __name__ == '__main__':
    main()
