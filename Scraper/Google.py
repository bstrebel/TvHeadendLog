#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    filter tv shows and episodes at TheTVDB
"""

__version__ = "0.9"
__author__ = 'bst'

import sys, json, re
from google import google

from Scraper import *

class Google(Scraper):

    fileName = None
    file = None
    path = None
    name = None
    id = None
    season = None
    episode = None
    thumbnail = None
    inDB = False

    def _cleanupFileName(self, name):
        name = name.lower()
        name = name.replace('.',' ')
        name = name.replace('_',' ')
        name = name.replace('\'',' ')
        name = name.strip()
        if name.endswith('-'):
            name = name[0:len(name)-1]
            name = name.strip()
        return name

    def _cleanupName(self, name):
        if type(name) is unicode:
            name = name.encode('utf8')
        name = name.lower()
        name = name.replace(':','')
        name = name.replace('/','')
        name = name.replace('\'',' ')
        name = name.strip()
        return name

    def __init__(self, data):

        self._lang = 'de'
        self._pages = 5
        Scraper.__init__(self, data)

    @property
    def lang(self): return self._lang

    @property
    def pages(self): return self._pages

    def check(self):

        search = self.data['title'] + " - " + self.data['subtitle']
        #search = self.data['title'] # + " - " + self.data['subtitle']

        #apicall = URL('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q='+search+' site:thetvdb.com').json(True)
        apicall = URL('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q='+search+' site:imdb.com').json(True)
        if apicall:

            data = json.loads(apicall)

            # Try to match the name from the file with the name from the search results
            # After each result, increase the searchresult counter by 1
            # If no exact match is found, assume that the first search result was the correct one
            searchresult = 0
            for serie in data['responseData']['results']:
                pattern = re.compile('(.*?): Series Info - TheTVDB', re.IGNORECASE)
                match = pattern.match(serie['titleNoFormatting'])
                if match:
                    if self._cleanupName(match.group(1)) == self._cleanupName(self.name):
                        break
                searchresult = searchresult+1
            else:
                searchresult = 0

            pattern = re.compile('.*?id%3D(\d+).*', re.IGNORECASE)
            match = pattern.match(data['responseData']['results'][searchresult]['url'])
            if match:
                self.id = match.group(1)

            # if self.id and db.isEnabled() and self.inDB == False:
            #     db.execute('INSERT INTO video (id,type,name) VALUES ('+str(db.escape(self.id))+',\'serie\',\''+db.escape(self.name)+'\')')
		return self.id

        #update = {}
        #result = google.search( "site:thetvdb.com " + self.data['subtitle'], self.pages)
        #return result

# region __Main__

if __name__ == '__main__':

    reload(sys)
    sys.setdefaultencoding('utf-8')

    data = {
        "title": "Mord mit Aussicht",
        "subtitle": "Vatertag",
        "filename": "/storage/recordings/Terra X/Terra X - S2013E28 - Phantome der Tiefsee (2) - Monsterhaie.mkv"
    }

    data = {
        "title": "Terra X",
        "subtitle": "Phantome der Tiefsee (2) - Monsterhaie",
        "filename": "/storage/recordings/Terra X/Terra X - S2013E28 - Phantome der Tiefsee (2) - Monsterhaie.mkv"
    }

    id = Google(data).check()
    print "id=" + id

# endregion

