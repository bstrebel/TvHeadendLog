#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import absolute_import
from __future__ import print_function

import os, sys, logging, logging.config, json, re, urllib, urlparse, requests, pprint
from collections import OrderedDict


class IMDbScraper():

    def __init__(self, data=None):

        import imdb     # IMDbPy package python-imdbpy
                        # cygwin: use default windows installer and move
                        # to .../site-packages (requires also python-lxml)
                        # cygwin: python-setuptools && easy_install-2.7 pip

        self._data = data if data else {}
        self._imdb = imdb.IMDb()

    @property
    def data(self): return self._data

    def search(self, *args, **kwargs):

        self.data.update(**kwargs)

        if 'imdb_tt' in self.data:
            movie = self._imdb.get_movie(self.data['imdb_tt'])
            if movie:
                # load movie attributes
                self._imdb.update(movie)
                self.data['year'] = movie.get('year', 'n/a')
                self.data['kind'] = movie.get('kind', 'unknown')
                if movie['kind'] == 'episode':
                    self.data['show'] = movie.get('episode of').get('title','n/a')
                    self.data['episode'] = movie.get('title', 'n/a')
                    self.data['season'] = movie.get('season',0)
                    self.data['number'] = movie.get('episode',0)
                elif movie['kind'] == 'tv movie':
                    self.data['name'] = movie.get('title','n/a')
                else:
                    #self.data['imdb_data'] = dict(movie.data)
                    pass
                return True
            else:
                print("Invalid imdb_tt [{}]".format(self.data['imdb_tt']))
                return False
        else:
            if 'episode' in self.data:
                result = self._imdb.search_episode(self.data['episode'])
            elif 'query' in self.data:
                result = self._imdb.search_movie(kwargs['query'])

            if result:
                for movie in result:
                    if movie['kind'] == 'episode':
                        # basic movie information
                        self.data['imdb_tt'] = movie.movieID
                        self.data['show'] = movie.get('episode of', 'n/a')
                        self.data['episode'] = movie.get('title', 'n/a')
                        self.data['year'] = movie.get('year', 'n/a')
                        # load movie attributes
                        self._imdb.update(movie)
                        #self.pp(movie.data)
                        #self.data['show'] = movie['episode of']['title']
                        #self.data['episode'] = movie['title']
                        self.data['season'] = movie.get('season',0)
                        self.data['number'] = movie.get('episode',0)
                        return True

        return False

class TvDbScraper():

    def __init__(self, key, data=None):

        from pytvdbapi import api     # pip package
        from fuzzywuzzy import fuzz   # pip package: requires python-levenshtein!

        self._data = data if data else {}
        self._tvdb = api.TVDB(key)
        # Scraper.__init__(self, data)

    @property
    def data(self): return self._data

    @property
    def lang(self): return self.data['lang'] if 'lang' in self.data else 'de'

    def search(self, **kwargs):

        self._data.update(**kwargs)

        if 'tvdb_series' in self.data:

            show = self._tvdb.get_series(self.data['tvdb_series'], self.lang)
            if show:
                self.data['show'] = show.SeriesName

            if 'tvdb_episode' in self.data:
                episode = self._tvdb.get_episode('de', episodeid=self.data['tvdb_episode'])
                if episode:
                    self.data['episode'] = episode.EpisodeName
                    self.data['season'] = episode.SeasonNumber
                    self.data['number'] = episode.EpisodeNumber
                    self.data['season'] = episode.SeasonNumber
                    return True

        else: # query series and episode name

            similar = []
            matches = []

            subtitle = self.data['episode'] if 'episode' in self.data and self.data['episode'] else self.data['subtitle']
            title = self.data['show'] if 'show' in self.data and self.data['show'] else self.data['title']

            # search = "%s %s" % (title, subtitle)
            # result = self._tvdb.search("%s %s" % (title, subtitle), self.lang)
            # pprint(result)
            #
            # result = self._tvdb.search(title, self.lang)
            # pprint(result)
            #
            # result = self._tvdb.search(subtitle, self.lang)
            # pprint(result)
            #
            #
            # if result:
            #     self.data['show'] = show.SeriesName
            #     for season in show:
            #         for episode in season:
            #             if int(episode.seasonid) == int(self.data['tvdb_season']):
            #                 name = episode.EpisodeName
            #                 if fuzz.token_set_ratio(search, name) > 90:
            #                     similar.append(episode)
            #                 if fuzz.token_set_ratio(search, name) == 100:
            #                     matches.append(episode)
            # if len(matches) > 0
            #     if len(matches) == 1:
            #         self.data['show'] = show.SeriesName
            #         self.data['episode'] = matches[0].EpisodeName
            #         self.data['season'] = matches[0].SeasonNumber
            #         self.data['number'] = matches[0].EpisodeNumber
            #         self.data['season'] = matches[0].SeasonNumber
            #         self.data['tvdb_episode'] =  matches[0].id
            #         return True
            #     else:
            #         print "Ambigious episode name [%s] for [%s]. Found multiple results ..." % (search, show.SeriesName)
            #         for episode in similar:
            #             print episode.Name

        return False

