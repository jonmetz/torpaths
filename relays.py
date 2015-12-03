import sqlite3

import pandas as pd

from generictracer import Tracer
from onionoo import Onionoo
from db import DB

class RelayTracer(Tracer):

    def trace_saved_relays(self):
        with open('relays.json', 'w+') as fp:

            import ipdb; ipdb.set_trace()
            fp.write('')
