from util import failUnless, failUnlessRaises, SoftFailure

class Rights(object):

    def __init__(self, pwhash):
        self.pwhash = pwhash
        self.actions = set([])

class PasswordAuthentication(object):

    def __init__(self):
        self.credentials = {}

    def userIsValid(self, username):
        return username in self.credentials

    def failIfInvalid(self, username):
        failUnless(self.userIsValid(username),
                   "Invalid username.")

    def addUser(self, username, pwhash):
        failUnless(not self.userIsValid(username),
                   "User exists.")
        # XXX: salt password
        self.credentials[username] = Rights(pwhash)

    def delUser(self, username):
        failUnless(self.userIsValid(username),
                   "Invaid username.")
        del self.credentials[username]

    def authUser(self, username, pwhash, action = None):
        return ((username in self.credentials) and
                (pwhash == self.credentials[username].pwhash))

    def userCanDo(self, username, action):
        self.failIfInvalid(username)
        return (action in self.credentials[username].actions)

    def entitleUser(self, username, action):
        self.failIfInvalid(username)
        self.credentials[username].actions.add(action)

    def unentitleUser(self, username, action):
        self.failIfInvalid(username)
        self.credentials[username].remove(action)

if __name__ == "__main__":

    # Setup
    auth = PasswordAuthentication()

    # create a user
    auth.addUser("foo", "fubar")

    # ensure that trying to create a duplicate user fails
    failUnlessRaises(lambda: auth.addUser("foo", "foobar"),
                     SoftFailure)

    # ensure that trying to delete an invalid user fails
    failUnlessRaises(lambda: auth.delUser("bar"),
                     SoftFailure)

    # ensure that trying to authenticate a nonexistant user fails
    assert not auth.authUser("bar", "bad")

    # ensure that trying to authenticae an existing user with a bad
    # password fails.
    assert not auth.authUser("foo", "foobar")

    # ensure authentication works with valid credentials
    assert auth.authUser("foo", "fubar")

    # ensure that access control on an invalid user raises an error
    failUnlessRaises(lambda: auth.userCanDo("bar", "foo-action"),
                     SoftFailure)

    # ensure that access control on a valid user does not raise an
    # error
    assert not auth.userCanDo("foo", "foo-action")

    # ensure that access control on a valid user with a valid action
    # works
    auth.entitleUser("foo", "foo-action")
    assert auth.userCanDo("foo", "foo-action")

    # ensure we can delete a valid user
    auth.delUser("foo")

