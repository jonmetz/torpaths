import json
import shutil
import time

from selenium.common import exceptions as selenium_exception
from pymongo import MongoClient

import browser
import database
from trace_asn_paths import AsnTracer
from common import get_db, get_my_public_ip
from database import get_sites

db = get_db()

def get_and_save_page_hosts(max_pages=3):
    n_pages = 0
    while True:
        if n_pages == max_pages:
            break
        n_pages += 1
        try:
            # TODO figure out better way to delete selenium tmp files (dirs with the path /tmp/tmp*)
            shutil.rmtree('/tmp')  # selenium will fill up our disk otherwise
        except OSError:
            # this is expected if we aren't root
            pass
        site = db.sites.find_one_and_delete({})
        print 'visiting', site
        if not site:
            print 'breaking'
            break
        b = browser.Browser()
        try:
            start = time.time()
            hosts = b.visit('http://' + site['site'] + '/')
            data = {
            'url': site['site'],
            'hosts': hosts,
            'accessed_timestamp': time.time()
            }
            print "actually took", time.time() - start
            db.pages.insert_one(data)
        except Exception as e:
            print 'problem with', site, e
        b.kill_proxy()


def trace_pages():

    pages = db.pages.find()
    asn_tracer = AsnTracer()
    my_ip = get_my_public_ip()

    for page in pages:
        trace_results = []
        for host in page['hosts']:
            trace_result = {'host': host, 'trace': asn_tracer.trace(str(host)), 'scanner_ip': my_ip}
            trace_results.append(trace_result)
        db.pages.update_one({'_id': page['_id']}, {'$set': {'traces': trace_results}})

def main():
    database.import_sites()
    get_and_save_page_hosts()

if __name__ == '__main__':
    main()
