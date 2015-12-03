"""
Provides miscelanious common functionality that is used by multiple modules but
isn't sufficiently important to warran its own module.

"""
import os
import urllib
import json

from pymongo import MongoClient
from ipaddr import IPAddress

MY_PUBLIC_IP = None

def is_addr_private(addr_str):
    addr = IPAddress(addr_str)
    return addr.is_private

def get_db():
    mongo_netloc = os.getenv('TORPATHS_MONGO_NETLOC', None)
    if mongo_netloc is None:
        return MongoClient().torpaths
    else:
        mongo_host, mongo_port_str = mongo_netloc.split(':')
        mongo_port = int(mongo_port_str)
        return MongoClient(host=mongo_host, port=mongo_port).torpaths

def get_my_public_ip(cache=True):
    if MY_PUBLIC_IP is None or not cache:
        data = json.loads(urllib.open("http://wtfismyip.com/").read())
        addr = data['YourFuckingIPAddress']
        MY_PUBLIC_IP = str(addr)

    return MY_PUBLIC_IP

def remove_collection(name):
    db = get_db()
    return getattr(db, name).remove()
