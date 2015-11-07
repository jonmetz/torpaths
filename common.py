"""
Provides miscelanious common functionality that is used by multiple modules but
isn't sufficiently important to warran its own module.

"""

from ipaddr import IPAddress

def is_addr_private(addr_str):
    addr = IPAddress(addr_str)
    return addr.is_private
