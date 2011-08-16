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


class ReportTest(unittest.TestCase):

    def setUp(self):
        conn = pymongo.Connection()
        db = conn.test
        for collection in db.collection_names():
            if collection.startswith('dabble'):
                db.drop_collection(collection)

        self.storage = MongoResultStorage(db)
        self.provider = MockIdentityProvider()
        configure(self.provider, self.storage)

        # also mock random.randrange with a callable
        # object which will tell us what the "random"
        # value was
        self.randrange = RandRange()
        dabble.random.randrange = self.randrange


    # def setUp(self):
    #     here = dirname(__file__)
    #     storage_dir = join(here, 'storage')
    #     if exists(storage_dir):
    #         rmtree(storage_dir)
    #     makedirs(storage_dir)

    #     self.storage = FSResultStorage(storage_dir)
    #     self.provider = MockIdentityProvider()
    #     configure(self.provider, self.storage)

    #     # also mock random.randrange with a callable
    #     # object which will tell us what the "random"
    #     # value was
    #     self.randrange = RandRange()
    #     dabble.random.randrange = self.randrange


    def tearDown(self):
        # pretend like the previous test never happened
        dabble.AB._id_provider = None
        dabble.AB._storage = None
        dabble.AB._AB__n_per_test = {}

        del self.storage
        del self.provider

    def test_one(self):
        class T(object):
            abtest = ABTest('foobar', ['foo'])

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

        report = self.storage.ab_report('foobar', 'show', 'fill')

        self.assertEquals(report['test_name'], 'foobar')
        self.assertEquals(report['alternatives'], ['foo'])
        self.assertEquals(report['results'][0]['attempted'], 3)
        self.assertEquals(report['results'][0]['completed'], 2)

    def test_two(self):
        class T(object):
            abtest = ABTest('foobar', ['foo', 'bar'])

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

        report = self.storage.ab_report('foobar', 'show', 'fill')

        self.assertEquals(report['test_name'], 'foobar')
        self.assertEquals(report['alternatives'], ['foo', 'bar'])
        self.assertEquals(report['results'][0]['attempted'], 1)
        self.assertEquals(report['results'][0]['completed'], 1)
        self.assertEquals(report['results'][1]['attempted'], 2)
        self.assertEquals(report['results'][1]['completed'], 1)


if __name__ == '__main__':
    unittest.main()

