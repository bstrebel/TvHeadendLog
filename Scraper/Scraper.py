#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    filter tv shows and episodes at TheTVDB
"""

__version__ = "0.9"
__author__ = 'bst'

import sys, json, re

class Scraper:

    # @staticmethod
    # def dbmap(key, data):
    #     return {
    #         #'tvdb': TvDbScraper(data),
    #         'google': Google(data)
    #     }[key]

    def __init__(self, data):
        self._data = data

    @property
    def data(self): return self._data

    def check(self, db):
        update = None
        for key in db:
            update = self.dbmap(key,data).check()
        return update

class URL:
	url = None
	ver = 2

	def __init__(self, url):
		import sys, urllib
		if sys.version_info[0] > 2:
			self.ver = 3
		self.url = urllib.quote_plus(url, ':/?=&')

	def open(self):
		if self.ver == 3:
			import urllib.request
			try:
				return urllib.request.urlopen(self.url)
			except:
				return None
		else:
			import urllib
			try:
				return urllib.urlopen(self.url)
			except:
				return None

	def json(self, asString = False):
		#Console.debug('Retrieving JSON for ' + self.url)
		if self.ver == 3:
			import urllib.request
			try:
				response = urllib.request.urlopen(urllib.request.Request(self.url, None, {'accept': 'application/json'}))
				if asString:
					return response.read().decode('utf-8')
				else:
					return response
			except:
				return None
		else:
			import urllib2
			try:
				response = urllib2.urlopen(urllib2.Request(self.url, None, {'accept': 'application/json'}))
				if asString:
					return response.read()
				else:
					return response
			except:
				return None

	def download(self, location):
		if self.ver == 3:
			import urllib.request
			try:
				if urllib.request.urlretrieve(self.url, location):
					return True
				else:
					return False
			except:
				return False
		else:
			import urllib
			try:
				if urllib.urlretrieve(self.url, location):
					return True
				else:
					return False
			except:
				return False


