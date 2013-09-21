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
        self.channel.onMessage = self.onMessage
        self.channel.onJoin = self.onJoin
        self.name = name
        self.items = []

    def onJoin(self, socket):
        for i, item in enumerate(self.items):
            self.channel.sendTo(socket,
                {"type": "insert",
                 "index": i,
                 "attrs": item})

    def onMessage(self, socket, msg):
        if msg.type == "insert":
            self.items.insert(msg.index, msg.attrs)
            self.channel.broadcast(
                {"type": "insert",
                 "index": msg.index,
                 "attrs": msg.attrs})
        elif msg.type == "delete":
            del self.items[msg.index]
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

        self.control = Channel("control")
        self.control.onMessage = self.controlMessageHandler
        ChannelDispatcher.addChannel(self.control)

        self.lists = []
        self.init()

    def controlMessageHandler(self, socket, msg):
        if msg.type == "get-lists":
            for list in self.lists:
                self.control.sendTo(
                    socket,
                    {"type": "list-added",
                     "name": list.name,
                     "id": list.id})
        elif msg.type == "create":
            self.createList(msg.name)
        

    def createList(self, name):
        l = List(name)
        self.lists.append(l)
        ChannelDispatcher.addChannel(l.channel)
        self.control.broadcast(
            {"type": "list-added",
             "name": name,
             "id": l.id})

    def flush(self):
        output = []
        for list in self.lists:
            output.append({"name": list.name,
                           "items": list.items})
        json.dump(output, open("data.txt", "w"))

    def init(self):
        try:
            data = json.load(open("data.txt", "r"))
            for l in data:
                self.createList(l["name"])
                for item in l["items"]:
                    l.insert(-1, item)
        except:
            pass

    def run(self):
        self.app.listen(8080)
        flusher = ioloop.PeriodicCallback(self.flush, 5000)
        flusher.start()
        ioloop.IOLoop.instance().start()



s = Server()
s.run()
