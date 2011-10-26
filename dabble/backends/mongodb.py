# Copyright (c) 2011, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__all__ = ('MongoResultStorage', )

from dabble import ResultStorage
from dabble.util import *

from datetime import datetime
from random import randrange
from bson.son import SON
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

class MongoResultStorage(ResultStorage):

    def __init__(self, database, namespace='dabble'):
        """Set up storage in MongoDB (using PyMongo) for A/B test results.
        Setup requires at least a :class:`pymongo.database.Database` instance,
        and optionally accepts a `namespace` parameter, which is used to
        generate collection names used for storage. Three collections will be
        used, named "<namespace>.tests" and "<namespace>.results".

        :Parameters:
          - `database`: a :class:`pymongo.database.Database` instance
            in which to create the two collections for result storage
          - `namespace`: the name prefix used to name collections
        """
        if not isinstance(database, Database):
            raise Exception('"database" argument is not a pymongo.database.Database')

        self.namespace = namespace

        self.tests = database['%s.tests' % namespace]
        self.results = database['%s.results' % namespace]

        self.results.ensure_index([('t', ASCENDING), ('i', ASCENDING)])

    def save_test(self, test_name, alternatives, steps):
        test = self.tests.find_one({'_id': test_name})

        if test and test['a'] != alternatives:
            raise Exception('test "%s" already exists with different alternatives' % test_name)

        elif not test:
            self.tests.save({
                '_id': test_name,
                'a': alternatives,
                's': steps,
            }, safe=True)

    def record(self, identity, test_name, alternative, action):
        self.results.update({
            'i': identity,
            't': test_name,
            'n': alternative},
            {'$addToSet': {'s': action}},
            upsert=True)

    def has_action(self, identity, test_name, alternative, action):
        return self.results.find_one({'i': identity, 't': test_name, 'n': alternative, 's': action}) is not None

    def set_alternative(self, identity, test_name, alternative):
        # XXX: possible race condition, but one will win, and
        # for A/B testing that's probably OK.
        result = self.results.find_one({'i': identity, 't': test_name})
        if not result:
            self.results.save({'i': identity, 't': test_name, 'n': alternative, 's': []})

        elif result and result['n'] != alternative:
            raise Exception('different alternative already set for identity %s' % identity)

    def get_alternative(self, identity, test_name):
        result = self.results.find_one({'i': identity, 't': test_name}) or {}
        return result.get('n')

    def report(self, test_name):
        test = self.tests.find_one({'_id': test_name})
        if test is None:
            raise Exception('unknown test "%s"' % test_name)

        report = {
            'test_name': test_name,
            'results': []
        }

        trials = sparsearray(int)

        for result in self.results.find({'t': test_name}):
            if result['s'] != test['s'][:len(result['s'])]:
                # invalid order of steps recorded
                continue

            for i in xrange(len(result['s'])):
                trials[result['n']][i] += 1

        for i, alternative in enumerate(test['a']):
            funnel = []
            alt = {'alternative': alternative, 'funnel': funnel}
            report['results'].append(alt)
            for s, stepspair in enumerate(pairwise(test['s'])):
                att = trials[i][s]
                con = trials[i][s + 1]
                funnel.append({
                    'stage': stepspair,
                    'attempted': att,
                    'converted': con,
                })

        return report

    def list_tests(self):
        """Return a list of string test names known."""
        return [t['_id'] for t in self.tests.find(fields=['_id'])]

