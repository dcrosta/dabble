import unittest

import dabble
from dabble import *
from dabble.backends.fs import *
from dabble.backends.mongodb import *
import pymongo

from os import makedirs
from os.path import dirname, exists, join
from shutil import rmtree

class MockIdentityProvider(IdentityProvider):

    def __init__(self):
        super(MockIdentityProvider, self).__init__()
        self.identity = None

    def get_identity(self):
        if self.identity is None:
            raise Exception('bad test, need to set identity')

        return self.identity

class RandRange(object):
    def __init__(self):
        self.n = 0
        self.last = None

    def __call__(self, max):
        self.last = self.n % max
        self.n += 1
        return self.last


def ReportTestFor(name, setUp_func, tearDown_func):
    def test_one(self):
        class T(object):
            abtest = ABTest('foobar', ['foo'], ['show', 'fill'])

        t = T()

        self.provider.identity = 1
        t.abtest.record('show')
        t.abtest.record('show')
        t.abtest.record('fill')

        self.provider.identity = 2
        t.abtest.record('show')
        t.abtest.record('fill')

        self.provider.identity = 3
        t.abtest.record('fill')

        self.provider.identity = 4
        t.abtest.record('show')

        report = self.storage.report('foobar')

        expected = {
            'test_name': 'foobar',
            'results': [{
                'alternative': 'foo',
                'funnel': [{
                    'stage': ('show', 'fill'),
                    'attempted': 3,
                    'converted': 2,
                }],
            }],
        }

        try:
            self.assertEquals(report, expected)
        except:
            from pprint import pprint
            pprint(report)
            pprint(expected)
            raise


    def test_two(self):
        class T(object):
            abtest = ABTest('foobar', ['foo', 'bar'], ['show', 'fill'])

        t = T()

        # foo
        self.provider.identity = 1
        t.abtest.record('show')
        t.abtest.record('show')
        t.abtest.record('fill')

        # bar
        self.provider.identity = 2
        t.abtest.record('show')
        t.abtest.record('fill')

        # foo
        self.provider.identity = 3
        t.abtest.record('fill')

        # bar
        self.provider.identity = 4
        t.abtest.record('show')

        report = self.storage.report('foobar')

        expected = {
            'test_name': 'foobar',
            'results': [
                {
                    'alternative': 'foo',
                    'funnel': [{
                        'stage': ('show', 'fill'),
                        'attempted': 1,
                        'converted': 1,
                    }],
                },
                {
                    'alternative': 'bar',
                    'funnel': [{
                        'stage': ('show', 'fill'),
                        'attempted': 2,
                        'converted': 1,
                    }],
                }
            ],
        }

        self.assertEquals(report, expected)

    def test_funnel(self):
        class T(object):
            abtest = ABTest('foobar', ['foo', 'bar'], ['a', 'b', 'c', 'd'])

        t = T()

        # foo
        self.provider.identity = 1
        t.abtest.record('a')
        t.abtest.record('b')

        # bar
        self.provider.identity = 2
        t.abtest.record('a')
        t.abtest.record('b')
        t.abtest.record('c')

        # foo
        self.provider.identity = 3
        t.abtest.record('a')
        t.abtest.record('b')
        t.abtest.record('c')

        # bar
        self.provider.identity = 4
        t.abtest.record('a')
        t.abtest.record('b')
        t.abtest.record('c')
        t.abtest.record('d')

        expected = {
            'test_name': 'foobar',
            'results': [
                {
                    'alternative': 'foo',
                    'funnel': [
                        {
                            'stage': ('a', 'b'),
                            'attempted': 2,
                            'converted': 2,
                        },
                        {
                            'stage': ('b', 'c'),
                            'attempted': 2,
                            'converted': 1,
                        },
                        {
                            'stage': ('c', 'd'),
                            'attempted': 1,
                            'converted': 0,
                        },
                    ],
                },
                {
                    'alternative': 'bar',
                    'funnel': [
                        {
                            'stage': ('a', 'b'),
                            'attempted': 2,
                            'converted': 2,
                        },
                        {
                            'stage': ('b', 'c'),
                            'attempted': 2,
                            'converted': 2,
                        },
                        {
                            'stage': ('c', 'd'),
                            'attempted': 2,
                            'converted': 1,
                        },
                    ],
                }
            ],
        }

        report = self.storage.report('foobar')
        self.assertEquals(report, expected)


    funcs = {
        'test_one': test_one,
        'test_two': test_two,
        'test_funnel': test_funnel,
    }
    if setUp_func:
        funcs['setUp'] = setUp_func
    if tearDown_func:
        funcs['tearDown'] = tearDown_func

    return type(name, (unittest.TestCase, ), funcs)

def generic_setUp(self):
    # also mock random.randrange with a callable
    # object which will tell us what the "random"
    # value was
    self.randrange = RandRange()
    dabble.random.randrange = self.randrange

def mongo_setUp(self):
    generic_setUp(self)

    conn = pymongo.Connection()
    db = conn.dabble_test
    for collection in db.collection_names():
        if collection.startswith('dabble'):
            db.drop_collection(collection)

    self.storage = MongoResultStorage(db)
    self.provider = MockIdentityProvider()
    configure(self.provider, self.storage)

def fs_setUp(self):
    generic_setUp(self)

    here = dirname(__file__)
    storage_dir = join(here, 'storage')
    if exists(storage_dir):
        rmtree(storage_dir)
    makedirs(storage_dir)

    self.storage = FSResultStorage(storage_dir)
    self.provider = MockIdentityProvider()
    configure(self.provider, self.storage)


def generic_tearDown(self):
    # pretend like the previous test never happened
    dabble.AB._id_provider = None
    dabble.AB._storage = None
    dabble.AB._AB__n_per_test = {}

    del self.storage
    del self.provider

def mongo_tearDown(self):
    generic_tearDown(self)

    conn = pymongo.Connection()
    db = conn.dabble_test
    for collection in ('dabble.tests', 'dabble.results'):
        db.drop_collection(collection)

def fs_tearDown(self):
    generic_tearDown(self)

    here = dirname(__file__)
    storage_dir = join(here, 'storage')
    if exists(storage_dir):
        rmtree(storage_dir)


MongoReportTest = ReportTestFor('MongoReportTest', mongo_setUp, mongo_tearDown)
FSReportTest = ReportTestFor('FSReportTest', fs_setUp, fs_tearDown)

if __name__ == '__main__':
    unittest.main()

