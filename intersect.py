from collections import defaultdict

from common import get_db

class IntersectFinder(object):
    def __init__(self):
        self.db = get_db()
        self.pages = None
        self.guards = None
        self.load_data()
        self.intersects = None
        self._asn_intersects = None

    def load_data(self):
        self.pages = list(self.db.pages.find())
        self.guards = list(self.db.guard_traces.find())

    @property
    def asn_intersects(self):
        if self._asn_intersects:
            return self._asn_intersects

        if self.intersects is None:
            self.find_intersects()
            assert self.intersects

        self._asn_intersects = defaultdict(lambda : [])

        for page, intersects in self.intersects.iteritems():
            for intersect in intersects:
                resource_host, relay, asns = intersect
                for asn in asns:
                    self._asn_intersects[asn].append({
                        'page': page,
                        'resource_host': resource_host,
                        'relay': relay
                    })

        return self._asn_intersects



    # def build_asn_guard_mapping(self):
    #     mapping = defaultdict(lambda: set())
    #     for guard in self.guards:
    #         guard_host = guard['guard']

    #         for trace in guard['traces']:
    #             mapping[trace['asn']].add(guard_host)
    #     return mapping

    # def build_page_asn_mapping(self):
    #     mapping = {}
    #     self.keepable_pages = []

    #     for page in self.pages:
    #         page_url = page['url']
    #         mapping[page_url] = set()
    #         # TODO: this is backwards, fix our page objects
    #         for trace in page['traces']:
    #             for host_trace in trace['host_traces']:
    #                     mapping[page_url].add(host_trace['asn'])
    #     return mapping

    @staticmethod
    def build_host_asn_map(traces):
        asn_map = {}
        for trace in traces:
            asns = set(hop['asn'] for hop in trace['trace'])
            asn_map[trace['host']] = asns

        return asn_map



    def _find_traces_intersects(self, traces_1, traces_2):
        intersects = []
        t1_asn_map = self.build_host_asn_map(traces_1)
        t2_asn_map = self.build_host_asn_map(traces_2)
        for host_1, asns_1 in t1_asn_map.iteritems():
            for host_2, asns_2 in t2_asn_map.iteritems():
                intersecting_asns = list(asns_1.intersection(asns_2))
                intersecting_asns.sort()
                intersects.append((host_1, host_2, tuple(intersecting_asns)))
        return intersects


    def find_intersects(self):
        intersects = defaultdict(lambda : set())

        for page in self.pages:
            page_intersects = self._find_traces_intersects(page['traces'], self.guards)
            for intersect in page_intersects:
                intersects[page['url']] = page_intersects

        self.intersects = dict(intersects)
        return self.intersects



def main():
    finder = IntersectFinder()
    result = finder.find_intersects()
    print result
    return result

if __name__ == '__main__':
    main()