class BingAPI():

    def __init__(self, key, data):
        # azure data market account key
        self._key = key
        self._data = data
        if 'scraper' not in self._data: self._data['scraper'] = {}

    def _request_url(self, query, **kwargs):

        if 'site' in kwargs: query = "site:{} {}".format(kwargs['site'], query)

        params = OrderedDict([
            ('Query', "'{}'".format(query)),
            ('$top', 10),
            ('$skip', 0),
            ('$format', 'json')
        ])

        return 'https://api.datamarket.azure.com/Bing/SearchWeb/v1/Web?{}'.format(urllib.urlencode(params))

    def search(self, query, **kwargs):

        postfix = ''
        url = self._request_url(query, **kwargs)
        scraper = {'query': query, 'result': []}
        if 'site' in kwargs:
            scraper['site'] = kwargs['site']
            postfix = " (%s)" % kwargs['site']
        found = 0


        #logging.getLogger('tvlog').setLevel(logging.ERROR)
        #logging.basicConfig(level=logging.ERROR)

        response = requests.get(url, auth=(self._key,self._key))

        if response:
            scraper['response'] = response.status_code
            content = json.loads(response.content)
            if response.status_code == 200:
                results = content['d']['results']
                # print json.dumps(results, indent=4, ensure_ascii=False, encoding='utf-8')
                for entry in results:
                    found += 1
                    result = {'name': entry['Title'],'link': entry['Url']}
                    scraper['result'].append(result)
            else:
                pass
                # print "Request returned with [%s] %s!" % (response.status_code, response.text)
            self._data['scraper'].update({'BingAPI'+postfix: scraper})
        return found

class GoogleCSE(object):

    def __init__(self, cse, key, data):

        self._search_engine_id = cse
        self._api_key = key
        self._data = data
        if 'scraper' not in self._data: self._data['scraper'] = {}

    def _url(self, query, **kwargs):

        params = OrderedDict([
            ('cx', self._search_engine_id),
            ('key', self._api_key),
            ('num', '10'),
            ('googlehost', 'www.google.de'),
            #('siteSearch', site),
            #('gss', '.com'),
            #('rsz', '10'),
            #('oq', query),
            ('q', query.encode('utf-8')),
            ('filter', '0'),  # duplicate content filter, 1 | 0
            ('safe', 'off'),  # strict | moderate | off
        ])

        return 'https://www.googleapis.com/customsearch/v1?{}'.format(
            urllib.urlencode(params))

    def search(self, query, **kwargs):

        url = self._url(query, **kwargs)
        scraper = {'query': query, 'url': url, 'result': []}; found = 0

        response = requests.get(url)

        if response:
            scraper['response'] = response.status_code
            content = json.loads(response.content)
            if response.status_code == 200:
                if 'items' in content:
                    results = content['items']
                    # print json.dumps(results, indent=4, ensure_ascii=False, encoding='utf-8')
                    for entry in results:
                        found += 1
                        result = {'name': entry['title'], 'link': entry['link']}
                        scraper['result'].append(result)
            else:
                pass
                # print "Request returned with [%s] %s!" % (response.status_code, response.text)

            self._data['scraper'].update({'GoogleCSE': scraper})

        return found

