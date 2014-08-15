#! /usr/bin/python

from tornado import web, ioloop, websocket

def run_test():
    print "got here"

ws = websocket.websocket_connect(
    "ws://localhost:8001/todo", 
    callback=run_test)

ioloop.IOLoop.instance().start()
