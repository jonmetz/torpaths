"""
The only real way to use this module is by using browser.visit
(on an instance of the Browser class. This method finds the paths
traversed when a browser visits a webpage.

"""
import os

from pyvirtualdisplay import Display
from selenium import webdriver
from pymongo import MongoClient

FIREFOX_PROF_DIR = os.getenv('TORPATHS_FIREFOX_PROF_DIR')
assert FIREFOX_PROF_DIR

db = MongoClient().torpaths

class Browser(object):
    """
    Controls the browser (Firefox) using selenium. Visits sites with it,
    coordinates recording of network traffic with the proxy, reads the results
    of the recording from mongo, and does traces on the results.

    """

    def __init__(self, proxy_host='localhost:8000'):
        super(Browser, self).__init__()
        profile = webdriver.FirefoxProfile(FIREFOX_PROF_DIR)
        self.driver = webdriver.Firefox(firefox_profile=profile)

    def _hosts_from_page(self, page_url):
        """
        Uses Selenium to visit a page. returns a list of hosts that are connected to,
        to fetch resources when loading the page.

        """
        db.proxy_out.delete_many({})
        self.driver.get(page_url)
        # when this point is reached, we have fetched most resources on the page
        contacted_hosts = set()
        for result in db.proxy_out.find():
            contacted_hosts.add(str(result['addr']))

        db.proxy_out.delete_many({})
        assert contacted_hosts, "No hosts contacted, is mitmdump (proxy.py) running?"
        return list(contacted_hosts)

    def visit(self, page_url):
        """
        Visits a webpage and determines the paths that are traversed when visiting it.
        """
        display = Display(visible=0, size=(800, 600))
        display.start()
        hosts = self._hosts_from_page(page_url)
        self.driver.close()
        data = {
            'url': page_url,
            'hosts': hosts,
        }

        db.page_resource_hosts.insert_one(data)
        return hosts
