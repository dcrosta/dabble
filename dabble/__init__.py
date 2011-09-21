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

__all__ = ('configure', 'IdentityProvider', 'ResultStorage', 'ABTest', 'ABParameter')

__version__ = '0.1'

from datetime import datetime
import random

class IdentityProvider(object):
    """:class:`IdentityProvider` is used to identify a user over
    a variety of sessions. It may use any means to do so, so long
    as (to the best of its ability) it returns the same identity
    for the same human being each time its :meth:`get_identity`
    method is called.
    """

    def get_identity(self):
        """:meth:`get_identity` is always called with no arguments,
        and should return a hashable object identifying the user
        for whom A/B trials are currently being run.
        """
        raise Exception('Not implemented. Use a sub-class of IdentityProvider')

class ResultStorage(object):
    """:class:`ResultStorage` provides an interface for storing
    and retrieving A/B test results to a persistent medium, often
    a database or file on disk.

    The :meth:`record_action`, :meth:`is_completed`, :meth:`set_alternative`,
    and :meth:`get_alternative` methods of this class will be called
    synchronously during usage of the framework (e.g. during web page loads),
    so care should be taken to ensure that they operate as efficiently as
    possible.
    """

    def save_test(self, test_name, alternatives):
        """Save an ABTest.

        Unlike the :meth:`record` method, this method should not save
        a new record when called with the same `test_name`. Instead,
        it should check if such a test already exists, and that it has
        the same set of alternatives, and raise if not.

        :Parameters:
          - `test_name`: the string name of the test, as set in
            :meth:`AB.__init__`
          - `alternatives`: a list of string names of the alternatives
            used by the :class:`ABTest`
        """
        raise Exception('Not implemented. Use a sub-class of ResultStorage')

    def record(self, identity, test_name, alternative, action, completed=False):
        """Save a user's action to the persistent medium.

        :Parameters:
          - `identity`: the hashed identity of the user, as returned
            by :meth:`IdentityProvider.get_identity`
          - `test_name`: the string name of the test, as set in
            :meth:`AB.__init__`
          - `alternative`: the postitive integer index of the alternative
            displayed to the user
          - `action`: the string name of the action the user took
          - `completed`: the boolean flag indicating whether the user has
            completed the task associated with this A/B test
        """
        raise Exception('Not implemented. Use a sub-class of ResultStorage')

    def is_completed(self, identity, test_name, alternative):
        """Return `True` if any user action for the given identity, test name,
        and alternative index was :meth:`record`ed with the completed flag
        set to `True`, and `False` otherwise.

        :Parameters:
          - `identity`: the hashed identity of the user, as returned
            by :meth:`IdentityProvider.get_identity`
          - `test_name`: the string name of the test, as set in
            :meth:`AB.__init__`
          - `alternative`: the postitive integer index of the alternative
            displayed to the user
        """
        raise Exception('Not implemented. Use a sub-class of ResultStorage')

    def set_alternative(self, identity, test_name, alternative):
        """Record the given alternative for the user.

        :Parameters:
          - `identity`: the hashed identity of the user, as returned
            by :meth:`IdentityProvider.get_identity`
          - `test_name`: the string name of the test, as set in
            :meth:`AB.__init__`
          - `alternative`: the postitive integer index of the alternative
            displayed to the user
        """
        raise Exception('Not implemented. Use a sub-class of ResultStorage')

    def get_alternative(self, identity, test_name):
        """Return the alternative for the user, as previously set with
        :meth:`set_alternative`. Return `None` if no previous call for
        the given identity and test name has happened.

        :Parameters:
          - `identity`: the hashed identity of the user, as returned
            by :meth:`IdentityProvider.get_identity`
          - `test_name`: the string name of the test, as set in
            :meth:`AB.__init__`
        """
        raise Exception('Not implemented. Use a sub-class of ResultStorage')

    def ab_report(self, test_name, a, b):
        """Return report data for the alternatives of a given test
        where users have either action `a` only, or actions `a` and
        `b`. Other actions, and duplicate or repeated actions are
        ignored.

        Action `a` is ordinarily a "start" action, for instance an
        action denoting "user was shown a page with an A/B test on it".
        Action `b` is ordinarily a "target" action, for instance an
        action denoting "user filled out the form being tested".

        The output is a dictionary in the following format:

            {   test_name: "...",
                alternatives: ["...", "...", ...],
                results: [
                    {   attempted: N,
                        completed: M,
                    }, ...
                ]
            }

        The dictionaries in the `results` array should be in the same
        order as the alternatives listed in the alternatives array,
        which need not be the same order as they are configured in
        the :class:`ABTest`.

        The values `N` and `M` within the result objects should count
        unique identities who attempted or completed the action. An
        attempt is defined as an identity with at least one recorded
        `a` action; a completion is defined as an identity with at
        least one recorded `a` action followed by (chronologically)
        at least one recorded `b` action. Note that "completed" here
        is distinct from the `completed` flag to :meth:`record`, which
        is intended for use from within the running application, not
        for reporting.

        Implementation of the report is delegated to the storage
        class since dabble cannot know the most efficient way to
        query the underlying data store.

        :Parameters:
          - `test_name`: the string name of the test, as set in
            :meth:`AB.__init__`
          - `a`: a string identifying a start action
          - `b`: a string identifying a completion action
        """
        raise Exception('Not implemented. Use a sub-class of ResultStorage')


