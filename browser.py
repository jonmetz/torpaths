"""
The only real way to use this module is by using browser.visit
(on an instance of the Browser class. This method finds the paths
traversed when a browser visits a webpage.

"""
import os

from time import sleep, time

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
from pymongo import MongoClient

from proxy import run as run_proxy

db = MongoClient().torpaths


from functools import wraps
import errno
import os
import signal

class TimeoutError(Exception):
    pass

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator

class Browser(object):
    """
    Controls the browser (Firefox) using selenium. Visits sites with it,
    coordinates recording of network traffic with the proxy, reads the results
    of the recording from mongo, and does traces on the results.

    """

    def __init__(self, proxy_url='localhost:8000'):
        self.proxy_url = proxy_url
        self.display = Display(visible=0, size=(800, 600))
        self.display.start()
        self.FF_PROFILE_PREFERENCES = {
            'browser.cache.disk.capacity': 0,
            'browser.cache.disk.enable': False,
            'browser.cache.disk.smart_size.first_run': False,
            'browser.cache.memory.enable': False,
            'browser.cache.memory.max_entry_size': 0,
            'browser.cache.offline.enable': False,
            'network.http.use-cache': False,
            'browser.privatebrowsing.autostart': True,
            'browser.cache.disk.smart_size.first_run': False,
            'datareporting.healthreport.service.firstRun': False,
            'toolkit.telemetry.reportingpolicy.firstRun': False,
            'startup.homepage_welcome_url': 'about:blank',
            'startup.homepage_welcome_url.additional': 'about:blank'
        }

        self.proxy_proc, self.proxy_queue = run_proxy()
        self.driver = None

    def _new_firefox_profile(self):
        ff_profile = webdriver.FirefoxProfile()

        for key, value in self.FF_PROFILE_PREFERENCES.iteritems():
            ff_profile.set_preference(key, value)

        return ff_profile


    def _clear_q(self):
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

    def kill_proxy(self):
        self.proxy_proc.terminate()

    def _wait_for_requests(self, sleep_period=2, at_least=7, at_most=60):
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

            if time() - start > at_most:
                break

        print "took " + str(time() - start)
        return contacted_hosts

    @timeout(120)
    def visit(self, page_url):
        """
        Visits a webpage and determines the paths that are traversed when visiting it.
        """
        if self.driver:
            self.driver.quit()
        self._clear_q()
        proxy = Proxy({
            'proxyType': ProxyType.MANUAL,
            'httpProxy': self.proxy_url,
            'ftpProxy': self.proxy_url,
            'sslProxy': self.proxy_url,
            'noProxy': self.proxy_url
        })
        self.driver = webdriver.Firefox(
            proxy=proxy,
            firefox_profile=self._new_firefox_profile()
        )
        hosts = self._hosts_from_page(page_url)
        self.driver.quit()
        self.driver = None
        return hosts
