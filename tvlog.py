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
import argparse
import inspect
import csv

from Scraper import Scraper


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

    def out(self, fmt):
        return eval(fmt).encode('utf-8')

    def tvdb(self):

        update = Scraper(self.raw).checkdb('tvdb')

        if update:
            for key in update.keys():
                self[key] = update[key]

    @property
    def tvHeadend(self): return LogEntry.tvHeadend

    @property
    def raw(self): return self._data

# region data property definitions

    @property
    def uuid(self): return self['uuid']

    @property
    def log(self): return os.path.join(tvHeadend.tvlog, self.uuid).replace(tvHeadend.cwd + '/', '')

    @property
    def start(self): return time.strftime('%Y-%m-%d %H:%M', time.localtime(self._data['start']))

    @property
    def stop(self): return time.strftime('%Y-%m-%d %H:%M', time.localtime(self._data['stop']))

    @property
    def date(self): return time.strftime('%Y-%m-%d', time.localtime(self._data['start']))

    @property
    def begin(self): return time.strftime('%H:%M', time.localtime(self._data['start']))

    @property
    def end(self): return time.strftime('%H:%M', time.localtime(self._data['stop']))

    @property
    def flags(self): return 0 if 'flags' not in self._data.keys() else self._data['flags']

    @property
    def status(self): return 'unknown' if 'status' not in self._data.keys() else self._data['status']

    @property
    def statusf(self): return "%-8s" % (self.status)

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

            if key in self._data.keys():
                return self._data[key].encode('utf-8')
            else:
                if 'files' in self._data.keys():
                    if len(self._data['files']) > 0:
                        if key in self._data['files'][0].keys():
                            return self._data['files'][0][key].encode('utf-8')
            return None

        elif key in ['title','subtitle','description']:

            if key in self._data.keys():
                if isinstance(self._data[key], dict):
                    if 'ger' in self._data[key].keys():
                        return self._data[key]['ger'].encode('utf-8')
                else:
                    return self._data[key].encode('utf-8')

            return ''

        elif key == 'status':
            if key not in self._data.keys(): return 'unknown'

        elif key == 'duration': return (self._data['stop'] - self._data['start']) / 60

        elif key in ['flags', 'season', 'number']:
            if key not in self._data.keys(): return 0
            else: return int(self._data[key])

        elif key == 'date': return time.strftime('%Y-%m-%d', time.localtime(self._data['start']))

        elif key == 'begin': return time.strftime('%H:%M', time.localtime(self._data['start']))

        elif key == 'end': return time.strftime('%H:%M', time.localtime(self._data['stop']))

        else:
            if key not in self._data.keys():
                return None

        return self._data[key]

    def __setitem__(self, key, value):

        if key == 'filename':

            if key in self._data.keys():
                self._data[key] = value
            else:
                if 'files' in self._data.keys():
                    if len(self._data['files']) > 0:
                        if key in self._data['files'][0].keys():
                            self._data['files'][0][key] = value

        elif key in ['title','subtitle','description']:

            if isinstance(value, dict):
                self._data[key] = value
            else:
                self._data[key]['ger'] = value

        else:
            self._data[key] = value

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
                self._data[uuid]['uuid'] = uuid

    def write(self):

        os.chdir(self.tvlog)
        for uuid in self.raw.keys():
            entry = self.merge(uuid)
            # print json.dumps(entry.raw, indent=4, ensure_ascii=False, encoding='utf-8')
            with codecs.open(uuid, mode='w', encoding='utf-8') as new:
                json.dump(entry.raw, new, indent=4, ensure_ascii=False, encoding='utf-8')

    def merge(self, uuid):

        with codecs.open(self.tvlog + '/' + uuid, mode='r', encoding='utf-8') as log:
            merge = LogEntry(json.load(log, encoding='utf-8'))
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

    def __init__(self, options, args):

        self._tvheadend = options['tvheadend']
        self._recordings = options['recordings']
        self._tvlog = options['tvheadend'] + '/dvr/log'
        self._tvcsv = options['tvheadend'] + '/dvr/log.csv'
        self._args = args
        self._cwd = os.getcwd()
        if not self._args.out: self._args.out = '"%s %s %-8s %s" % (.date, .begin, .status, .info)'
        if not self._args.filter: self._args.filter = "True"
        if not self._args.source: self._args.source = 'tvlog'
        self._source = None
        self._theSource = None
        self._format = None
        self._theFormat = None
        self._filter = None
        self._data = None

