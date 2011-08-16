# Dabble

Dabble is a simple A/B testing framework for Python. Using dabble, you
configure your tests in code, collect results, and analyze them later to
make informed decisions about design changes, feature implementations, etc.

You define an A/B test in dabble with class `ABTest`, which describes the
test name and the names of each of the alternatives. You then define one or
more `ABParameter`s, which contain the values you wish to vary for each
alternative in the test. Each test can have one or more alternatives, though
the most common case is to have 2 (hence "A/B testing").

Dabble works best in web frameworks which use class-based views, though it
is certainly possible to use dabble in a framework with function-based
views.

## Example

    import dabble
    dabble.configure(
        CookieIdentityProvider('dabble_id'),
        FSResultStorage('/path/to/results.data')
    )

    class Signup(page):
        path = '/signup'

        signup_button = ABTest('signup button', ['Red Button', 'Green Button'])
        button_color = ABParameter('signup button', ['#ff0000', '#00ff00'])

        def GET(self):
            self.signup_button.record('show')
            return render('index.html', button_color=self.button_color)

        def POST(self):
            self.signup_button.record('signup')
            return redirect('/account')

Behind the scenes, dabble has used a cookie for each user on your site to
assigne them each an *identity*, so that each user always ever sees the same
*alternative*. Users may visit the homepage many times over many browsing
sessions, but as long as they have the same cookie present in their browser,
they will always see either the red or the green button, depending on which
was chosen the first time the viewed the page.

When a user signs up, the `record()` method of `ABTest` is called, to track
the user's action. Later on, reports can be generated to determine whether
the red or the green button induced more users to sign up.

## Configuring Dabble

In addition to `ABTest` and `ABParameter`, dabble also needs an
`IdentityProvider` and a `ResultsStorage`. Dabble provides several
alternatives for each of these out of the box, and it is also
straightforward to write your own.

`IdentityProvider`s should make their best possible effort to always
identify individuals, rather than browsing sessions (particularly if cookies
are set to expire when the user closes his/her browser). If you are testing
a feature that requires users to be logged in, then their username is a good
choice for identity.

`ResultsStorage` stores configuration and results of A/B tests, and provides
some facilities for generating reports based on the stored results. Dabble
provides several backends, including `MongoResultsStorage`, and
`FSResultsStorage`.

At this time it is not possible to configure different `IdentityProvider`s
or `ResultsStorage`s for different tests within the same application.

