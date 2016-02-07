"""
Finds out what DNS servers were queried for a given domain.
Instantiate a DNSTracer object and call object.trace(domain_name) to use.
"""

import re
import subprocess

from common import is_addr_public


class DNSTracer(object):
    """
    Determines what dns servers must be queried to map a domain name to IP.
    """

    REGEX = re.compile(r"Received \d+ bytes from (?P<server>.*)\#")

    def trace(self, domain_name):
        """
        The main interface of the DNSTracer class. Takes a domain_name as an
        argument and returns a list of nameservers that must be queried to receive
        an answer
        """
        cmd = ['dig', '+trace', domain_name]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        assert err is None
        results = self.REGEX.findall(out)
        return [result for result in results if is_addr_public(result)]
