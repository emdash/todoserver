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

from sockjs.tornado import SockJSConnection
from util import \
    HardFailure, \
    SoftFailure, \
    failUnless, \
    failUnlessRaises, \
    Msg
import json
import time
import auth


class Channel(object):

    '''One-way pub/sub channel. Sending a message to a channel will
    broadcast the message to all subscribing sockets which have joined
    the channel.'''

    def __init__(self, name):
        self.subscribers = set()
        self.name = name
        self.entitled = set([])

    def entitle(self, user):
        self.entitled.add(user)

    def revoke(self, user):
        self.entitled.remove(user)

    def join(self, socket):
        failUnless(socket.username in self.entitled,
                   "You are not allowed to join this channel.")
        self.subscribers.add(socket)
        self.onJoin(socket)

    def leave(self, socket):
        self.subscribers.remove(socket)

    def broadcast(self, msg):
        for subscriber in self.subscribers:
            self.sendTo(subscriber, msg)

    def sendTo(self, subscriber, msg):
        subscriber.send(json.dumps(
                {"type":  "channel-message",
                 "name": self.name,
                 "content": msg}))

    def send(self, socket, msg):
        self.onMessage(socket, msg)

    def onMessage(self, socket, message):
        pass

    def onJoin(self, socket):
        pass

    def onLeave(self, socket):
        pass


class ChannelDispatcher(SockJSConnection):

    '''A tornado SockJS handler which subdivides the SockJS connection
    into multiple channels. Upon receiving a message, it is routed to
    the appropriate channel. It is also the outgoing socket to which
    channels direct outgoing messages.

    An instance of this class is created by Tornado for each incoming
    SockJS connection. Resources common to all channels are treated as
    class-level properties. In particular, the addChannel and
    destroyChannel methods are exposed to provide a mechanism for
    managing channels.
    ''' 

    authenticated = False
    username = None
    auth = auth.PasswordAuthentication()
    attempts = 0
    channels = {}
    lasttry = 0

    def on_open(self, something):
        self.joined = set()

    def on_close(self, something):
        joined = set(self.joined)
        for channel in joined:
            channel.leave(self)

    def on_message(self, msg):
        msg = Msg.fromJSON(msg)

        try:
            self.handleMessage(msg)
        except SoftFailure, e:
            self.send(json.dumps({"type": "error",
                                  "message": e.message}))
        except HardFailure, e:
            print "Hard failure: %s" % e.message
            self.send(json.dumps({"type": "error",
                                  "message": e.message}))
            self.close()

    def failUnlessAuthenticated(self):
        failUnless(self.authenticated, "You are not logged in.")

    def failIfInvalidChannel(self, channel):
        self.failUnlessAuthenticated()
        failUnless(channel in self.channels, "Invalid channel name.")

    def failIfNotJoined(self, channel):
        self.failIfInvalidChannel(channel)
        failUnless(self in self.channels[channel].subscribers, "Not joined to channel.")

    def handleMessage(self, msg):
        if msg.type == "login":
            self.doLogin(msg)
        elif msg.type == "join":
            self.failIfInvalidChannel(msg.name)
            self.doChannelJoin(msg.name)
        elif msg.type == "leave":
            self.failIfNotJoined(msg.name)
            self.doChannelLeave(msg.name)
        elif msg.type == "send":
            self.failIfNotJoined(msg.name)
            self.doChannelSend(msg.name, Msg(**msg.content))

    def doLogin(self, msg):
        self.attempts += 1
        interval = time.time() - self.lasttry
        self.lasttry = time.time()

        failUnless(self.attempts < 5, "Too many attempts." )
        failUnless(self.auth.authUser(msg.user, msg.password),
                   "Access Denied.")
        failUnless(interval > 2, "Minimum retry interval not expired.")

        self.send(json.dumps({"type": "login",
                              "status": "ok"}))
        self.attempts = 0
        self.username = msg.user
        self.authenticated = True

    def doChannelJoin(self, name):
        self.channels[name].join(self)
        self.joined.add(self.channels[name])

    def doChannelLeave(self, name):
        self.channels[name].leave(self)
        self.joined.remove(self.channels[name])

    def doChannelSend(self, channel, msg):
        self.channels[channel].send(self, msg)

    @classmethod
    def addChannel(self, channel, user = None):
        self.channels[channel.name] = channel

        # by default, entitle the user who created the channel
        if user:
            channel.entitle(user)

    @classmethod
    def destroyChannel(self, name):
        channel = self.channels[name]
        channel.broadcast({"type": "destroy"})
        subscribers = set(channel.subscribers)
        for subscriber in subscribers:
            subscriber.doChannelLeave(name)
        del self.channels[name]

    @classmethod
    def addUser(self, user, pwhash):
        self.auth.addUser(user, pwhash)


if __name__ == "__main__":

    class SocketMock(ChannelDispatcher):

        def __init__(self, user):
            self.username = user
            self.last = None
            self.left = False

        def send(self, msg):
            self.last = msg

        def doChannelLeave(self, name):
            self.left = name

    # setup
    channel = Channel("foochan")
    channel.entitle("foouser")
    s1 = SocketMock("foouser")
    s2 = SocketMock("foouser")
    s3 = SocketMock("unknownuser")

    # test that entitled users may join
    channel.join(s1)
    channel.join(s2)

    # test that unentitled users may not join
    failUnlessRaises(lambda: channel.join(s3), SoftFailure)

    # test broadcast
    channel.broadcast({"type": "foo"})
    assert json.loads(s1.last) == json.loads(s2.last) == {
        "type": "channel-message",
        "name": "foochan",
        "content": {"type": "foo"},
    }

    # disconnect one socket. make sure broadcast does not send to it.
    channel.leave(s1)
    channel.broadcast({"type": "bar"})
    assert json.loads(s1.last) == {
        "type": "channel-message",
        "name": "foochan",
        "content": {"type": "foo"}
    }
    assert json.loads(s2.last) == {
        "type": "channel-message",
        "name": "foochan",
        "content": {"type": "bar"}
    }

    # test dispatcher
    ChannelDispatcher.addChannel(channel)
    ChannelDispatcher.addUser("foo", "foobar")
    ChannelDispatcher.addUser("bar", "foobar")

    ChannelDispatcher.destroyChannel("foochan")
    assert s2.left == "foochan"

