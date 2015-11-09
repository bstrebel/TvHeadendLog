#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    filter tv shows and episodes at TheTVDB
"""

__version__ = "0.9"
__author__ = 'bst'

import sys, json, re
from pytvdbapi import api

from Scraper import Scraper

class TvDB(Scraper):

    def __init__(self, data):
        self._lang = 'de'
        self._tvdb = api.TVDB('4F36CC91D7116666')
        Scraper.__init__(self, data)

    @property
    def tvdb(self): return self._tvdb

    @property
    def lang(self): return self._lang

    def check(self):
        update = {}
        result = self.tvdb.search(self.data['title'], self.lang)
        show = result[0]
        for season in show:
            for episode in season:
                if re.match(self.data['subtitle'],episode.EpisodeName):
                    print("Found: {0} - {1}". format(show.SeriesName, episode.EpisodeName))

        return update

# region __Main__

if __name__ == '__main__':

    reload(sys)
    sys.setdefaultencoding('utf-8')

    data = {
        "title": "Terra X",
        "subtitle": "Phantome der Tiefsee - Monsterhaie",
        "filename": "/storage/recordings/Terra X/Terra X - S2013E28 - Phantome der Tiefsee (2) - Monsterhaie.mkv"
    }

    # data = {
    #     "title": "Mord mit Aussicht",
    #     "subtitle": "Vatertag",
    #     "filename": "/storage/recordings/Terra X/Terra X - S2013E28 - Phantome der Tiefsee (2) - Monsterhaie.mkv"
    # }

    update = TvDB(data).check()
    print update

# endregion

