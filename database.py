from os import getenv

from time import time
from common import get_db

def get_collection(name):
    return list(get_db()[name].find())

def remove_collection(name):
    db = get_db()
    return getattr(db, name).remove()

def copy_collection(from_collection, to_collection):
    db = get_db()
    from_collection = getattr(db, from_collection).find()
    sz = 0
    for item in from_collection:
        try:
            getattr(db, to_collection).insert_one(item)
            sz += 1
        except pymongo.errors.DuplicateKeyError:
            print 'already copied'

    return sz


def get_trace_db():
    """
    Route traces will depend on where they are done from,
    as well as the time they are performed.
    Therefore when saving them, we should specify this.
    """
    db = get_db()

    def get_default_name():
        current_time = time()
        host_name = getenv('HOSTNAME', None)
        if host_name is not None:
            return host_name + '_' + current_time
        else:
            return str(current_time)

    scan_name = getenv('TORPATHS_SCAN_NAME', get_default_name())
    return getattr(db, scan_name)

def import_sites(filename="sites.txt"):
    db = get_db()
    with open(filename) as fp:
        lines = [line.strip('\n') for line in fp.readlines()]
    db.sites.remove()
    for site in lines:
        db.sites.insert_one({'site': site})

def get_sites(n=1):
    db = get_db()
    for _ in xrange(n):
        site = db.sites.find_one_and_delete({})
        if site:
            yield site
        else:
            break
