#!/usr/bin/env python
import json
import os
import os.path
import pickle
from collections import defaultdict, OrderedDict
from datetime import datetime

from dateutil.parser import parse
from dateutil.tz import tzutc

EPOCH = datetime(1970, 1, 1, tzinfo=tzutc())
PROJECT_DIR = os.path.split(os.path.realpath(__file__))[0]
CHALLENGE_DIR = os.path.join(PROJECT_DIR, 'challenges')
ENABLED_CHALLENGES = [
    'echo',
    'palindrome',
    'twos',
    'string_compression',
    'factorial',
    'lcs',
    'weighted_average',
    'reverse_words',
    'lights'
]


class Challenge(object):
    def __init__(self, json):
        self.json = json
        self.name = json['name']
        self.tag = json['tag']
        self.weights = json['weights']
        self.description = json['description']
        self.official = json['official']
        self.sample = json['sample']
        self.sample_input = self.sample['test_cases']
        self.sample_output = self.sample['solutions']

        self.reset_points()
        self.leaderboards = OrderedDict([
            ('Development Speed', []),
            ('Time Efficiency', []),
            ('Memory Efficiency', [])
        ])
        if 'data' in json:
            self.dev_speed = json['data']['dev_speed']
            self.speed = json['data']['speed']
            self.memory = json['data']['memory']
        else:
            self.dev_speed = {}
            self.speed = {}
            self.memory = {}
        self.langs = json.get('langs', {})

    def reset_points(self):
        self.overall_points = defaultdict(lambda: 0)
        self.points = {
            'Development Speed': defaultdict(lambda: 0),
            'Time Efficiency': defaultdict(lambda: 0),
            'Memory Efficiency': defaultdict(lambda: 0)
        }

    def sample_input_as_html(self):
        return "<br />-----<br />".join(self.sample_input).replace('\n', '<br />')
    
    def sample_output_as_html(self):
        return "<br />-----<br />".join(self.sample_output).replace('\n', '<br />')

    def check(self, results, test):
        if not results:
            return False
        
        solutions = (self.sample if test else self.official)['solutions']
        if results['stdout'] == solutions:
            return True
        else:
            return results['stdout'] == [s + '\n' for s in solutions]

    def get_overall_points(self):
        sorted_data = sorted(
            self.overall_points.items(),
            key=lambda v: v[1],
            reverse=True)
        return enumerate(sorted_data, start=1)

    def register_solution(self, username, results, lang):
        dev = self.dev_speed.get(username, None)
        spd = self.speed.get(username, None)
        mem = self.memory.get(username, None)

        new_dev = (parse(results['created_at']) - EPOCH).total_seconds()
        new_spd = sum(results['time'])
        new_mem = sum(results['memory'])

        self.dev_speed[username] = min(dev, new_dev) or new_dev
        self.speed[username] = min(spd, new_spd) or new_spd
        self.memory[username] = min(mem, new_mem) or new_mem

        if username not in self.langs:
            self.langs[username] = {}
        if self.dev_speed[username] == new_dev:
            self.langs[username]["Development Speed"] = lang
        if self.speed[username] == new_spd:
            self.langs[username]["Time Efficiency"] = lang
        if self.memory[username] == new_mem:
            self.langs[username]["Memory Efficiency"] = lang

    def recalculate_points(self):
        def second_item(v):
            return v[1]

        def calculate_points(values, key, long_key):
            best = values[0][1]
            worst = values[-1][1]
            last_value = None
            for user, value in values:
                try:
                    pts = 50 * (value - worst) / float(best - worst) + 50
                except ZeroDivisionError:
                    pts = 100
                points = pts * self.weights[key]
                self.points[long_key][user] += points
                self.overall_points[user] += points

        dev = sorted(self.dev_speed.items(), key=second_item)
        spd = sorted(self.speed.items(), key=second_item)
        mem = sorted(self.memory.items(), key=second_item)
        if not dev or not spd or not mem:
            return

        self.reset_points()
        calculate_points(dev, 'dev', 'Development Speed')
        calculate_points(spd, 'spd', 'Time Efficiency')
        calculate_points(mem, 'mem', 'Memory Efficiency')

    def get_user_category_value(self, username, category):
        data = {
            'Development Speed': self.dev_speed,
            'Time Efficiency': self.speed,
            'Memory Efficiency': self.memory
        }
        return data[category][username]

    def get_user_category_lang(self, username, category):
        return self.langs[username][category]

    def recalculate_leaderboards(self):
        self.recalculate_points()
        for section, data in self.points.iteritems():
            sorted_data = enumerate(
                sorted(data.items(), key=lambda v: v[1], reverse=True), 
                start=1)
            self.leaderboards[section] = [
                (i, item[0], item[1], 
                    self.get_user_category_value(item[0], section),
                    self.get_user_category_lang(item[0], section))
                for i, item in sorted_data
            ]
        self.__class__.update_databases()

    def has_no_solutions(self):
        return len(self.dev_speed) == 0

    def to_dict(self):
        return {
            "name": self.name,
            "tag": self.tag,
            "weights": self.weights,
            "description": self.description,
            "official": self.official,
            "sample": self.sample,
            "official": self.official,
            "data": {
                "dev_speed": self.dev_speed,
                "speed": self.speed,
                "memory": self.memory
            },
            "langs": self.langs
        }

    def __repr__(self):
        return self.name

    @classmethod
    def initialize(cls):
        cls._challenges = [
            Challenge(
                json.load(
                    open(os.path.join(CHALLENGE_DIR, 
                                      "{0}.json".format(tag)), 'r')))
            for tag in ENABLED_CHALLENGES
        ]
        try:
            with open('/tmp/challenges.pkl', 'r') as challenges:
                original_challenges = [Challenge(c) for c in pickle.load(challenges)]
            for challenge in original_challenges:
                for i, new_challenge in enumerate(cls._challenges):
                    if new_challenge.tag == challenge.tag:
                        cls._challenges[i].dev_speed = challenge.dev_speed
                        cls._challenges[i].speed = challenge.speed
                        cls._challenges[i].memory = challenge.memory
                        cls._challenges[i].langs = challenge.langs
        except:
            pass

    @classmethod
    def update_databases(cls):
        with open('/tmp/challenges.pkl', 'w') as pickle_file:
            pickle.dump([c.to_dict() for c in cls._challenges], pickle_file)

    @classmethod
    def get(cls, id_):
        return cls._challenges[int(id_) - 1]

    @classmethod
    def all(cls):
        return cls._challenges

    @classmethod
    def recalculate_all(cls):
        [c.recalculate_leaderboards() for c in cls._challenges]

    @classmethod
    def get_user_points(cls, username):
        return sum([challenge.overall_points.get(username, 0)
                    for challenge in cls._challenges])
