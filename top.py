import socket

from multiprocessing import Process
from shutil import rmtree
from time import time
from glob import glob

import pymongo
from selenium.common import exceptions as selenium_exception
from ipaddr import IPAddress

from browser import Browser
from trace_asn_paths import AsnTracer
from trace_dns import DNSTracer
from database import get_sites, import_sites, get_db
from guards import get_and_save_guard_traces

NUM_PAGES_DEFAULT = 300

db = get_db()

def get_and_save_page_hosts(max_pages=NUM_PAGES_DEFAULT):
    n_pages = 0
    while True:
        if n_pages == max_pages:
            break
        n_pages += 1
        cleanup_tmp_selenium_files()
        site = db.sites.find_one_and_delete({})
        print 'visiting', site
        if not site:
            print 'breaking'
            break
        b = Browser()
        try:
            start = time()
            hosts = b.visit('http://' + site['site'] + '/')
            data = {
            'url': site['site'],
            'hosts': hosts,
            'accessed_timestamp': time()
            }
            print "actually took", time() - start
            db.pages.insert_one(data)
        except Exception as e:
            print 'problem with', site, e
        b.kill_proxy()


def get_page_hosts(pages=None, include_dns_servers=False):
    if pages is None:
        pages = db.pages.find()

    page_hosts = set()
    for page in pages:
        for host in page['hosts']:
            page_hosts.add(host)

    if include_dns_servers:
        dns_traces = db.page_host_dns_servers.find()
        for dns_trace in dns_traces:
            for dns_server in dns_trace['dns_servers']:
                page_hosts.add(dns_server)

    return page_hosts

def trace_dns_of_page_hosts(page_hosts=None):
    if page_hosts is None:
        page_hosts = get_page_hosts()

    dns_tracer = DNSTracer()
    host_dns_servers = get_db().page_host_dns_servers

    for host in page_hosts:
        # Skip any host that is an IP
        try:
            IPAddress(host)
            continue
        except ValueError:
            pass

        # Skip any hosts we have traced before
        if list(host_dns_servers.find({'host': host})):
            continue

        host_dns_trace = {
            'dns_servers': dns_tracer.trace(host),
            'host': host
        }
        host_dns_servers.insert_one(host_dns_trace)

def trace_asns_of_hosts(page_hosts=None, include_dns_servers=True):
    """
    Find AS paths of hosts contacted when visiting each page.

    """
    if page_hosts is None:
        page_hosts = get_page_hosts(include_dns_servers)

    asn_tracer = AsnTracer()

    for host in page_hosts:

        # Skip any hosts we have traced before
        if list(db.host_asn_traces.find({'host': host})):
            continue
        try:
            host_asn_trace = {
                'host': host,
                'trace': asn_tracer.trace(str(host)),
            }
        except socket.gaierror:
            host_asn_trace = {
                'host': host,
                'trace': [],
            }

        db.host_asn_traces.insert_one(host_asn_trace)

def cleanup_tmp_selenium_files():
    """
    When using Firefox with selenium, Firefox will leave some temporary files
    related to creating a Firefox profile in the /tmp directory. Since visiting
    pages uses a new profile each time, we should delete these files to prevent
    them from filing up the disk.

    """
    selenium_tmp_dirs = glob('/tmp/tmp*')
    for selenium_tmp_dir in selenium_tmp_dirs:
        rmtree(selenium_tmp_dir)


def pipelined_pages_trace(pages_db_name=None, num_pages=NUM_PAGES_DEFAULT):
    """
    Allows tracing of pages (finding all dns servers that were possibly queried
    and all asns traversed), concurrently with visiting pages in a browser.
    pages_db_name is the database we get the pages from, note that this is usually
    different from the one it is saved to. num_pages is the number of pages this
    function will trace before terminating. If this is higher than the number of
    pages, this function will loop forever.
    returns None.

    """


    pages_mongo_collection = get_db(pages_db_name).pages
    traced_hosts = set(str(trace['host']) for trace in get_db(pages_db_name).host_asn_traces.find())
    visited_pages = set(page['url'] for page in pages_mongo_collection.find())
    traced_pages = set(page for page in visited_pages if page in traced_hosts)

    while len(traced_pages) < num_pages:
        visited_pages = set(page['url'] for page in pages_mongo_collection.find())
        untraced_page_urls = visited_pages - traced_pages
        if untraced_page_urls:
            untraced_pages = pages_mongo_collection.find(
                {'url': {'$in': list(untraced_page_urls)}}
            )
            try:
                for page in untraced_pages:
                    print 'tracing dns', page['url']
                    trace_dns_of_page_hosts(get_page_hosts([page,], False))
                    print 'tracing asns', page['url']
                    trace_asns_of_hosts(get_page_hosts([page,], True))
                    traced_pages.add(page['url'])
            except pymongo.errors.CursorNotFound:
                print 'CursorNotFound'
                pass
