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

__all__ = ('FSResultStorage', )

from dabble import ResultStorage
from os.path import exists, join, abspath
from os import SEEK_END
from lockfile import FileLock
import json

# TODO: factor out scanning files for a matching record
# TODO: factor out json dumping to remove excess spaces

class FSResultStorage(ResultStorage):

    def __init__(self, directory):
        """Set up storage in the filesystem for A/B test results.

        :Parameters:
          - `directory`: an existing directory in the filesystem where
            results can be stored. Several files with the ".dabble"
            extension will be created.
          - `namespace`: the name prefix used to name collections
        """
        self.directory = abspath(directory)

        if not exists(self.directory):
            raise Exception('directory "%s" does not exist' % self.directory)

        self.lock = FileLock(join(self.directory, 'lock.dabble'))

        self.tests_path = join(self.directory, 'tests.dabble')
        self.results_path = join(self.directory, 'results.dabble')
        self.alts_path = join(self.directory, 'alts.dabble')

    def save_test(self, test_name, alternatives):
        if exists(self.tests_path):
            fp = file(self.tests_path, 'r')
            for line in fp:
                data = json.loads(line)
                if data['t'] == test_name:
                    if data['a'] != alternatives:
                        raise Exception(
                            'test "%s" already exists with different alternatives' % test_name)
                    return

        with self.lock:
            # else test did not exist
            fp = file(self.tests_path, 'a')
            fp.seek(0, SEEK_END)
            fp.write(json.dumps({'t': test_name, 'a': alternatives}))
            fp.write('\n')
            fp.close()

    def record(self, identity, test_name, alternative, action, completed=False):
        with self.lock:
            fp = file(self.results_path, 'a')
            fp.seek(0, SEEK_END)
            fp.write(json.dumps({
                'i': identity,
                't': test_name,
                'n': alternative,
                'a': action,
                'c': completed
            }))
            fp.write('\n')
            fp.close()

    def is_completed(self, identity, test_name, alternative):
        if not exists(self.results_path):
            return False

        fp = file(self.results_path, 'r')
        for line in fp:
            data = json.loads(line)
            if data['i'] == identity and data['t'] == test_name and \
               data['n'] == alternative and data['c']:
                return True

        return False

    def set_alternative(self, identity, test_name, alternative):
        if exists(self.alts_path):
            fp = file(self.alts_path, 'r')
            for line in fp:
                data = json.loads(line)
                if data['i'] == identity and data['t'] == test_name:
                    raise Exception(
                        'different alternative already set for identity %s' % identity)

        with self.lock:
            fp = file(self.alts_path, 'a')
            fp.seek(0, SEEK_END)
            fp.write(json.dumps({
                'i': identity,
                't': test_name,
                'n': alternative,
            }))
            fp.write('\n')
            fp.close()

    def get_alternative(self, identity, test_name):
        if not exists(self.alts_path):
            return None

        fp = file(self.alts_path, 'r')
        for line in fp:
            data = json.loads(line)
            if data['i'] == identity and data['t'] == test_name:
                return data['n']

        return None

    def ab_report(self, test_name, a, b):
        test = None

        fp = file(self.tests_path, 'r')
        for line in fp:
            data = json.loads(line)
            if data['t'] == test_name:
                test = data
                break

        if test is None:
            raise Exception('unknown test "%s"' % test_name)

        out = {
            'test_name': test_name,
            'alternatives': test['a'],
            'results': [
                {'attempted': set(), 'completed': set()}
                for alt in test['a']
            ]
        }

        fp = file(self.results_path, 'r')
        for line in fp:
            data = json.loads(line)
            if data['t'] == test_name:
                result = out['results'][data['n']]
                if data['a'] == a:
                    result['attempted'].add(data['i'])
                elif data['a'] == b and data['i'] in result['attempted']:
                    result['completed'].add(data['i'])

        for result in out['results']:
            result['attempted'] = len(result['attempted'])
            result['completed'] = len(result['completed'])

        return out