#region property definitions

    @property
    def cwd(self): return self._cwd

    @property
    def root(self): return self._tvheadend

    @property
    def recordings(self): return self._recordings

    @property
    def tvlog(self): return self._tvlog

    @property
    def tvcsv(self): return self._tvcsv

    @property
    def format(self): return self._format

    @property
    def filter(self): return self._filter

    @property
    def source(self): return self._source

    @property
    def data(self): return self._data

    @data.setter
    def data(self, value): self._data = value

    @property
    def theSource(self): return self._theSource

    @property
    def theFilter(self): return self._theFilter

    @property
    def theFormat(self): return self._theFormat

#endregion

    def run(self):

        self._source = self._args.source.strip('"\'')
        self._format = self.parse_output_format()
        self._filter = self.parse_output_filter()

        if self.source == 'tvlog':
            self._theSource = self.tvlog
            self._data = LogData(self)
        elif self.source == 'tvcsv':
            self._theSource = self.tvcsv
            self._data = CsvData(self)
        else:
            return

        if self._args.check == "conflicts":
            self.check_conflicts()
        elif self._args.check == "tvdb":
            self.check_tvdb()
        else:
            self.list_data()


    def parse_output_filter(self):

        filter = self._args.filter
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

        fmt = self._args.out
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

        self.data.read()
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

    def list_data(self):

        sys.stderr.write("\nSource:\t{0}\nFilter:\t{1}\nFormat:\t{2}\n\n". format(self.theSource, self.theFilter, self.theFormat))

        if self.theFormat == 'CSV' and not self._args.noheader:
            print CsvData.header()

        self.data.read()

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

        self.data.read()
        for k in self.data.filter():
            self.data[k].tvdb()

def main():

    reload(sys)
    sys.setdefaultencoding('utf-8')

    options = {

        'home': os.path.expanduser('~'),
        'tvheadend': os.path.expanduser('~') + '/.hts/tvheadend',
        'recordings': os.readlink(os.path.expanduser('~') + '/.hts/tvheadend' + '/.recordings'),
        'cwd': os.getcwd()
    }

    # command line arguments
    parser = argparse.ArgumentParser(description='TVheadend Toolbox Rev. 0.1 (c) Bernd Strebel')
    parser.add_argument('-v', '--verbose', action='count', help='increasy verbosity')
    parser.add_argument('-r', '--recordings', type=str, help='recording directory')
    parser.add_argument('-t', '--tvheadend', type=str, help='tvheadend log directory')
    parser.add_argument('-s', '--source', type=str, help='data source')
    parser.add_argument('-f', '--filter', type=str, help='filter expression')
    parser.add_argument('-o', '--out', type=str, help='output expression')
    parser.add_argument('-n', '--noheader', action='store_true', help='suppress header for csv output')
    #parser.add_argument('-i', '--init', action='store_true', help='check recording conflicts')
    #parser.add_argument('-c', '--csv', action='store_true', help='check recording conflicts')
    #parser.add_argument('-c', '--check', action='store_true', help='check recording conflicts')
    parser.add_argument('-d', '--checkdb', action='store_true', help='check movie databases')

    parser.add_argument('-c', '--check', type=str, choices=['conflicts'],
                        help='perform checks on recording entries')

    parser.add_argument('--log', type=str, help='alternate logging configuration file')
    parser.add_argument('-l', '--loglevel', type=str,
                        choices=['DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'CRITICAL',
                                 'debug', 'info', 'warn', 'warning', 'error', 'critical'],
                        help='debug log level')

    args = parser.parse_args()

    options['recordings'] = os.getenv('RECORDINGS', options['recordings'])
    if args.recordings:
        options['recordings'] = args.recordings

    options['tvheadend'] = os.getenv('TVHEADEND', options['tvheadend'])
    if args.tvheadend:
        options['tvheadend'] = args.tvheadend

    TvHeadend(options, args).run()

# region __Main__

if __name__ == '__main__':

    tvHeadend = None
    main()
    
# endregion

'''
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
