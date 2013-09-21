#! /usr/bin/python

from tornado import web, ioloop
from sockjs.tornado import SockJSRouter, SockJSConnection

class EchoConnection(SockJSConnection):

    def on_open(self, something):
        print "New connection"

    def on_message(self, msg):
        print msg
        self.send(msg)

EchoRouter = SockJSRouter(EchoConnection, '/echo')
app = web.Application(EchoRouter.urls)
app.listen(8080)
ioloop.IOLoop.instance().start()
