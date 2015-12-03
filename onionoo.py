import json
import urllib2

class Onionoo(object):
    DETAILS_URL = "https://onionoo.torproject.org/details"
    TABLE_NAME = 'onionoorelays'

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

    def get_relays(self):
        relays = json.loads(urllib2.urlopen(urllib2.Request(self.DETAILS_URL)).read())['relays']
        return relays
