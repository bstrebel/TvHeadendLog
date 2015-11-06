#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    search tv shows and episodes at TheTVDB
"""

__version__ = "0.9"
__author__ = 'bst'

import sys, platform, os, json, codecs, time
import argparse


#from pytvdbapi import api
#db = api.TVDB('4F36CC91D7116666')

class LogEntry():

    global tvHeadend

    def format(self, key):
        return {
            'short': "%s %s-%s %s %s" % (self.date, self.begin, self.end, self.status, self.info)
        }[key].encode('utf-8')

    def short(self): return self.format('short')

    def __init__(self, data):

        self._data = data


# region Property definitions

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
    def status(self):
        value = 'unknown' if 'status' not in self._data.keys() else self._data['status']
        return "%-8s" % (value)

    @property
    def title(self): return self['title']

    @property
    def subtitle(self): return self['subtitle']

    @property
    def filename(self): return self['filename']

    @filename.setter
    def filename(self, value): self['filename'] = value

    @property
    def basename(self): return os.path.basename(self.filename) if self.filename else ''

    @property
    def file(self): return self.filename.replace(tvHeadend.recordings + '/','') if self.filename else ''

    @property
    def info(self): return  self.basename if self.filename else self.title + ' - ' + self.subtitle

# endregion

    def raw(self):
        return self._data

    def __getitem__(self, key):

        if key == 'filename':

            if key in self._data.keys():
                return self._data[key]
            else:
                if 'files' in self._data.keys():
                    if len(self._data['files']) > 0:
                        if key in self._data['files'][0].keys():
                            return self._data['files'][0][key]
            return None

        elif key in ['title','subtitle','description']:

            if key in self._data.keys():
                if 'ger' in self._data[key].keys():
                    return self._data[key]['ger']
            return None

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

            if key in self._data.keys():
                if 'ger' in self._data[key].keys():
                    self._data[key]['ger'] = value

        else:
            self._data[key] = value

    # @property
    # def title(self): return self._title
    #
    # @title.setter
    # def title(self, value): self._title = value


class LogData():

    global tvHeadend

    def read(self):
        os.chdir(self._tvlog)
        for file in os.listdir('.'):
            if os.path.isdir(file): continue
            uuid = file
            with codecs.open(self._tvlog + '/' + file, mode='r', encoding='utf8') as log:
                self._data[uuid] = json.load(log, encoding='utf-8')
                self._data[uuid]['uuid'] = uuid

    def write(self):
        for uuid in self._data:
            with codecs.open(uuid + '.new', mode='w', encoding='utf-8') as new:
                json.dump(self._data[uuid], new, indent=4, ensure_ascii=False, encoding='utf-8')

    def upcoming(self):

        result = {}
        sd = sorted(self._data, key=lambda exp: (self._data[exp]['start']))
        dl = len(sd)
        current = 0
        for entry in sd:
            index = current + 1
            while ( index < dl ):
                if (self._data[sd[index]]['start'] < self._data[entry]['stop']):
                    if entry not in result.keys(): result[entry] = []
                    result[entry].append(sd[index])
                index += 1
            current += 1

        return result

    def search(self, expr):

        search = "lambda exp, self=self: " + expr.replace("{", "self._data[exp]['").replace("}","']")
        return filter(eval(search), self._data)

    def __init__(self):

        self._tvlog = tvHeadend.tvlog
        self._recordings = tvHeadend.recordings
        self._data = {}

    def __getitem__(self, key):

        if key in self._data.keys():
            return LogEntry(self._data[key]);

        return None

    def __setitem__(self, key, value):

        self._data[key] = value

    @property
    def raw(self): return self._data


class TvHeadend():

    def __init__(self, tvheadend, recordings):

        self._tvheadend = tvheadend
        self._recordings = recordings
        self._tvlog = tvheadend + '/dvr/log'

    @property
    def root(self): return self._tvheadend

    @property
    def recordings(self): return self._recordings

    @property
    def tvlog(self): return self._tvlog

    def upcoming(self, args):

        sys.stderr.write("\nChecking for conflicting entries ...\n\n")
        logData = LogData()
        logData.read()
        result = logData.upcoming()
        if result:
            counter = 0
            for k in result:
                counter +=1
                print logData[k].short()
                for v in result[k]:
                    print logData[v].short()
                if counter < len(result): print '--'
            print
            return 1
        else:
            sys.stderr.write("... done!\n")
            return 0

    def search(self, args):

        #sys.stderr.write("Filter: {0}\n".format(expr.replace("{","data['").replace("}","']")))
        logData = LogData()
        logData.read()
        for k in logData.search(args.search):
            print logData[k].short()

    def run(self, args):
        if args.upcoming: self.upcoming(args)
        if args.search: self.search(args)

def main():

    global tvHeadend
    header = ['start','stop','uuid','date','begin','end','duration','flags','status','channel','comment','title']

    _home = os.path.expanduser('~')
    _tvheadend = _home + '/.hts/tvheadend'
    _recordings = os.readlink(_tvheadend + '/.recordings')

    # command line arguments
    parser = argparse.ArgumentParser(description='TVheadend Toolbox Rev. 0.1 (c) Bernd Strebel')
    parser.add_argument('-v', '--verbose', action='count', help='increasy verbosity')
    parser.add_argument('-r', '--recordings', type=str, help='recording directory')
    parser.add_argument('-t', '--tvheadend', type=str, help='tvheadend log directory')
    parser.add_argument('-s', '--search', type=str, help='filter expression')
    parser.add_argument('-i', '--init', action='store_true', help='check recording conflicts')
    parser.add_argument('-c', '--csv', action='store_true', help='check recording conflicts')
    parser.add_argument('-u', '--upcoming', action='store_true', help='check recording conflicts')
    parser.add_argument('-d', '--checkdb', action='store_true', help='check movie databases')
    parser.add_argument('--log', type=str, help='alternate logging configuration file')
    parser.add_argument('-l', '--loglevel', type=str,
                        choices=['DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'CRITICAL',
                                 'debug', 'info', 'warn', 'warning', 'error', 'critical'],
                        help='debug log level')

    args = parser.parse_args()

    _recordings = os.getenv('RECORDINGS', _recordings)
    if args.recordings:
        _recordings = args.recordings

    try:
        os.chdir(_recordings)
    except os.error:
        sys.stderr.write("Invalid recordings directory [{0}]. Aborting ...".format(_recordings))
        exit(1)

    _tvheadend = os.getenv('TVHEADEND', _tvheadend)
    if args.tvheadend:
        _recordings = args.tvheadend

    try:
        os.chdir(_tvheadend)
    except os.error:
        sys.stderr.write("Invalid tvheadend directory [{0}]. Aborting ...".format(_tvheadend))
        exit(1)

    tvHeadend = TvHeadend(_tvheadend, _recordings)
    tvHeadend.run(args)

# region __Main__
if __name__ == '__main__':

    tvHeadend = None
    main()
# endregion

'''
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

'''
