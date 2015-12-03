"""
Provides the main functionality for looking up AS paths to reach a host.
Create an AsnTracer object and then call asn_tracer.trace(host) to get the asns
that are traversed to contact the host.
Note that the convention in this project is to use the term asn (AS number)
instead of AS (for variable naming reasons).
"""
import json
import re
import urllib2

import dns.resolver
from scapy.all import traceroute as scapy_traceroute
from scapy.all import conf as scapy_conf
scapy_conf.verb = 0  # shutup scapy

from common import is_addr_private


class AsnTracer(object):
    """
    Performs traceroutes on hosts and finds the ASNs of each hop in the traceroute
    """

    # use for getting answers from the Team Cymru query
    ASN_MAPPING_REGEX = re.compile(
        r'.origin\.asn\.cymru\.com\. \d+ IN TXT \"(?P<Asn>\d+) \|'
    )

    def __init__(self):
        # TODO: use a maxsize for the cache
        self.trace_cache = {}

    @staticmethod
    def _lookup_whois(host):
        """
        This method is used when we can't determine the asn of an host.
        It looks up the whois info on the host and saves the handle (@handle of
        orgRef) of the organization that owns the host.
        """

        BASE_URL = "http://whois.arin.net/rest/ip/"
        url = BASE_URL + host
        request = urllib2.Request(url, headers={'Accept': 'application/json'})
        response = json.loads(urllib2.urlopen(request).read())

        try:
            data = {
                'org_handle': response['net']['orgRef']['@handle']
            }
            return data
        except KeyError:  # If there is no orgRef or it doesn't have a handle
            return {'org_handle': None}

    @classmethod
    def hosts_to_asns(cls, hosts):
        """
        Takes a list of ip addresses (hosts) and returns the asn of each of
        the IPs. It uses the IP to asn mapping from Team Cymru to do this.
        If the lookup fails it will try to retreive the handle of the organization
        that owns the host using _lookup_whois(host).
        """

        QUERY_TYPE = 'TXT'
        BASE_DST = '.origin.asn.cymru.com'

        def fmt_dst(addr):
            """
            Format the destination of our Team Cymru query since the destination
            is how the query is specified. This is done by reversing the octets of
            an address and appending the result to BASE_DST
            """
            octets = addr.split('.')
            reversed_str = '.'.join(octets[::-1])
            return reversed_str + BASE_DST


        asns = []
        for host in hosts:
            dst = fmt_dst(host)
            # TODO: use scapy for this instead of dnspython
            try:  # try using the Team Cymru mapping
                answers = dns.resolver.query(dst, QUERY_TYPE).response.answer
            except dns.resolver.NXDOMAIN:
                # If the mapping fails, try looking up the whois info
                asns.append(
                    {'host': host, 'asn': None,
                     'whois': AsnTracer._lookup_whois(host)}
                )
                continue

            assert len(answers) == 1
            results = re.findall(cls.ASN_MAPPING_REGEX, answers[0].to_text())
            # if there's more than one reuslt they better be the same
            if len(set(results)) != 1:
                asn = '/'.join(list(set(results)))
            else:
                asn = results[0]

            # we don't lookup the whois info if the asn mapping was successful
            asns.append({'host': host, 'asn': asn, 'whois': None})

        return asns

    def trace(self, host, use_cache=False, dont_cache=True):
        """
        This is the main interface of AsnTracer class to the outside world.
        Given a host it performs a traceroute to the host and then looksup the
        asns of each hop in the traceroute and returns the result. If the
        mapping fails it returns the whois info instead (when possible).
        Since this is the most time consuming part of the torpaths program,
        it uses a cache to avoid performing traceroutes, IP to asn mappings and
        whois lookups multiple times. To always perform a lookup even if the
        result is in the cache pass use_cache=False as an argument. To prevent
        a result from being cache pass dont_cache=True as argument.
        Note that if a host appears multiple times in a traceroute it will only
        appear once in the results. If it is a private address then it will not
        be included at all.

        """

        if use_cache and host in self.trace_cache:
            return self.trace_cache[host]

        ans, unans = scapy_traceroute(host)
        traceroute_hops = set(
            result.src for _, result in ans if not is_addr_private(result.src)
        )
        result = self.hosts_to_asns(traceroute_hops)

        if not dont_cache:
            self.trace_cache[host] = result

        return result
