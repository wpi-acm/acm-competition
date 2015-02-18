#!/usr/bin/env python
import hashlib
import pickle

from flask_login import UserMixin

USER_FILE = '/tmp/users.pkl'
SHADOW_FILE = '/tmp/shadows.pkl'


class User(UserMixin):
    def __init__(self, username):
        self.username = username

    def get_id(self):
        return self.username

    def __repr__(self):
        return self.username

    @classmethod
    def initialize(cls):
        try:
            with open(USER_FILE, 'r') as pickle_file:
                cls._users = pickle.load(pickle_file)
        except:
            cls._users = {}
        try:
            with open(SHADOW_FILE, 'r') as pickle_file:
                cls._shadows = pickle.load(pickle_file)
        except:
            cls._shadows = {}

    @classmethod
    def update_databases(cls):
        with open(USER_FILE, 'w') as pickle_file:
            pickle.dump(cls._users, pickle_file)
        with open(SHADOW_FILE, 'w') as pickle_file:
            pickle.dump(cls._shadows, pickle_file)

    @classmethod
    def get(cls, userid, default):
        return cls._users.get(userid, default)

    @classmethod
    def authenticate(cls, username, password):
        if username not in cls._shadows:
            cls._shadows[username] = hashlib.sha512(password).hexdigest()
        if cls._shadows[username] == hashlib.sha512(password).hexdigest():
            cls._users[username] = cls(username)
            cls.update_databases()
            return True
        return False
