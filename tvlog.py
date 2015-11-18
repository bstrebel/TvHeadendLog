#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    filter tv shows and episodes at TheTVDB
"""

__version__ = "0.9"
__author__ = 'bst'

import sys
import os
import json
import codecs
import time
import re
import inspect
import csv
import logging
import logging.config

import pprint

#TODO : class hierarchy refactoring: Entry -> TvHeadend, MediathekView,File

class LogEntry():

    # TvHeadend context set from class Data during initialization
    tvHeadend = None

    @staticmethod
    def attributes():
        attributes = []
        members = inspect.getmembers(LogEntry, lambda m: not(inspect.isroutine(m)))
        for attribute in filter(lambda m: not m[0].startswith('__'), members):
            attributes.append(attribute[0])
        return attributes

    def __init__(self, data):

        self._data = data

        if not self._data.has_key('tvlog'):
            self._data['tvlog'] = { 'type': 'tv'}
            for key in ['uuid', 'show', 'episode', 'season', 'number', 'status', 'flags']:
                if self._data.has_key(key):
                    self._data['tvlog'][key] = self._data[key]
                    del self._data[key]
        if not self._data['tvlog'].has_key('type'): self._data['tvlog']['type'] = 'tv'

    def out(self, fmt):
        return eval(fmt).encode('utf-8')

    def tvdb(self):

        merge = ['title', 'subtitle']
        from tvscraper import TvScraper

        update = dict(self.tvlog)

        for key in merge:
            update[key] = self[key]

        print "\n\n[%s / %s]" % (self['title'], self['subtitle'])

        update = TvScraper(update, self.logger).search()

        print json.dumps(update, indent=4, ensure_ascii=False)

        if update:

            for key in merge:
                self[key] = update[key]
                del update[key]

            for key in update.keys():
                self.tvlog[key] = update[key]

    @property
    def tvHeadend(self): return LogEntry.tvHeadend

    @property
    def logger(self): return self.tvHeadend.logger

    @property
    def raw(self): return self._data

    @property
    def tvlog(self): return self.raw['tvlog']

# region data property definitions

    @property
    def uuid(self): return self['uuid']

    @property
    def log(self): return os.path.join(tvHeadend.tvlog, self.uuid).replace(tvHeadend.cwd + '/', '')

    @property
    def start(self): return time.strftime('%Y-%m-%d %H:%M', time.localtime(self.raw['start']))

    @property
    def stop(self): return time.strftime('%Y-%m-%d %H:%M', time.localtime(self.raw['stop']))

    @property
    def date(self): return time.strftime('%Y-%m-%d', time.localtime(self.raw['start']))

    @property
    def begin(self): return time.strftime('%H:%M', time.localtime(self.raw['start']))

    @property
    def end(self): return time.strftime('%H:%M', time.localtime(self.raw['stop']))

    @property
    def title(self): return self['title']

    @property
    def subtitle(self): return self['subtitle']

    @property   # full pathname
    def filename(self): return self['filename']

    @filename.setter
    def filename(self, value): self['filename'] = value

    @property   # pathname without recordings root
    def file(self): return self.filename.replace(tvHeadend.recordings + '/','') if self.filename else ''

    @property   # filename only without any directory
    def basename(self): return os.path.basename(self.filename) if self.filename else ''

    @property
    def show(self): return self['show']

    @property
    def episode(self): return self['episode']

    @property
    def show(self): return self['season']

    @property
    def show(self): return self['number']

    @property
    def flags(self): return self['flags']

    @property
    def status(self): return self['status']

    @property
    def statusf(self): return "%-8s" % (self.status)


    @property
    def info(self):
        result = 'n/a'
        if self.filename:
            result = self.basename
        else:
            if self.title:
                result = self.title
                if self.subtitle:
                    result = result + ' - ' + self.subtitle
            else:
                if self.subtitle:
                    result = self.subtitle
        return result

# endregion

    def __getitem__(self, key):

        if key == 'filename':

            if key in self.raw.keys():
                return self.raw[key].encode('utf-8')
            else:
                if 'files' in self.raw.keys():
                    if len(self.raw['files']) > 0:
                        if key in self.raw['files'][0].keys():
                            return self.raw['files'][0][key].encode('utf-8')
            return None

        elif key in ['title', 'subtitle', 'description']:

            if key in self.raw.keys():
                if isinstance(self.raw[key], dict):
                    if 'ger' in self.raw[key].keys():
                        return self.raw[key]['ger'].encode('utf-8')
                else:
                    return self.raw[key].encode('utf-8')

            return ''

        elif key == 'status':
            if key not in self.tvlog.keys(): return 'unknown'
            else: return self.tvlog[key]

        elif key == 'duration': return (self.raw['stop'] - self.raw['start']) / 60

        elif key in ['flags', 'season', 'number']:
            if key not in self.tvlog.keys(): return 0
            else: return int(self.tvlog[key])

        elif key == 'date': return time.strftime('%Y-%m-%d', time.localtime(self.raw['start']))

        elif key == 'begin': return time.strftime('%H:%M', time.localtime(self.raw['start']))

        elif key == 'end': return time.strftime('%H:%M', time.localtime(self.raw['stop']))

        else:
            if key in self.tvlog.keys():
                return self.tvlog[key]
            if key in self.raw.keys():
                return self.raw[key]

        return None

    def __setitem__(self, key, value):

        if key == 'filename':

            if key in self.raw.keys():
                self.raw[key] = value
            else:
                if 'files' in self.raw.keys():
                    if len(self.raw['files']) > 0:
                        if key in self.raw['files'][0].keys():
                            self.raw['files'][0][key] = value

        elif key in ['title','subtitle','description']:

            if isinstance(value, dict):
                self.raw[key] = value
            else:
                self.raw[key]['ger'] = value

        else:
            if key in self.raw.keys():
                self.raw[key] = value
            else:
                self.tvlog[key] = value

    # @property
    # def title(self): return self._title
    #
    # @title.setter
    # def title(self, value): self._title = value

class Data:

    def __init__(self, tvHeadend):

        LogEntry.tvHeadend = tvHeadend
        
        self._tvHeadend = tvHeadend
        self._data = {}

    def __getitem__(self, key):
        if key in self._data.keys():
            return LogEntry(self._data[key]);

        return None

    def __setitem__(self, key, value):
        self._data[key] = value

    @property
    def tvHeadend(self): return self._tvHeadend

    @property
    def logger(self): return self.tvHeadend.logger

    @property
    def recordings(self): return self.tvHeadend.recordings

    @property
    def tvlog(self): return self.tvHeadend.tvlog

    @property
    def tvcsv(self): return self.tvHeadend.tvcsv

    @property
    def raw(self): return self._data

    def read(self): pass

    def write(self): pass

    def check_conflicts(self):

        result = {}
        sd = sorted(self._data, key=lambda exp: (self._data[exp]['start']))
        dl = len(sd)
        current = 0
        for entry in sd:
            index = current + 1
            while index < dl:
                if self._data[sd[index]]['start'] < self._data[entry]['stop']:
                    if entry not in result.keys(): result[entry] = []
                    result[entry].append(sd[index])
                index += 1
            current += 1

        return result

    def filter(self):

        return sorted(filter(eval(self.tvHeadend.filter), self._data), key=lambda exp: (self._data[exp]['start']))

class LogData(Data):

    def __init__(self, tvHeadend):
        Data.__init__(self, tvHeadend)

    def read(self):
        os.chdir(self.tvlog)
        for file in os.listdir('.'):
            if os.path.isdir(file): continue
            uuid = file
            with codecs.open(self.tvlog + '/' + file, mode='r', encoding='utf-8') as log:
                self._data[uuid] = json.load(log, encoding='utf-8')
                log.close()
                self._data[uuid]['uuid'] = uuid

    def write(self):

        os.chdir(self.tvlog)
        for uuid in self.raw.keys():
            entry = self.merge(uuid)
            # print json.dumps(entry.raw, indent=4, ensure_ascii=False, encoding='utf-8')
            with codecs.open(uuid, mode='w', encoding='utf-8') as new:
                json.dump(entry.raw, new, indent=4, ensure_ascii=False, encoding='utf-8')
                new.close()

    def merge(self, uuid):

        with codecs.open(self.tvlog + '/' + uuid, mode='r', encoding='utf-8') as log:
            merge = LogEntry(json.load(log, encoding='utf-8'))
            log.close()
            for key in self.raw[uuid].keys():
                merge[key] = self.raw[uuid][key]
        return merge

class CsvData(Data):

    _csvheader = ["start", "stop", "uuid", "date", "begin", "end", "duration", "flags",
                  "status", "channelname", "comment", "title", "subtitle", "show", "episode",
                  "season", "number", "filename", "description"]

    @staticmethod
    def header():
        return "|".join(CsvData._csvheader)

    def __init__(self, tvHeadend):

        Data.__init__(self, tvHeadend)

    def read(self):

        csv.register_dialect('tvlog', delimiter='|', quoting=csv.QUOTE_NONE)
        csvfile = os.path.join(self.tvcsv)
        with codecs.open(csvfile, mode='r', encoding='utf-8') as fh:
            reader = csv.DictReader(fh, dialect='tvlog')
            for entry in reader:
                uuid = entry['uuid']
                del entry['uuid']
                for key in ['start', 'stop', 'duration', 'flags', 'season', 'number']:
                    entry[key] = int(entry[key])
                self._data[uuid] = entry

class TvHeadend():

    def __init__(self, options):

        self._data = None
        self._options = options

        # transformed eval strings
        self._source = None
        self._filter = None
        self._format = None

        # formatted ouput strings
        self._theSource = None
        self._theFilter = None
        self._theFormat = None

#region property definitions

    @property
    def data(self): return self._data

    @data.setter
    def data(self, value): self._data = value

    @property
    def options(self): return self._options

    @property
    def logger(self): return self.options.get('logger')

    @property
    def cwd(self): return self.options.get('cwd')

    @property
    def root(self): return self.options.get('tvheadend')

    @property
    def tvheadend(self): return self.options.get('tvheadend')

    @property
    def recordings(self): return self.options.get('recordings')

    @property
    def tvlog(self): return self.options.get('tvlog')

    @property
    def tvcsv(self): return self.options.get('tvcsv')

    @property
    def out(self): return self.options.get('out')

    @property
    def check(self): return self.options.get('check')

    @property
    def update(self): return self.options.get('update')

    @property
    def format(self): return self._format

    @property
    def filter(self): return self._filter

    @property
    def source(self): return self._source

    @property
    def theSource(self): return self._theSource

    @property
    def theFilter(self): return self._theFilter

    @property
    def theFormat(self): return self._theFormat

#endregion

    def run(self):

        self._source = self.options['source'].strip('"\'')
        self._format = self.parse_output_format()
        self._filter = self.parse_output_filter()

        if self.source == 'tvlog':
            self._theSource = self.tvlog
            self._data = LogData(self)
        elif self.source == 'tvcsv':
            self._theSource = self.tvcsv
            self._data = CsvData(self)
        else:
            #TODO: process other source options
            return

        self._data.read()

        if self.check:
            if self.check in ['conflicts', 'upcoming']:
                self.check_conflicts()
                return
            elif self.check == 'tvdb':
                self.check_tvdb()

        if self.update:
            self._data.write()

        self.list_data()

    def parse_output_filter(self):

        filter = self.options['filter']
        if filter.strip('"\'') == 'None':
            self._theFilter = "None"
            filter = 'True'
        elif filter.strip('"\'') == 'True':
            self._theFilter = "None"
        else:
            for property in LogEntry.attributes():
                filter = filter.replace('{' + property + '}', "LogEntry(self._data[exp])['" + property + "']")
                filter = re.sub('(\.' + property + '\W)', r'LogEntry(self._data[exp])\1', filter)

            self._theFilter = filter

        return "lambda exp, self=self: " + filter

    def parse_output_format(self):

        fmt = self.options['out']
        if fmt.strip('"\'') == 'csv':
            self._theFormat = "CSV"
            fmt = '"%d|%d|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s|%s|%d|%d|%s|%s" % (' \
                  'self["start"], self["stop"], self["uuid"], self["date"], self["begin"], self["end"], self["duration"], self["flags"], ' \
                  'self["status"], self["channelname"], self["comment"], self["title"], self["subtitle"], self["show"], self["episode"], ' \
                  'self["season"], self["number"], self["filename"], self["description"])'
        elif fmt.strip('"\'') == 'json':
            self._theFormat = "JSON"
            fmt = 'json.dumps(self._data, indent=4, ensure_ascii=False, encoding=\'utf-8\')'
        else:
            if '{' in fmt or '.' in fmt:
                for property in LogEntry.attributes():
                    fmt = fmt.replace('{' + property + '}', "self['" + property + "']")
                    fmt = fmt.replace('.' + property, "self." + property)
            else:
                match = re.search('\W+', fmt)
                if match:
                    dlm = match.group(0)
                    exp = "'" + dlm + "'.join(["
                    for k in fmt.split(dlm):
                        exp = exp + 'self.' + k + ','
                    fmt = exp.rstrip(',') + "])"
                else:
                    fmt = 'self.' + fmt

            self._theFormat = fmt

        return fmt

    def check_conflicts(self):

        sys.stderr.write("\nChecking for conflicting entries ...\n\n")

        # self.data.read()
        result = self.data.check_conflicts()
        if result:
            counter = 0
            for k in result:
                counter +=1
                print self.data[k].out(self.format)
                for v in result[k]:
                    print self.data[v].out(self.format)
                if counter < len(result): print '--'
            print
            return 1
        else:
            sys.stderr.write("... done!\n")
            return 0

    def list_data(self, reload=False):

        sys.stderr.write("\nSource:\t{0}\nFilter:\t{1}\nFormat:\t{2}\n\n". format(self.theSource, self.theFilter, self.theFormat))

        if self.theFormat == 'CSV' and not self._args.noheader:
            print CsvData.header()

        if reload: self.data.read()

        counter = {}
        out = []
        for k in self.data.filter():

            if self.data[k].status not in counter.keys():
                counter[self.data[k].status] = 1
            else:
                counter[self.data[k].status] += 1

            if self.theFormat == 'JSON':
                # print self.data.merge(k).out(self.format)
                out.append(self.data[k].raw)
            else:
                print self.data[k].out(self.format)

        if self.theFormat == 'JSON':
            print json.dumps(out, indent=4, ensure_ascii=False, encoding='utf-8')

        sys.stderr.write("\nStatistcs: ")
        for k in counter.keys():
            sys.stderr.write("{0}={1} ".format(k, counter[k]))
        sys.stderr.write("\n\n")

    def check_tvdb(self):

        # self.data.read()
        for k in self.data.filter():
            self.data[k].tvdb()

class LogFileHandler(logging.FileHandler):
    def __init__(self, path, mode='a', endcoding='utf-8'):
        path = os.path.expanduser(path)
        logging.FileHandler.__init__(self, path, mode, endcoding)

def main():

    from ConfigParser import ConfigParser
    from argparse import ArgumentParser

    reload(sys)
    sys.setdefaultencoding('utf-8')

    HOME = os.path.expanduser('~')

    options = {

        'home':         HOME,
        'tvheadend':    HOME + '/.hts/tvheadend',
        'config':       HOME + '/.tvlog.cfg',
        'recordings':   '/storage/recordings',
        'loglevel':     'INFO',
        'out':          '"%s %s %-8s %s" % (.date, .begin, .status, .info)',
        'filter':       'True',
        'source':       'tvlog',
        'cwd': os.getcwd()
    }

    # command line arguments
    parser = ArgumentParser(description='TVheadend Toolbox Rev. 0.1 (c) Bernd Strebel')
    parser.add_argument('-c', '--config', type=str, help='alternate configuration file')
    parser.add_argument('-v', '--verbose', action='count', help='increasy verbosity')
    parser.add_argument('-r', '--recordings', type=str, help='recording directory')
    parser.add_argument('-t', '--tvheadend', type=str, help='tvheadend log directory')
    parser.add_argument('-s', '--source', type=str, help='data source')
    parser.add_argument('-f', '--filter', type=str, help='filter expression')
    parser.add_argument('-o', '--out', type=str, help='output expression')
    parser.add_argument('-u', '--update', action='store_true', help='update tvlog files')
    parser.add_argument('-n', '--noheader', action='store_true', help='suppress header for csv output')

    #parser.add_argument('-i', '--init', action='store_true', help='check recording conflicts')
    #parser.add_argument('-c', '--csv', action='store_true', help='check recording conflicts')
    #parser.add_argument('-c', '--check', action='store_true', help='check recording conflicts')
    #parser.add_argument('-d', '--checkdb', action='store_true', help='check movie databases')
    #parser.add_argument('--log', type=str, help='alternate logging configuration file')

    parser.add_argument('--check', type=str, choices=['conflicts','tvdb','upcoming'],
                        help='perform checks on recording entries')

    parser.add_argument('-l', '--loglevel', type=str,
                        choices=['DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'CRITICAL',
                                 'debug', 'info', 'warn', 'warning', 'error', 'critical'],
                        help='debug log level')

    args = parser.parse_args()
    opts = vars(args)

    # use alternate configuration file
    options['config'] = os.getenv('TVLOG', options['config'])
    if args.config: options['config'] = args.config

    logging.config.fileConfig(options['config'])
    logger = logging.getLogger('tvlog')

    logger.debug("tvlog started with args: %s" % ' '.join(sys.argv[1:]))

    config = ConfigParser(options)
    config.read(os.path.expanduser(options['config']))

    # precedence: defaults > config file > environment > command line
    for key in ['recordings', 'tvheadend']:
        options[key] = config.get('tvlog', key)
        options[key] = os.getenv(key.upper(), options[key])

    for key in opts.keys():
        if options.has_key(key) and opts[key] is not None:
            options[key] = opts[key]
        else:
            options.setdefault(key, opts[key])

    options['tvheadend'] = os.path.expanduser(options['tvheadend'])
    options['tvlog'] = options['tvheadend'] + '/dvr/log'
    options['tvcsv'] = options['tvheadend'] + '/dvr/log.csv'

    options['logger'] = logger

    new_level = getattr(logging, options['loglevel'].upper(), None)
    if new_level:
        logger.setLevel(new_level)

    TvHeadend(options).run()

# region __Main__

if __name__ == '__main__':

    tvHeadend = None
    main()
    exit(0)

# endregion

'''

    #for key in self.attributes():
    #    if self.raw.has_key(key):
    #        update[key] = self[key]


    def write(self):
        for uuid in self._data:
            with codecs.open(uuid + '.new', mode='w', encoding='utf-8') as new:
                json.dump(self._data[uuid], new, indent=4, ensure_ascii=False, encoding='utf-8')

        reader = csv.reader(fh, dialect='tvlog')
        for line in reader:
            for attribute in line:
                print attribute.encode('utf-8'),
            print
    # try:
    #     os.chdir(_recordings)
    # except os.error:
    #     sys.stderr.write("Invalid recordings directory [{0}]. Aborting ...".out(_recordings))
    #     exit(1)

    # try:
    #     os.chdir(_tvheadend)
    # except os.error:
    #     sys.stderr.write("Invalid tvheadend directory [{0}]. Aborting ...".out(_tvheadend))
    #     exit(1)

#    if not args.filter:
#        args.filter = 'True'
         #self._start = data['start']
        #self._stop = data['stop']
        #self._uuid = data['uuid']

        #self._date = time.strftime('%Y-%m-%d', time.localtime(data['start']))
        #self._begin = time.strftime('%H:%M', time.localtime(data['start']))
        #self._end = time.strftime('%H:%M', time.localtime(data['stop']))
        #self._duration = (data['stop'] - data['start'])/60

        #self._flags = 0 if 'flags' not in data.keys() else data['flags']
        #self._status = 'unknown' if 'status' not in data.keys() else data['status']

        #self._title = data['title']['ger']
        #self._subtitle = data['subtitle']['ger']

        x = logData['1b364c7def98cded0e34ed25bf3061b7']['description']
        logData['1b364c7def98cded0e34ed25bf3061b7']['filename'] = "new filename"
        y = logData['1b364c7def98cded0e34ed25bf3061b7']['filename']
        print(y)
                    # print(LogEntry(self._data[entry]).short())
                    # print(LogEntry(self._data[sd[index]]).short())
                    # print("")
        #result = filter(lambda exp, self=self: self._data[exp]['status'] == "new", self._data)
        # expr = "{status} in ['new', 'finished']"


        new = '"%s %s %s" % (self.date, self.statusf, self.info)'
        return {
            'short': "%s %s-%s %s %s" % (self.date, self.begin, self.end, self.statusf, self.info),
            'new': eval(new)
        }[key].encode('utf-8')

        def short(self): return self.out('new')

        #filter = args.filter
        #filter = "lambda exp, self=self: " + filter.replace("{", "LogEntry(self._data[exp])['").replace("}","']")
        #filter = re.sub('(\.[^_]\w+)(?=\.)', r'LogEntry(self._data[exp])\1', filter)

        #filter = filter.replace("{", "LogEntry(self._data[exp])['").replace("}","']")
        #filter = re.sub('\^(\w+)', r'LogEntry(self._data[exp]).\1', filter)

        #result = filter(lambda exp, self=self: LogEntry(self._data[exp]).status == 'new', self._data)
        #return result

'''
