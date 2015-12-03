"""
The only real way to use this module is by using browser.visit
(on an instance of the Browser class. This method finds the paths
traversed when a browser visits a webpage.

"""
import os
import httplib
import multiprocessing as mp

from time import sleep

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
from pymongo import MongoClient
from selenium.common import exceptions as selenium_exception

from proxy import run
from common import get_db


class Browser(object):
    """
    Controls the browser (Firefox) using selenium. Visits sites with it,
    coordinates recording of network traffic with the proxy, reads the results
    of the recording from mongo, and does traces on the results.

    """

    SLEEP_MAX = 60

    def __init__(self, proxy_url='127.0.0.1:8000', q=None):
        self.proxy_url = proxy_url
        self.display = Display(visible=0, size=(800, 600))
        self.display.start()
        _, port = proxy_url.split(':')
        port = int(port)
        self._proxy_proc, self.proxy_queue = run(port=port)

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


    def __del__(self):
        self.kill_proxy()

    def kill_proxy(self):
        pass
        # return self._proxy_proc.terminate()

    def _new_firefox_profile(self):
        ff_profile = webdriver.FirefoxProfile()

        for key, value in self.FF_PROFILE_PREFERENCES.iteritems():
            ff_profile.set_preference(key, value)

        return ff_profile

    def _hosts_from_page(self, page_url):
        """
        Uses Selenium to visit a page. returns a list of hosts that are connected to,
        to fetch resources when loading the page.

        """

        self.driver.get(page_url)
        # when this point is reached, we have fetched most resources on the page
        contacted_hosts = self._wait_for_requests()

        try:
            assert contacted_hosts, "No hosts contacted, is the proxy running?"
        except:
            import ipdb; ipdb.set_trace()
        return list(contacted_hosts)

    def _wait_for_requests(self, sleep_period=2, at_least=3):

        contacted_hosts = set()
        sleep(at_least)
        should_sleep = True
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
        return contacted_hosts


    def visit(self, page_url):
        """
        Visits a webpage and determines the paths that are traversed when visiting it.

        """

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
        self.driver.set_page_load_timeout(self.SLEEP_MAX)

        hosts = self._hosts_from_page(page_url)
        try:
            self.driver.quit()
        except httplib.BadStatusLine:
            print 'bad status line'
            return

        data = {
            'url': page_url,
            'hosts': hosts,
        }

        return hosts


class MultiVisitor(object):
    PROXY_HOST = '127.0.0.1'
    port = 8000

    def __init__(self, num_threads=8):
        self.num_threads = num_threads
        self.pool = mp.Pool(num_threads)

    def visit_multiple(self, urls):

        def pick_port_num(url):
            num = self.get_port()
            return num, url

        urls = map(pick_port_num, urls)
        self.pool.map(_visit_one, urls)

    @classmethod
    def get_port(cls):
        port = cls.port
        cls.port += 1
        return port


def _visit_one(port_url_tup, storage={}):
    port, url = port_url_tup
    proxy_url = MultiVisitor.PROXY_HOST + ':' + str(8000 + port)

    if not 'browser' in storage:
        b = Browser(proxy_url=proxy_url)
        storage['browser'] = b
        assert 'db' not in storage
        db = get_db()
        storage['db'] = db
    else:
        b = storage['browser']
        db = storage['db']
        # empty the queue
        while not b.proxy_queue.empty():
            b.proxy_queue.get()

    try:
        hosts = b.visit(url)

        db.pages.insert_one({
            'url': url,
            'hosts': hosts
        })
    except selenium_exception.TimeoutException:
        print 'TimeoutException on {0}'.format(url)
        return
    except selenium_exception.WebDriverException:
        print 'webdriver exception on {0}'.format(url)
        return
    return hosts
