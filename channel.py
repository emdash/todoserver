## One-way pub-sub channel over SockJS
## Sending to the channel will send a message to all subscribers

from sockjs.tornado import SockJSConnection
from util import HardFailure, SoftFailure, failUnless, Msg
import json


class Channel(object):

    def __init__(self, name):
        self.subscribers = set()
        self.name = name

    def join(self, socket):
        self.subscribers.add(socket)

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
        self.onMessage(self, socket, msg)

    def onMessage(self, socket, message):
        pass

    def onJoin(self, socket):
        pass

    def onLeave(self, socket):
        pass


class ChannelDispatcher(SockJSConnection):

    authenticated = False
    channels = {}

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
            self.failUnlessAuthenticated()
            self.failIfInvalidChannel(msg.name)
            self.doChannelJoin(msg.name)
        elif msg.type == "leave":
            self.failIfNotJoined(msg.name)
            self.doChannelLeave(msg.name)
        elif msg.type == "send":
            self.failIfNotJoined(msg.name)
            self.doChannelSend(msg.name, Msg(**msg.content))

    def doLogin(self, msg):
        failUnless(msg.user == "dotsony" and msg.password == "foobar", "Access Denied.")
        self.send(json.dumps({"type": "login",
                              "status": "ok"}))
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
    def addChannel(self, channel):
        self.channels[channel.name] = channel

    @classmethod
    def destroyChannel(self, name):
        subscribers = set(self.channels[name].subscribers)
        for subscriber in subscribers:
            subscribers.doChannelLeave(name)
        del self.channels[name]
