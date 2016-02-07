"""
Provides miscelanious common functionality that is used by multiple modules but
isn't sufficiently important to warran its own module.

"""

import os
import urllib
import json
import collections

from pymongo import MongoClient

from ipaddr import IPAddress

HOST_BLACKLIST = {
    # TODO: maybe these could be left in to test safety of using Tor without TBB?
    'search.services.mozilla.com',
    'tiles.services.mozilla.com',
    'tiles-cloudfront.cdn.mozilla.net',
    'shavar.services.mozilla.com',
    'tracking-protection.cdn.mozilla.net',
    'ocsp.digicert.com',
}

ASN_BLACKLIST = {
    '16276', # OVH
    # not sure why we see these, but they're pretty rare anyway
    '',
    None,
}

def is_addr_public(addr_str):
    addr = IPAddress(addr_str)
    return not (addr.is_private or addr.is_loopback or addr.is_multicast or
                addr.is_link_local)

def get_my_public_ip():
    data = json.loads(urllib.urlopen("http://wtfismyip.com/json").read())
    addr = data['YourFuckingIPAddress']
    my_ip = str(addr)
    return my_ip

def get_unique_asns(tracable):
    if tracable['host'] in HOST_BLACKLIST:
        return set()
    return set(get_asn(trace) for trace in tracable['trace'] if get_asn(trace) not in ASN_BLACKLIST)

def get_asn(trace):
    if trace['asn'] is not None:
        return trace['asn']
    else:
        return trace['whois']['org_handle']


def get_unique_page_asns(page):
    unique = set()
    page_url = page['url']
    for trace in page['traces']:
        # if trace['host'] != page_url:
        #     continue
        for pos_unique_asn in get_unique_asns(trace):
            unique.add(pos_unique_asn)
    return unique

def sanity_check(pages, guards):
    guard_asns = {}
    for guard in guards:
        asns_of_guard = get_unique_asns(guard)
        for asn in asns_of_guard:
            if '16276' in asn:
                continue
            if guard['host'] not in guard_asns:
                guard_asns[guard['host']] = set()

            guard_asns[guard['host']].add(asn)

    page_asns = {}
    for page in pages:
        asns_of_page = get_unique_page_asns(page)
        for asn in asns_of_page:
            if '16276' in asn:
                continue
            if page['url'] not in page_asns:
                page_asns[page['url']] = set()

            page_asns[page['url']].add(asn)

    intersects = set()
    asn_intersect_counts = collections.defaultdict(lambda: 0)
    for page, asns_of_page in page_asns.iteritems():
        for guard, asns_of_guard in guard_asns.iteritems():
            isection = (asns_of_page).intersection(asns_of_guard)

            if len(isection) != 0:
                intersects.add((page, guard))
                for asn in isection:
                    asn_intersect_counts[asn] += 1

    return set(intersects), asn_intersect_counts


def get_asn_scores(asn_map):
    return {asn: len(relays_pages[0]) * len(relays_pages[1]) for asn, relays_pages in asn_map.iteritems()}

def find_intersects():
    return sanity_check(pages, guards)
