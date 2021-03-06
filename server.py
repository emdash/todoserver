#! /usr/bin/python
#
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


from tornado import web, ioloop
from sockjs.tornado import SockJSRouter
from channel import Channel, ChannelDispatcher
from uuid import uuid4
from util import \
    HardFailure, \
    SoftFailure, \
    failUnless, \
    Msg, \
    rename, \
    require,\
    requireEnv

import json
import os
import time

PORT = int(requireEnv("TODO_PORT"))
FLUSH_INTERVAL = int(requireEnv("TODO_FLUSH_INTERVAL"))
DATA_PATH = requireEnv("TODO_DATA_PATH")
BACKUP_PATH = requireEnv("TODO_BACKUP_PATH")
assert os.path.exists(BACKUP_PATH)
assert os.path.isdir(BACKUP_PATH)
CREDENTIALS_PATH = requireEnv("TODO_CREDENTIALS_PATH")
TEMP_PATH = requireEnv("TODO_TEMP_PATH")

class List(object):

    def __init__(self, name, id=None):
        self.id = id if id else str(uuid4())
        self.channel = Channel(self.id)
        self.channel.onMessage = self.onMessage
        self.channel.onJoin = self.onJoin
        self.name = name
        self.items = []
        self.dirty = False

    def entitle(self, user):
        self.channel.entitle(user)

    def entitled(self, user):
        return user in self.channel.entitled

    def onJoin(self, socket):
        for i, item in enumerate(self.items):
            self.channel.sendTo(socket,
                {"type": "insert",
                 "index": i,
                 "attrs": item})

    def onMessage(self, socket, msg):
        require(msg, "index")

        if msg.type == "insert":
            require(msg, "attrs")
            self.items.insert(msg.index, msg.attrs)
            self.channel.broadcast(
                {"type": "insert",
                 "index": msg.index,
                 "attrs": msg.attrs})
            self.dirty = True

        elif msg.type == "delete":
            del self.items[msg.index]
            self.channel.broadcast(
                {"type": "delete",
                 "index": msg.index})
            self.dirty = True

        elif msg.type == "update":
            require(msg, "attrs")
            item = self.items[msg.index]
            item.update(msg.attrs)
            self.channel.broadcast(
                {"type": "update",
                 "index": msg.index,
                 "attrs": msg.attrs})
            self.dirty = True


class Server(object):

    def __init__(self):
        Router = SockJSRouter(ChannelDispatcher, '/todo')
        self.app = web.Application(Router.urls)

        self.control = Channel("control")
        self.control.onMessage = self.controlMessageHandler
        ChannelDispatcher.addChannel(self.control)

        self.lists = []
        self.byId = {}
        self.init()
        self.dirty = True

    def controlMessageHandler(self, socket, msg):
        if msg.type == "get-lists":
            for list in self.lists:
                if not list.entitled(socket.username):
                    continue

                self.control.sendTo(
                    socket,
                    {"type": "list-added",
                     "name": list.name,
                     "id": list.id})
        elif msg.type == "create":
            require(msg, "name")
            self.createList(msg.name, None, socket.username)
            self.dirty = True
        elif msg.type == "rename":
            require(msg, "id")
            require(msg, "name")
            self.byId[msg.id].name = msg.name
            self.control.broadcast({"type": "list-rename",
                                    "id": msg.id,
                                    "name": msg.name})
            self.dirty = True
        elif msg.type == "delete":
            require(msg, "id")
            self.deleteList(msg.id)
            self.dirty = True

    def createList(self, name, id=None, username=None):
        l = List(name, id)
        self.lists.append(l)
        self.byId[l.id] = l
        ChannelDispatcher.addChannel(l.channel, username)
        self.control.broadcast(
            {"type": "list-added",
             "name": name,
             "id": l.id})

    def deleteList(self, id):
        self.lists.remove(self.byId.pop(id))
        ChannelDispatcher.destroyChannel(id)
        self.control.broadcast({"type": "list-delete",
                                "id": id})

    def flush(self):
        if self.isDirty():
            print "syncdb"
            output = []
            for l in self.lists:
                output.append({"name": l.name,
                               "id": l.id,
                               "items": l.items,
                               "users": list(l.channel.entitled)})
            json.dump(output, open(TEMP_PATH, "w"))
            rename(DATA_PATH, "%s/%d.txt" % (BACKUP_PATH, int(time.time())))
            rename(TEMP_PATH, DATA_PATH)
            self.clearDirty()

    def clearDirty(self):
        for l in self.lists:
            l.dirty = False
        self.dirty = False

    def isDirty(self):
        return self.dirty or any((l.dirty for l in self.lists))

    def init(self):
        creds = json.load(open(CREDENTIALS_PATH, "r"))
        for user in creds:
            ChannelDispatcher.addUser(
                user["username"],
                user["pwhash"])
            self.control.entitle(user["username"])

        if not os.path.exists(DATA_PATH):
            return

        data = json.load(open(DATA_PATH, "r"))
        for l in data:
            self.createList(l["name"], l["id"])
            lst = self.byId[l["id"]]
            for item in l["items"]:
                lst.items.append(item)
            for user in l["users"]:
                lst.entitle(user)


    def run(self):
        self.app.listen(PORT)
        flusher = ioloop.PeriodicCallback(self.flush, FLUSH_INTERVAL)
        flusher.start()
        ioloop.IOLoop.instance().start()


s = Server()
s.run()
