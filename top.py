from multiprocessing import Process
from shutil import rmtree
from time import time
from glob import glob

from selenium.common import exceptions as selenium_exception
from pymongo import MongoClient
from ipaddr import IPAddress

from browser import Browser
from trace_asn_paths import AsnTracer
from trace_dns import DNSTracer
from common import get_db
from database import get_sites, import_sites
from guards import get_and_save_guard_traces

db = get_db()

def get_and_save_page_hosts(max_pages=500):
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


def get_page_hosts(include_dns_servers=False):
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

def trace_dns_of_page_hosts():
    dns_tracer = DNSTracer()
    host_dns_servers = get_db().page_host_dns_servers
    page_hosts = get_page_hosts()
    for host in page_hosts:
        # Skip any host that isn't an IP
        try:
            IPAddress(host)
        except ValueError:
            continue

        host_dns_trace = {
            'dns_servers': dns_tracer.trace(host),
            'host': host
        }
        host_dns_servers.insert_one(host_dns_trace)

def trace_asns_of_hosts(include_dns_servers=True):
    """
    Find AS paths of hosts contacted when visiting each page.
    """
    asn_tracer = AsnTracer()
    page_hosts = get_page_hosts(include_dns_servers)

    for host in page_hosts:
        host_asn_trace = {
            'host': host,
            'trace': asn_tracer.trace(str(host)),
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


def main():
    guards_process = Process(target=get_and_save_guard_traces())
    guards_process.start()
    import_sites()
    get_and_save_page_hosts()
    trace_dns_of_page_hosts()
    guards_process.join()
    trace_asns_of_hosts()


if __name__ == '__main__':
    main()
