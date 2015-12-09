"""
Provides miscelanious common functionality that is used by multiple modules but
isn't sufficiently important to warran its own module.

"""
import os
import urllib
import json

import pymongo

from ipaddr import IPAddress

DEBUG = os.getenv('TORPATHS_DEBUG', False)

def is_addr_private(addr_str):
    addr = IPAddress(addr_str)
    return addr.is_private

def get_db():
    mongo_netloc = os.getenv('TORPATHS_MONGO_NETLOC', None)

    if mongo_netloc is None:
        return pymongo.MongoClient().torpaths
    else:
        mongo_host, mongo_port_str = mongo_netloc.split(':')
        mongo_port = int(mongo_port_str)
        if not DEBUG:
            return pymongo.MongoClient(host=mongo_host, port=mongo_port).torpaths
        else:
            return pymongo.MongoClient(host=mongo_host, port=mongo_port).torpaths_debug

def get_my_public_ip():
    data = json.loads(urllib.urlopen("http://wtfismyip.com/json").read())
    addr = data['YourFuckingIPAddress']
    my_ip = str(addr)
    return my_ip

def remove_collection(name):
    db = get_db()
    return getattr(db, name).remove()


def copy_collection(from_coll, to_coll):
    db = get_db()
    from_coll = getattr(db, from_coll).find()
    sz = 0
    for item in from_coll:
        try:
            getattr(db, to_coll).insert_one(item)
            sz += 1
        except pymongo.errors.DuplicateKeyError:
            print 'already copied'

    return sz

def get_collection(name):
    return list(get_db()[name].find())
