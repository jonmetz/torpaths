import re
import json

from selenium.common import exceptions as selenium_exception
from pymongo import MongoClient

import browser
from trace_asn_paths import AsnTracer
from common import get_db, get_my_public_ip

# b = browser.Browser()
db = get_db()


def get_and_save_page_hosts(filename='sites.txt'):
    i = 0
    with open(filename) as fp:

        urls = [str('http://' + url.strip('\n') + '/')
                for url in fp.readlines()]

        mv = browser.MultiVisitor()
        # mv.visit_multiple(urls[:1])
        mv.visit_multiple(urls[1:3])
        mv.visit_multiple(urls[3:10])
        import ipdb; ipdb.set_trace()
        # tries = 0
        # for url in urls:
        #     if i == 5:
        #         break
        #     i += 1
        #     try:
        #         db.pages.insert_one({
        #             'url': url,
        #             'hosts': b.visit(url)
        #         })
        #         if tries:
        #             tries = 0 # was successful retry: reset
        #     except selenium_exception.TimeoutException:
        #         print 'TimeoutException on {0}'.format(url)
        #         continue
        #     except selenium_exception.WebDriverException:
        #         tries += 1
        #         if tries == 3:
        #             tries = 0
        #             print 'continuing, tries at max'
        #         continue


def trace_pages():
    pages = db.pages.find()
    asn_tracer = AsnTracer()
    for page in pages:
        traces = [{'host': host, 'host_traces': asn_tracer.trace(str(host)), 'scanner_ip': g}
                  for host in page['hosts']]

    db.pages.update_one({'_id': page['_id']}, {'$set': {'traces': traces}})
