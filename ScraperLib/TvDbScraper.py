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

from pytvdbapi import api
db = api.TVDB('4F36CC91D7116666')

from Scraper import *

class TvDbScraper(Scraper):

    def __init__(self, data):
        Scraper.__init__(self, data)

    def check(self):
        return self.data


# region __Main__

if __name__ == '__main__':

    pass


# endregion

