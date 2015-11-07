"""
Finds out what DNS servers were queried for a given domain.
Instantiate a DNSTracer object and call object.trace(domain_name) to use.
"""

import re

import envoy


class DNSTracer(object):
    """
    Determines what dns servers must be queried to map a domain name to ip
    """

    REGEX = re.compile(r"Received \d+ bytes from (?P<server>.*)\#")

    def trace(self, domain_name):
        """
        The main interface of the DNSTracer class. Takes a domain_name as an
        argument and returns a list of nameservers that must be queried to receive
        an answer
        """
        # TODO: use scapy for this instead of dig and envoy
        proc = envoy.run('dig +trace '+ domain_name)
        assert proc.status_code == 0
        return self.REGEX.findall(proc.std_out)
