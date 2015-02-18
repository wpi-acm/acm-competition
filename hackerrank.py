#!/usr/bin/env python
import os
import json
import requests

API_URL = "http://api.hackerrank.com/checker/submission.json"

class HackerRankSubmitter(object):
    def __init__(self):
        self.langs = self.get_langs(force=True)

    def get_langs(self, force=False):
        print "getting langs"    
        if force:
            r = requests.get("http://api.hackerrank.com/checker/languages.json").text
            print "got langs"
            self.langs = json.loads(r)
        return self.langs

    def submit(self, file_content, lang, challenge, test=False):
        if test:
            test_cases = challenge.sample['test_cases']
        else:
            test_cases = challenge.official['test_cases']
        submission = {
            'source': file_content,
            'lang': self.get_langs()['languages']['codes'][lang],
            'testcases': json.dumps(test_cases),
            'api_key': "hackerrank|128303-15|153420c28478f8f01ee8b86c501ce52a156b4555"
        }
        try:
            response = json.loads(requests.post(API_URL, data=submission, timeout=10.0).text)['result']
        except requests.exceptions.Timeout:
            response = None
        challenge.recalculate_leaderboards()
        return response


print "importing things"
hackerrank = HackerRankSubmitter()