class TvScraper:

    def __init__(self, data={}, options={}):

        self._options = options
        self._options.setdefault('google', False)

        self._data = data
        self._data.setdefault('scraper', {})

    @property
    def data(self): return self._data

    @property
    def scraper(self): return self._data.get('scraper', {})

    # @scraper.setter
    # def scraper(self, value): self.data['scraper'] = value

    @property
    def options(self): return self._options

    @property
    def logger(self): return self.options['logger']

    @property
    def google(self): return self.options['google']

    @property
    def isTv(self): return self.data['type'] == 'tv'

    @property
    def google_cse(self): return self.options['google_cse']

    @property
    def google_cse_key(self): return self.options['google_cse']

    @property
    def bing_api_key(self): return self.options['google_cse']

    @property
    def thetvdb_api_key(self): return self.options['google_cse']

    @property
    def query(self): return self._data.get('query', None)

    # @query.setter
    # def query(self, value): self.data['query'] = value

    @property
    def tvQuery(self):

        query = ''
        if self.data.get('show'):
            query = self.data['show']
            if self.data.get('episode'):
                query = query + ' ' + self.data['episode']
        else:
            if self.data.get('title'):
                query = self.data['title']
                if self.data.get('subtitle'):
                    query = query + ' ' + self.data['subtitle']
        return query

    def _scraped(self, key, query):
        return key in self.scraper and self.data.get('query') == query

    '''
    http://www.imdb.com/title/tt1172564/

    http://thetvdb.com/?tab=episode&seriesid=126301&seasonid=510424&id=4625859&lid=14
    http://thetvdb.com/?tab=season&seriesid=126301&seasonid=510424&lid=14
    http://thetvdb.com/?tab=seasonall&id=126301&lid=14
    '''

    def _check_scraper_result(self, scraper, tvdb=True):

        scraper = self.data['scraper'].get(scraper, {'result': []})
        scraper['index'] = -1; scraper['ranking'] = 0; index = 0

        for result in scraper['result']:

            link = result['link']

            if re.search('thetvdb\.com/\?tab=', link):
                match = re.match('.*thetvdb.com/\?tab=episode&seriesid=(\d+)&seasonid=(\d+)&id=(\d+)', link)
                if match:
                    self.data['tvdb_series'] = match.group(1)
                    self.data['tvdb_season'] = match.group(2)
                    self.data['tvdb_episode'] = match.group(3)
                    scraper['index'] = index; scraper['ranking'] = 3
                    if tvdb:
                        return TvDbScraper(self.thetvdb_api_key, self.data).search()
                    return True
                else:
                    match = re.match('.*thetvdb.com/\?tab=season&seriesid=(\d+)&seasonid=(\d+)',link)
                    if match:
                        self.data['tvdb_series'] = match.group(1)
                        self.data['tvdb_season'] = match.group(2)
                        scraper['index'] = index; scraper['ranking'] = 2
                    else:
                        match = re.match('.*thetvdb\.com/\?tab=seasonall&id=(\d+)',link)
                        if match:
                            scraper['index'] = index; scraper['ranking'] = 1
                            self.data['tvdb_series'] = match.group(1)

            elif re.match('.*imdb.com/title', link):
                match = re.match('.*imdb.com/title/tt(\d+)',link)
                if match:
                    self.data['imdb_tt'] = match.group(1)
                    scraper['index'] = index; scraper['ranking'] = 3
                    if tvdb:
                        return IMDbScraper(self.data).search()
                    return True

            index += 1

        return False

    def search(self, **kwargs):

        self.data.update(**kwargs)

        if self.isTv:

            query = self.tvQuery
            search = True

            if 'query' in self.data:

                if self.query == query:
                    search = False
                else:
                    self._data['query'] = query
                    self._data['scraper'] = {}

            for site in ['thetvdb.com', 'imdb.com']:
                key = "BingAPI ({})".format(site); tvdb = False
                if search:
                    BingAPI(self.bing_api_key, self.data).search(query, site=site); tvdb = True
                if self._check_scraper_result(key, tvdb): return self.data

            key = 'BingAPI' ; tvdb = False
            if search:
                BingAPI(self.bing_api_key, self.data).search(query); tvdb = True
            if self._check_scraper_result(key, tvdb): return self.data

            if self.google:
                key = 'GoogleCSE'; tvdb = False
                if search:
                    GoogleCSE(self.google_cse, self.google_cse_key, self.data).search(query); tvdb = True
                if self._check_scraper_result(key, tvdb): return self.data

            # if GoogleHTTP(self.data).search(query):
            #    if self._check_scraper_result('GoogleHTTP'): return self.data

        return self.data

class LogFileHandler(logging.FileHandler):

    def __init__(self, path, mode='a', endcoding='utf-8'):
        path = os.path.expanduser(path)
        logging.FileHandler.__init__(self, path, mode, endcoding)

