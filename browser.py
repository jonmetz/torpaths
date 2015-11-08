"""
The only real way to use this module is by using browser.visit
(on an instance of the Browser class. This method finds the paths
traversed when a browser visits a webpage.

"""
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

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
        self.raw_result = result

    def __unicode__(self):
        return unicode(self.raw_result)

    def __str__(self):
        return str(self.raw_result)

    def __repr__(self):
        return str(self.summary)


    def get_resource_hosts(self):
        """
        returns the hosts that were contacted directly to fetch resources.

        """
        hosts = self.raw_result['resource_hosts']
        return [host_dict for host_dict in hosts]


    def get_dns_servers(self):
        """
        The dns version of get_resource_hosts. returns the DNS servers
        that were queried in order to connect to the resources_hosts

        """
        hosts = self.raw_result['resource_hosts']
        dns_servers = []
        for host in hosts:
            dns_servers.extend(host['queried_dns_servers'])
        return dns_servers

    def _get_hosts(self, l):
        return list(set(x['host'] for x in l))

    def get_resource_host_hostnames(self):
        """
        Get the hostnames of the servers this page needed to load resources from.

        """
        return self._get_hosts(self.get_resource_hosts())

    def get_dns_server_hostnames(self):
        """
        Get the hostnames of the dns servers that were queried to get
        everything needed by this page

        """

        return self._get_hosts(self.get_dns_servers())

    def get_resource_hosts_asns(self):
        """
        returns the list of asns traversed to reach the resource_hosts

        """
        resource_hosts = self.get_resource_hosts()
        return list(set(itertools.chain(*[self.summarize_resource_host(host)
                                          for host in resource_hosts])))

    def get_dns_servers_asns(self):
        """
        The dns version of get_resource_hosts. returns the asns that were
        traversed to reach the result of get_dns_servers

        """
        servers = self.get_dns_servers()
        return list(set(itertools.chain(*[self.summarize_dns_server(server)
                                          for server in servers])))

    def summarize_asn(self, asn_result):
        """
        Returns an asn dict's AS number or the orgRef of the host from its whois
        info, if we couldn't figure out the AS.

        """

        if asn_result['asn']:
            return asn_result['asn']
        else:
            whois = asn_result['whois']
            return whois['org_handle'] if whois['org_handle'] else None

    def summarize_dns_server(self, dns_server):
        return list(
            set(
                self.summarize_asn(asn) for asn in dns_server['traversed_asns']
            )
        )


    def summarize_resource_host(self, r_server):
        summarized_asns = [
            self.summarize_asn(asn) for asn in r_server['traversed_asns']
        ]

        summarized_dns_servers = list(itertools.chain(
            *[self.summarize_dns_server(dns_server) for dns_server in
              r_server['queried_dns_servers']]
        ))

        return summarized_dns_servers + summarized_asns

    def get_asns(self):
        """
        Show all asns traversed to view a page, including ones that we've
        used the host's whois data because we couldn't find its AS.

        """

        asns = [self.summarize_resource_host(host) for host in
                self.raw_result['resource_hosts']]
        return list(set(itertools.chain(*asns)))

    def get_real_asns(self):
        """
        Only show ASNs that are real, not ones that are orgRefs from
        whois data.

        """

        return list(set(self.get_asns()) - set(self.get_pseudo_asns()))

    def get_pseudo_asns(self):
        """
        Get asns which we had to use whois data for instead.

        """

        asns = self.get_asns()
        return [asn for asn in asns if asn.isalpha()]

    @property
    def summary(self):
        """
        Provides a summary of the result as a (page, asns_traversed) tuple.

        """
        asns = self.get_asns()
        asns.sorted()

        return [self.raw_result['page'], asns]

def main():
    assert len(sys.argv) > 1
    urls = sys.argv[1:]
    browser = Browser()
    result = browser.visit_multiple(urls)
    print(result)
    return result


if __name__ == '__main__':
    main()
