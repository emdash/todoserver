## Commmon Code
import json

class HardFailure(Exception): pass


class SoftFailure(Exception): pass


def failUnless(self, condition, msg=None, hard=False):
    if hard:
        if not condition:
            raise HardFailure(msg)
    else:
        if not condition:
            raise SoftFailure(msg)


class Msg(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        self.values = kwargs

    @classmethod
    def fromJSON(self, string):
        return Msg(**json.loads(string))
