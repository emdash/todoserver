# The MIT License (MIT)
#
# Copyright (c) 2014 Brandon Lewis
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import json
import os

class HardFailure(Exception): pass


class SoftFailure(Exception): pass


def failUnless(condition, msg=None, hard=False):
    if hard:
        if not condition:
            raise HardFailure(msg)
    else:
        if not condition:
            raise SoftFailure(msg)


def require(msg, attr):
    failUnless(hasattr(msg, attr), "Required attribute %r missing" % attr)


class Msg(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        self.values = kwargs

    @classmethod
    def fromJSON(self, string):
        return Msg(**json.loads(string))


def rename(old, new):
    if os.path.exists(old):
        os.rename(old, new)

def failUnlessRaises(func, exc):
    raised = False

    try:
        func()
    except exc:
        raised = True
    finally:
        assert raised
