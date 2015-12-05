from collections import defaultdict

from common import get_db

class IntersectionFinder(object):
    def __init__(self):
        self.db = get_db()
        self.pages = None
        self.guards = None
        self.load_data()

    def load_data(self):
        self.pages = list(self.db.pages.find())
        self.guards = list(self.db.guard_traces.find())

    def build_asn_guard_mapping(self):
        mapping = defaultdict(lambda: set())
        for guard in self.guards:
            guard_host = guard['guard']

            for trace in guard['traces']:
                mapping[trace['asn']].add(guard_host)
        return mapping

    def build_page_asn_mapping(self):
        mapping = {}
        self.keepable_pages = []

        for page in self.pages:
            page_url = page['url']
            mapping[page_url] = set()
            for host_trace in page['host_traces']:
                for trace in host_trace['traces']:
                        mapping[page_url].add(trace['asn'])
        return mapping


    def find_intersections(self):
        asn_guard_mapping = self.build_asn_guard_mapping()
        page_asn_mapping = self.build_page_asn_mapping()

        intersections = defaultdict(lambda : set())

        for page_url, asns in page_asn_mapping.iteritems():
            for asn in asns:
                for guard in asn_guard_mapping[asn]:
                    intersections[page_url].add(guard)
        self.intersections = intersections
        return intersections
