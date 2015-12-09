import json
import urllib2

class Onionoo(object):
    DETAILS_URL = "https://onionoo.torproject.org/details"
    TABLE_NAME = 'onionoorelays'

    def __init__(self, limit=None):
        self.data = None
        self.limit = limit

    @staticmethod
    def remove_nonrunning(relays):
        return [relay for relay in relays if relay["running"]]

    @staticmethod
    def clean_relay(relay):
        new_dict = {}
        for key, val in relay.iteritems():
            if isinstance(val, dict) or isinstance(val, list):
                val = json.dumps(val)
            new_dict[key] = val

        return new_dict

    @property
    def onionoo_url(self):
        if self.limit:
            url = self.DETAILS_URL + '?limit=' + str(self.limit)
        else:
            url = self.DETAILS_URL
        return url

    def get_relays(self):
        self.data = json.loads(urllib2.urlopen(urllib2.Request(self.onionoo_url)).read())
        relays = self.data['relays']
        return relays
