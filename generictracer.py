# Tell scapy to be quiet
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from multiprocessing.pool import ThreadPool

from trace_asn_paths import AsnTracer
from trace_dns import DNSTracer
from db import DB

class Tracer(object):

    def __init__(self, thread_count=16):
        self.dns_tracer = DNSTracer()
        self.pool = ThreadPool(thread_count)
        self.asn_tracer = AsnTracer()
        self.timeout_backoff = 0
        self.perform_dns_traces = False
        self.db = DB()

    def _trace(self, host):
        """
        Traces the Asns to a host and to the nameservers used to find the host.
        Returns the nameservers queried, and the Asns traversed to each host.

        """

        # def asn_tracer_dns_helper(contacted_host):
        #     """
        #     For use on DNS servers.

        #     """

        #     return {
        #         'host': contacted_host,
        #         'traversed_asns': self.asn_tracer.trace(contacted_host)
        #     }

        # if self.perform_dns_traces:
        #     #dirty_queried_dns_servers = self.dns_tracer.trace(host)
        #     # queried_dns_servers = [dns_server for dns_server in
        #     #                        dirty_queried_dns_servers if dns_server and
        #     #                        not is_addr_private(dns_server)]

        #     # async_result = self.pool.map_async(
        #     #     asn_tracer_dns_helper,
        #     #     queried_dns_servers
        #     # )
        #     traversed_asns = self.asn_tracer.trace(host)
        #     result = {
        #         'host': host,
        #         'traversed_asns': traversed_asns
        #         'queried_dns_servers': async_result.get(25 + self.timeout_backoff)
        #     }
        # else:
        traversed_asns = self.asn_tracer.trace(host)
        result = {
            'host': host,
            'traversed_asns': traversed_asns
        }
        return result