def configure(identity_provider, result_storage):
    if not isinstance(identity_provider, IdentityProvider):
        raise Exception('identity_provider must extend IdentityProvider')
    if not isinstance(result_storage, ResultStorage):
        raise Exception('result_storage must extend ResultStorage')

    if AB._id_provider is not None or AB._storage is not None:
        raise Exception('configure called multiple times')

    AB._id_provider = identity_provider
    AB._storage = result_storage

class AB(object):
    """TODO.
    """

    # these are set by the configure() function
    _id_provider = None
    _storage = None

    # track the number of alternatives for each
    # named test; helps prevent errors where some
    # parameters have more alts than others
    __n_per_test = {}

    def __init__(self, test_name, alternatives):
        if test_name not in AB.__n_per_test:
            AB.__n_per_test[test_name] = len(alternatives)
        if len(alternatives) != AB.__n_per_test[test_name]:
            raise Exception('Wrong number of alternatives')

        self.test_name = test_name
        self.alternatives = alternatives

    @property
    def identity(self):
        return hash(self._id_provider.get_identity())

    @property
    def alternative(self):
        alternative = self._storage.get_alternative(self.identity, self.test_name)

        if alternative is None:
            alternative = random.randrange(len(self.alternatives))
            self._storage.set_alternative(self.identity, self.test_name, alternative)

        return alternative

class ABTest(AB):
    # can be added to a class definition to define information
    # about the AB test, as will be shown in the admin UI.
    # additionally, if the ABTest is assigned as a class attribute,
    # it contains some information about the state of the test
    #
    #   class ShowAForm(app.page):
    #       path = '/page/with/form'
    #       abtest = ABTest('my_test', ['Complete Form', 'Brief Form']
    #       formname = ABParameter('my_test', ['form_one', 'form_two'])
    #
    #       def GET(self):
    #           if abtest.completed:
    #               raise web.seeother('/page/after/form/completion')
    #           render('template.html', form=self.get_form(self.formname))

    def __init__(self, test_name, alternatives):
        super(ABTest, self).__init__(test_name, alternatives)
        self._storage.save_test(test_name, alternatives)

    def record(self, action, completed=False):
        self._storage.record(
            self.identity,
            self.test_name,
            self.alternative,
            action,
            completed
        )

    def is_completed(self):
        self._storage.is_completed(
            self.identity,
            self.test_name,
            self.alternative
        )


class ABParameter(AB):
    # a descriptor object which can be used to vary parameters
    # in a class definition according to A/B testing rules.
    #
    # each viewer who views the given class will always be
    # consistently shown the Nth choice from among the
    # alternatives, even between different attributes in the
    # class, so long as the name is the same between them

    def __get__(self, instance, owner):
        return self.alternatives[self.alternative]


