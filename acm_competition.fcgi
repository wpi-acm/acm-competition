#!/usr/bin/python
from flup.server.fcgi import WSGIServer
from server import app

if __name__ == '__main__':
    WSGIServer(app, bindAddress='/tmp/acm_competition-fcgi.sock').run()