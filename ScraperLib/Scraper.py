#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    filter tv shows and episodes at TheTVDB
"""

__version__ = "0.9"
__author__ = 'bst'

import sys, platform, os, json, codecs, time, re
import argparse
import inspect
import csv

from TvDbScraper import TvDbScraper

class Scraper:

    dbmap = {

        "tvdb": TvDbScraper
    }


    def __init__(self, data):
        self._data = data

    @property
    def data(self): return self._data

    def check(self, db):
        update = None
        for key in db:
            if key in Scraper.dbmap.keys():
                update = Scraper.dbmap[key](data).check()

        return update

# region __Main__

if __name__ == '__main__':

    data = {
        "title": "Terra X",
        "subtitle": "Phantome der Tiefsee (2) - Monsterhaie",
        "filename": "/storage/recordings/Terra X/Terra X - S2013E28 - Phantome der Tiefsee (2) - Monsterhaie.mkv"
    }

    update = Scraper(data).check(['tvdb'])
    print update


# endregion

