#! /usr/bin/python

from tornado import web, ioloop
from sockjs.tornado import SockJSRouter
from channel import Channel, ChannelDispatcher
from uuid import uuid4
from util import HardFailure, SoftFailure, failUnless, Msg
import json


class List(object):

    def __init__(self, name):
        self.id = str(uuid4())
        self.channel = Channel(self.id)
        self.channel.on_message = self.onMessage
        self.name = name
        self.items = []

    def onMessage(self, socket, msg):
        if msg.type == "insert":
            items.insert(msg.index, msg.attrs)
            self.channel.broadcast(
                {"type": "insert",
                 "index": msg.index,
                 "attrs": msg.attrs})
        elif msg.type == "delete":
            del items[msg.index]
            self.channel.broadcast(
                {"type": "delete",
                 "index": msg.index})
        elif msg.type == "update":
            item = self.items[msg.index]
            item.update(msg.attrs)
            self.channel.broadcast(
                {"type": "update",
                 "index": msg.index,
                 "attrs": msg.attrs})


class Server(object):

    def __init__(self):
        Router = SockJSRouter(ChannelDispatcher, '/todo')
        self.app = web.Application(Router.urls)

        self.lists = [List("Foo"), List("bar")]
        self.control = Channel("control")
        self.control.onMessage = self.controlMessageHandler
        ChannelDispatcher.addChannel("control", self.control)

    def controlMessageHandler(self, channel, socket, msg):
        if msg.type == "get-lists":
            for list in self.lists:
                channel.sendTo(
                    socket,
                    {"type": "list-added",
                     "name": list.name,
                     "id": list.id})

    def run(self):
        self.app.listen(8080)
        ioloop.IOLoop.instance().start()


s = Server()
s.run()
