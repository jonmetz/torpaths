"""
The only real way to use this module is by using browser.visit
(on an instance of the Browser class. This method finds the paths
traversed when a browser visits a webpage.
Note that the mitmdump proxy with the proxy.py (included in this package)
extension must be running for this to work.

"""
import sys

from multiprocessing.pool import ThreadPool

import redis

from selenium import webdriver

from trace_asn_paths import AsnTracer
from trace_dns import DNSTracer
from common import is_addr_private

class Browser(object):
    """
    Controls the browser (PhantomJS) using selenium. Visits sites with it,
    coordinates recording of network traffic with the proxy, reads the results
    of the recording from redis, and does traces on the results.

    """

    PROXY_INPUT_QUEUE = 'proxy_queue'

    def __init__(self, proxy_url='localhost:8000', thread_count=4,
                 window_sz=(1366, 728),
                 ghostdriver_log_location='/tmp/ghostdriver.log'):

        """
        The default arguments should work for 99% of cases.
        """

        service_args = [
            '--proxy=' + proxy_url,
            '--ignore-ssl-errors=true'
        ]
        self.driver = webdriver.PhantomJS(
            service_log_path=ghostdriver_log_location,
            service_args=service_args
        )
        self.driver.set_window_size(*window_sz)

        self.redis_conn = redis.Redis()
        self.dns_tracer = DNSTracer()
        self.pool = ThreadPool(thread_count)
        self.asn_tracer = AsnTracer()

    def visit(self, page_url):
        """
        Visits a webpage and determines the paths that are traversed when visiting it.
        """

        # Remove leftovers from previous visit
        self.redis_conn.delete(self.PROXY_INPUT_QUEUE)
        self.redis_conn.delete(page_url)
        # make sure the proxy knows what page the requests come from
        self.redis_conn.lpush(self.PROXY_INPUT_QUEUE, page_url)
        self.driver.get(page_url)
        # when this point is reached, we have fetched most resources on the page
        contacted_hosts = set( # remove the many duplicates
            self.redis_conn.lrange(page_url, 0, -1) # get all the hosts
        )
        self.redis_conn.delete(page_url)
        assert contacted_hosts, "No hosts contacted, is mitmdump (proxy.py) running?"

        def host_to_path_dict(host):
            """
            Helper function used by the thread pool

            """

            return {
                'host': host,
                'traversed_asns': self.asn_tracer.trace(host),
            }

        # This stores the results we care about
        page_traversed_asns = {
            'page': page_url,
            'hosts': self.pool.map(host_to_path_dict, contacted_hosts)
        }
        # add traces of DNS servers that were contacted during this visit
        #self.get_dns_servers_paths(page_traversed_asns)
        self.driver.close()
        return PageResult(page_traversed_asns)

    def get_dns_servers_paths(self, page_results):
        """
        Finds the paths traversed to any DNS server that was contacted in order
        to fetch resources needed to load a page.

        """
        for host_dict in page_results['hosts']:
            queried_dns_servers = self.dns_tracer.trace(host_dict['host'])
            traversed_to_dns_servers = []
            for dns_server in queried_dns_servers:
                if not is_addr_private(dns_server):
                    traversed_to_dns_servers.extend(
                        self.asn_tracer.trace(dns_server)
                    )
            host_dict['traversed_asns'] += traversed_to_dns_servers


class PageResult(object):
    """
    Helper class that provides methods to extract important
    data from the results of a page visit.

    """

    def __init__(self, result):
        self.result = result

    def __unicode__(self):
        return str(self.result)

    def __str__(self):
        return str(self.result)

    def __repr__(self):
        return str(self.summarize())

    def get_resource_hosts(self):
        """
        returns the hosts that were contacted directly to fetch resources.

        """

    def get_dns_servers(self):
        """
        The dns version of get_resource_hosts. returns the DNS servers
        that were queried in order to connect to the resources_hosts

        """

    def get_resource_hosts_asns(self):
        """
        returns the list of asns traversed to reach the resource_hosts

        """

    def get_dns_servers_asns(self):
        """
        The dns version of get_resource_hosts. returns the asns that were
        traversed to reach the result of get_dns_servers

        """

    def summarize(self):
        """
        Provides a summary of the result as a (page, asns_traversed) tuple.

        """
        page_url = self.result['page']
        asns = set()
        for contacted_host in self.result['hosts']:
            for asn in contacted_host['traversed_asns']:
                asn_str = asn['asn']
                if asn_str:
                    asns.add(asn_str)
                else:  # asn was None: was unable to find asn from IP
                    org_handle = asn['whois']['org_handle']
                    if org_handle:
                        asns.add(org_handle)
                    else:  # couldn't find an org_handle from IP's whois data
                        asns.add(asn['addr'])
        return page_url, asns

def main():
    assert len(sys.argv) > 1
    urls = sys.argv[1:]
    browser = Browser()
    return [browser.visit(url) for url in urls]


if __name__ == '__main__':
    main()
