"""
The only real way to use this module is by using browser.visit
(on an instance of the Browser class. This method finds the paths
traversed when a browser visits a webpage.

"""
import os

from time import sleep, time

from pyvirtualdisplay import Display
from selenium import webdriver
from pymongo import MongoClient

from proxy import run as run_proxy

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
        self.display = Display(visible=0, size=(800, 600))
        self.display.start()
        self.ff_profile = webdriver.FirefoxProfile(FIREFOX_PROF_DIR)
        _, self.proxy_queue = run_proxy()


    def _clear_q():
        while not self.proxy_queue.empty():
            print self.proxy_queue.get(), 'WARNING'

    def _hosts_from_page(self, page_url):
        """
        Uses Selenium to visit a page. returns a list of hosts that are connected to,
        to fetch resources when loading the page.

        """

        self.driver.get(page_url)
        # when this point is reached, we have fetched most resources on the page
        contacted_hosts = self._wait_for_requests()

        assert contacted_hosts, "No hosts contacted, is the proxy running?"
        return list(contacted_hosts)

    def _wait_for_requests(self, sleep_period=2, at_least=7):
        start = time()
        contacted_hosts = set()
        sleep(at_least)
        while True:
            if not self.proxy_queue.empty():
                old_len = len(contacted_hosts)
                new_host = self.proxy_queue.get()
                if new_host not in contacted_hosts:
                    contacted_hosts.add(new_host)
                    should_sleep = True
            elif should_sleep:
                sleep(sleep_period)
                should_sleep = False
            else:
                break
        print "took " + str(time() - start)
        return contacted_hosts


    def visit(self, page_url):
        """
        Visits a webpage and determines the paths that are traversed when visiting it.
        """

        self.driver = webdriver.Firefox(firefox_profile=self.ff_profile)
        hosts = self._hosts_from_page(page_url)
        self.driver.close()
        data = {
            'url': page_url,
            'hosts': hosts,
        }

        return hosts
