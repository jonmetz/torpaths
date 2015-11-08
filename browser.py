"""
The only real way to use this module is by using browser.visit
(on an instance of the Browser class. This method finds the paths
traversed when a browser visits a webpage.

"""

import itertools
import sys
import time
import urlparse

from multiprocessing.pool import ThreadPool

import envoy

from trace_asn_paths import AsnTracer
from trace_dns import DNSTracer
from common import is_addr_private


class Browser(object):
    """
    Controls the browser (PhantomJS). Visits sites with it, records hosts
    that were contacted during the page load and does traceroutes to these
    hosts and the dns servers used to locate them.

    """

    def __init__(self, thread_count=8):

        self.dns_tracer = DNSTracer()
        self.pool = ThreadPool(thread_count)
        self.asn_tracer = AsnTracer()


    def _hosts_from_page(self, page_url):
        """
        Uses PhantomJS to visit a returns a list of hosts that are connected to,
        to fetch resources when loading the page.

        """

        browser_proc = envoy.run("phantomjs browser.js " + page_url, timeout=30)
        urls = [url.strip('"') for url in browser_proc.std_out.split('\n') if url != '' ]
        netlocs = [urlparse.urlparse(url).netloc for url in urls]
        contacted_hosts = set(netloc if ':' not in netloc else netloc.split(':')[0] for netloc in netlocs)
        return contacted_hosts

    def visit_multiple(self, page_urls):
        """
        The plural version of visit.

        """
        # TODO: parallelize?
        return map(self.visit, page_urls)


    def visit(self, page_url):
        """
        Visits a webpage and determines the paths that are traversed when visiting it.

        """
        resource_hosts = self._hosts_from_page(page_url)

        # This stores the results we care about
        print page_url
        page_result = {
            'page': page_url,
            'resource_hosts': map(self._trace, list(resource_hosts))
        }
        return PageResult(page_result)

    def _trace(self, host):
        """
        Traces the Asns to a host and to the nameservers used to find the host.
        Returns the nameservers queried, and the Asns traversed to each host.

        """


        def asn_tracer_dns_helper(contacted_host):
            """
            For use on DNS servers.

            """

            return {
                'host': contacted_host,
                'traversed_asns': self.asn_tracer.trace(contacted_host)
            }

        dirty_queried_dns_servers = self.dns_tracer.trace(host)
        queried_dns_servers = [dns_server for dns_server in
                               dirty_queried_dns_servers if dns_server and
                               not is_addr_private(dns_server)]
        return {
            'host': host,
            'traversed_asns': self.asn_tracer.trace(host),
            'queried_dns_servers': self.pool.map(
                asn_tracer_dns_helper,
                queried_dns_servers
            )
        }

class PageResult(object):
    """
    Helper class that provides methods to extract important
    data from the results of a page visit.

    """

    def __init__(self, result):
        self._result = result

    def __unicode__(self):
        return unicode(self._result)

    def __str__(self):
        return str(self._result)

    def __repr__(self):
        return str(self.summary)

    def get_resource_hosts(self):
        """
        returns the hosts that were contacted directly to fetch resources.

        """
        for host_dict in hosts:
            return host_dict['host']

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

    @property
    def summary(self):
        """
        Provides a summary of the result as a (page, asns_traversed) tuple.

        """
        page_url = self._result['page']
        asns = set()
        for contacted_host in self._result['hosts']:
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
