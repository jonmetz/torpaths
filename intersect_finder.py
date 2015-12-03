from pymongo import MongoClient

class IntersectFinder(object):
    def __init__(self):
        self.db = MongoClient().torpaths
        self.page_asns = None
        self.page_hosts = None
        self.load_data()


    def load_data(self):
        self.db.page_resource_hosts.find()


    def find_intersections(self):
        build_mapping
