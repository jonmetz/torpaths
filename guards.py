from onionoo import Onionoo

from trace_asn_paths import AsnTracer
from database import get_trace_db

db = get_trace_db().guard_traces
asn_tracer = AsnTracer()

def is_ipv6(netloc):
    return netloc.count(':') > 1 and '[' in netloc and ']' in netloc

def clean_onionoo_data(relay):
    cleaned = {}
    # cleaned['as_number'] = relay['as_number'] if 'as_number' in relay else None
    addresses = relay['or_addresses']
    if len(addresses) == 1:
        cleaned['address'], _ = addresses[0].split(':')
    else:
        addrs = [netloc.split(':')[0] for netloc in addresses if not is_ipv6(netloc)]
        if len(addrs) == 1:
            cleaned['address'] = addrs[0]
        else:
            cleaned['address'] = None
            cleaned['addresses'] = addrs

    return cleaned

def get_guard_addrs():
    o = Onionoo()
    relays = o.get_relays()
    relays = o.remove_nonrunning(relays)
    complete_guards = [relay for relay in relays if float(relay['guard_probability']) > 0.0]
    return [clean_onionoo_data(guard)['address'] for guard in complete_guards]


def get_and_save_guard_traces():
    guard_addrs = get_guard_addrs()
    guard_traces = []
    for addr in guard_addrs:
        trace = asn_tracer.trace(addr)
        guard_trace = {
            'host': addr,
            'trace': trace
        }
        db.guard_traces.insert_one(guard_trace)
        guard_traces.append(guard_trace)
    return guard_traces

def main():
    return get_and_save_guard_traces()


if __name__ == '__main__':
    main()
