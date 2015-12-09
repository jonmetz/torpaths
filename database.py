from common import get_db

db = get_db()

def import_sites(filename="sites.txt"):
    with open(filename) as fp:
        lines = [line.strip('\n') for line in fp.readlines()]
    db.sites.remove()
    for site in lines:
        db.sites.insert_one({'site': site})

def get_sites(n=1):
    for _ in xrange(n):
        site = db.sites.find_one_and_delete({})
        if site:
            yield site
        else:
            break