def main():

    # from six.moves.configparser import ConfigParser
    from ConfigParser import ConfigParser
    from argparse import ArgumentParser

    reload(sys)
    sys.setdefaultencoding('utf-8')

    HOME = os.path.expanduser('~')
    CWD = os.getcwd()

    options = {

        'home':             HOME,
        'config':           None,
        'loglevel':         'INFO',
        'type':             'tv',
        'google_cse':       None,
        'google_cse_key':   None,
        'bing_api_key':     None,
        'thetvdb_api_key':  None,
        'cwd':              CWD
    }

    # command line arguments
    parser = ArgumentParser(description='TVheadend Toolbox Rev. 0.1 (c) Bernd Strebel')
    parser.add_argument('-c', '--config', type=str, help='alternate configuration file')
    parser.add_argument('-b', '--scraper', type=str, help='alternate configuration file')
    parser.add_argument('-q', '--query', type=str, help='episode/movie title')
    parser.add_argument('-g', '--google', action='store_true', help='use google cse')
    parser.add_argument('-v', '--verbose', action='count', help='increasy verbosity')

    parser.add_argument('-t', '--type', type=str,
                        choices=['TV','Tv','tv', 'MOVIE','Movie','movie'],
                        help='search for tv show ore movie')

    parser.add_argument('-l', '--loglevel', type=str,
                        choices=['DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'CRITICAL',
                                 'debug', 'info', 'warn', 'warning', 'error', 'critical'],
                        help='debug log level')

    args = parser.parse_args()
    opts = vars(args)

    # use alternate configuration file
    options['config'] = os.getenv('TVSCRAPER', options['config'])
    if args.config:
        options['config'] = args.config

    if not options['config']:
        script, ext = os.path.splitext(os.path.basename(sys.argv[0]))
        config = script + ".cfg"
        for path in ['./', HOME + '/.', '/etc/' ]:
            if os.path.isfile(path + config):
                options['config'] = path + config
                break

    if options['config'] and os.path.isfile(options['config']):
        logging.config.fileConfig(options['config'])
        config = ConfigParser(options)
        config.read(os.path.expanduser(options['config']))
    else:
        logging.warning("Missing configuration file!")

    pp = pprint.PrettyPrinter(indent=32)
    root = logging.getLogger()
    logger = logging.getLogger('tvscraper')

    # precedence: defaults > config file > environment > command line
    for key in ['google_cse', 'google_cse_key', 'bing_api_key', 'thetvdb_api_key']:
        options[key] = config.get('tvscraper', key)
        options[key] = os.getenv(key.upper(), options[key])
    for key in opts:
        if key in options and opts[key] is not None:
            options[key] = opts[key]
        else:
            options.setdefault(key, opts[key])

    options['type'] = options['type'].lower()
    options['logger'] = logger

    new_level = getattr(logging, options['loglevel'].upper(), None)
    if new_level:
        root.setLevel(new_level)
        logger.setLevel(new_level)

    logger.debug("args: %s" % ' '.join(sys.argv[1:]))
    logger.debug("options:\n" + pp.pformat(options))

    if not options['query']:
        logger.critical("No query specified. Aborting ...")
        exit(1)

    data = {'type': options['type'],
            'query': options['query']}

    result = TvScraper(data, options).search()

    print(json.dumps(result, indent=4, ensure_ascii=False, encoding='utf-8'))

if __name__ == '__main__': main()


'''

def _main():

    data = [
        {
            "title": "Der Darß - Küste der Kraniche",
            "subtitle": ""
        },
        # {
        #     "title": "Terra X",
        #     "subtitle": "Phantome der Tiefsee (2) - Monsterhaie",
        # },
        # {
        #     "title": "Mord mit Aussicht",
        #     "subtitle": "Vatertag",
        # }
    ]

    for entry in data:
        query = "%s %s" % (entry['title'], entry['subtitle'])
        result = TvScraper().search(query=query, type='tv')
        print json.dumps(result, indent=4, ensure_ascii=False, encoding='utf-8')

if __name__ == '__main__':

    reload(sys)
    sys.setdefaultencoding('utf-8')
    main()

        self._config = {

            'imdb' : {
                'class': IMDbScraper,
                'query': "%s %s" % (data['title'], data['subtitle']),
                'site': "site:imdb.com"},
            'tvdb' : {
                'class': TvDbScraper,
                'site': "thetvdb"}
        }

        sites = kwargs['site'] if kwargs.has_key('site') else ['tvdb']
        # keys = kwargs['keys'] if kwargs.has_key('keys') else ['title', 'subtitle']

        for site in sites:
            config = self.config[site]
            if config['class'](self.data).search('tv'):
                return


'''
