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

from datetime import datetime
from random import randrange
from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from bson.son import SON

class MongoResultStorage(ResultStorage):

    def __init__(self, database, namespace='dabble'):
        """Set up storage in MongoDB (using PyMongo) for A/B test results.
        Setup requires at least a :class:`pymongo.database.Database` instance,
        and optionally accepts a `namespace` parameter, which is used to
        generate collection names used for storage. Three collections will be
        used, named "<namespace>.tests", "<namespace>.results", and
        "<namespace>.alts".

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
        self.alts = database['%s.alts' % namespace]

        self.tests.ensure_index([
            ('t', ASCENDING),  # test name
        ], unique=True)

        self.results.ensure_index([
            ('i', ASCENDING),
            ('d', ASCENDING),
        ])
        self.results.ensure_index([
            ('i', ASCENDING),  # identity
            ('t', ASCENDING),  # test name
            ('n', ASCENDING),  # alternative
            ('c', DESCENDING), # completed
        ])

        self.alts.ensure_index([
            ('i', ASCENDING),  # identity
            ('t', ASCENDING),  # test name
            ('n', ASCENDING),  # alternative
        ], unique=True)

    def save_test(self, test_name, alternatives):
        test = self.tests.find_one({'t': test_name})

        if test and test['a'] != alternatives:
            raise Exception('test "%s" already exists with different alternatives' % test_name)

        elif not test:
            self.tests.save({
                't': test_name,
                'a': alternatives,
            }, safe=True)

    def record(self, identity, test_name, alternative, action, completed=False):
        self.results.save({
            'i': identity,
            't': test_name,
            'n': alternative,
            'a': action,
            'c': completed,
            'd': datetime.utcnow(),
        }, safe=True)

    def is_completed(self, identity, test_name, alternative):
        return self.results.find_one({
            'i': identity,
            't': test_name,
            'n': alternative,
            'c': True
        }) is not None

    def set_alternative(self, identity, test_name, alternative):
        try:
            self.alts.save({
                'i': identity,
                't': test_name,
                'n': alternative
            })
        except DuplicateKeyError:
            raise Exception('different alternative already set for identity %s' % identity)

    def get_alternative(self, identity, test_name):
        alt = self.alts.find_one({'i': identity, 't': test_name}) or {}
        return alt.get('n')

    def ab_report(self, test_name, a, b):
        test = self.tests.find_one({'t': test_name})
        if test is None:
            raise Exception('unknown test "%s"' % test_name)

        db = self.results.database
        # TODO: better collection name?
        intermediate_name = '%s.report.%s' % (self.namespace, randrange(1000, 9999))

        pa = a.replace('"', r'\"')
        pb = b.replace('"', r'\"')

        map_func = """
        function() {
            emit({i: this.i, n: this.n}, {a: this.a === "%s", b: this.a === "%s", d: this.d});
        }""" % (pa, pb)

        reduce_func = """
        function(key, values) {
            function cmp_d(x, y) {
                if (x.d < y.d) return -1;
                if (y.d < x.d) return 1;
                return 0;
            }
            values.sort(cmp_d);
            var out = {a: false, b: false, d: values[values.length-1].d};
            values.forEach(function(obj) {
                out.a = out.a || obj.a;
                out.b = (out.a && obj.b) || out.b;
            });
            return out;
        }"""

        finalize_func = """
        function(key, value) {
            return {a: value.a, b:value.b};
        }"""

        intermediate = self.results.map_reduce(
            map=map_func,
            reduce=reduce_func,
            finalize=finalize_func,
            out=intermediate_name,
            query={'t': test_name},
            sort=SON([('i', ASCENDING), ('d', ASCENDING)]),
        )

        results = intermediate.group(
            key={'_id.n': 1, 'value': 1},
            initial={'count': 0},
            reduce="function(obj, prev) { prev.count++; }",
            condition={}
        )
        intermediate.drop()

        out = {
            'test_name': test_name,
            'alternatives': test['a'],
            'results': [
                {'attempted': 0, 'completed': 0}
                for alt in test['a']
            ]
        }

        for result in results:
            if result['value']['a']:
                out['results'][int(result['_id.n'])]['attempted'] += result['count']
                if result['value']['b']:
                    out['results'][int(result['_id.n'])]['completed'] += result['count']

        return out

