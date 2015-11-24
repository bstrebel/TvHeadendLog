#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    filter tv shows and episodes at TheTVDB
"""

from __future__ import absolute_import
from __future__ import print_function

__version__ = "1.0"
__author__ = 'b.strebel@ebs-foto.de'

import sys, os, json, codecs, time, re, inspect, csv, logging, logging.config, pprint
# from six.moves import filter

#TODO : class hierarchy refactoring: Entry -> TvHeadend, MediathekView,File

class LogEntry():

    # TvHeadend context set from class Data during initialization
    tvHeadend = None

    @staticmethod
    def attributes():
        attributes = []
        members = inspect.getmembers(LogEntry, lambda m: not(inspect.isroutine(m)))
        for attribute in [m for m in members if not m[0].startswith('__')]:
            attributes.append(attribute[0])
        return attributes

    def __init__(self, data):

        self._data = data

        # if 'tvlog' not in self._data:
        #     # create from csv entry
        #     self._data['tvlog'] = { 'type': 'tv'}
        #     # move extended attributes to tvlog {}
        #     for key in ['uuid', 'show', 'episode', 'season', 'number', 'status', 'flags']:
        #         if key in self._data:
        #             self._data['tvlog'][key] = self._data[key]
        #             del self._data[key]
        #     # remove virtual attributes
        #     for key in ['date', 'begin', 'end', 'duration']:
        #         if key in self._data: del self._data[key]
        #
        #     filename = self._data['filename']
        #     del self._data['filename']
        #     self['filename'] = filename
        #
        # if 'type' not in self._data['tvlog']: self._data['tvlog']['type'] = 'tv'

    def out(self, fmt):
        return eval(fmt).encode('utf-8')

    def _status(self, update=True):

        # recording status: upcoming    start > now
        #                   recording   start < now && stop > now
        #                   new         stop  < now && file exists
        #                   failed      stop  < now && file missing
        #                   finished    stop  < now && checked against tvdb

        ### self._data.setdefault('tvlog', {})
        ### self._data['tvlog'].setdefault('status', 'unknown')
        ### status = self._data['tvlog']['status']

        #if status in ['new', 'failed', 'finished'] and not update:
        #    return status

        start = self['start']; stop = self['stop']; now = int(time.time())

        if stop < now:
            if self['filename']:
                if os.path.isfile(self['filename']):
                    if self.checked:
                        return 'finished'
                    else:
                        return 'new'
                else:
                    return 'missing'
            else:
                # self.tvHeadend.ppLog(self._data)
                return 'failed'
        else:
            if start > now:
                return 'upcoming'
            else:
                return 'recording'

        return 'unknown'


    def tvdb(self):

        merge = ['title', 'subtitle', 'comment']
        from tvscraper import TvScraper

        update = dict(self.tvlog)
        update.setdefault('type','tv')

        options = {'google': self.tvHeadend.google,
                   'logger': self.logger}

        for key in merge:
            update[key] = self[key]

        self.logger.info("{} / {}".format(self['title'], self['subtitle']))

        update = TvScraper(update, options).search()

        self.logger.debug(json.dumps(update, indent=4, ensure_ascii=False))

        if update:

            for key in merge:
                self[key] = update[key]
                del update[key]

            self.raw.setdefault('tvlog', update)
            for key in update:
                self.tvlog[key] = update[key]

    @property
    def tvHeadend(self): return LogEntry.tvHeadend

    @property
    def ppLog(self, obj): return LogEntry.tvHeadend.ppLog(obj)

    @property
    def logger(self): return self.tvHeadend.logger

    @property
    def google(self): return self.tvHeadend.google

    @property
    def mirror(self): return self.tvHeadend.mirror

    @property
    def recordings(self): return self.tvHeadend.recordings


    @property
    def raw(self): return self._data

    @property
    def tvlog(self): return self['tvlog']

    @property
    def type(self): return self['type']

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
    def now(self): return time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time()))

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
    def season(self): return self['season']

    @property
    def number(self): return self['number']

    @property
    def flags(self): return self['flags']

    @property
    def status(self): return self['status']

    @property
    def statusf(self): return "{:8}".format(self.status)

    @property
    def checked(self): return self['number'] > 0

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

            if key in self.raw:
                return re.sub(self.recordings, self.mirror, self.raw[key].encode('utf-8'))
            else:
                if 'files' in self.raw:
                    if len(self.raw['files']) > 0:
                        if key in self.raw['files'][0]:
                            return re.sub(self.recordings, self.mirror, self.raw['files'][0][key].encode('utf-8'))
            return ''

        elif key in ['title', 'subtitle', 'description']:

            if key in self.raw:
                if isinstance(self.raw[key], dict):
                    if 'ger' in self.raw[key]:
                        return self.raw[key]['ger'].encode('utf-8')
                else:
                    return self.raw[key].encode('utf-8')

            return ''

        elif key in ['comment']:
            if key in self.raw:
                if self.raw[key]: return self.raw[key]
            return ''

        elif key == 'status': return self._status()

        elif key == 'duration': return (self.raw['stop'] - self.raw['start']) / 60

        elif key in ['flags', 'season', 'number']:
            if key not in self.tvlog: return 0
            else: return int(self.tvlog[key])

        elif key == 'date': return time.strftime('%Y-%m-%d', time.localtime(self.raw['start']))

        elif key == 'begin': return time.strftime('%H:%M', time.localtime(self.raw['start']))

        elif key == 'end': return time.strftime('%H:%M', time.localtime(self.raw['stop']))

        elif key == 'tvlog': return self.raw.get('tvlog', {'type': 'tv'})

        elif key == 'type': return self['tvlog'].get('type', 'tv')

        else:
            if key in self.tvlog:
                return self.tvlog[key]
            if key in self.raw:
                return self.raw[key]

        return None


    def __setitem__(self, key, value):

        if key == 'filename':

            if key in self.raw:
                self.raw[key] = value
            else:
                if 'files' in self.raw:
                    if len(self.raw['files']) > 0:
                        if key in self.raw['files'][0]:
                            self.raw['files'][0][key] = value
                else:
                    self.raw.setdefault('files', [])
                    self.raw['files'].append({key: value})

        elif key in ['title', 'subtitle', 'description']:

            if isinstance(value, dict):
                self.raw[key] = value
            else:
                self.raw.setdefault(key, {})
                self.raw[key]['ger'] = value

        elif key == 'tvlog':
            if key in self.raw: self.raw[key] = value
            else: self.raw.setdefault(key, {})

        else:
            if key in self.raw:
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
        if key in self._data:
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
                    if entry not in result: result[entry] = []
                    result[entry].append(sd[index])
                index += 1
            current += 1

        return result

    def filter(self):

        return sorted(filter(eval(self.tvHeadend.filter), self._data), key=lambda exp: (self._data[exp]['start']))

class LogData(Data):

    def __init__(self, tvHeadend):
        Data.__init__(self, tvHeadend)

    def read(self, path):

        if os.path.isdir(path):
            cwd = os.getcwd()
            os.chdir(path)
            for file in os.listdir('.'):
                if os.path.isdir(file): continue
                uuid = file
                with codecs.open(file, mode='r', encoding='utf-8') as log:
                    self._data[uuid] = json.load(log, encoding='utf-8')
                    #self._data[uuid] = LogEntry(json.load(log, encoding='utf-8'))
                    #self._data[uuid]['tvlog']['status'] = self._data[uuid].status
                    log.close()
                    # self._data[uuid]['uuid'] = uuid
            os.chdir(cwd)
        else:
            with codecs.open(path, mode='r', encoding='utf-8') as log:
                self._data = json.load(log, encoding='utf-8')
                log.close()

    def write(self, path, replace=False):

        if os.path.isdir(path):
            cwd = os.getcwd()
            os.chdir(path)
            for uuid in self.raw:

                if replace:
                    entry = LogEntry(self.raw[uuid])
                else:
                    entry = self.merge(uuid)

                # print json.dumps(entry.raw, indent=4, ensure_ascii=False, encoding='utf-8')
                with codecs.open(uuid, mode='w', encoding='utf-8') as new:
                    json.dump(entry.raw, new, indent=4, ensure_ascii=False, encoding='utf-8')
                    new.close()

            os.chdir(cwd)
        else:
            pass

    def merge(self, uuid):
        # top level only!
        with codecs.open(uuid, mode='r', encoding='utf-8') as log:
            merge = LogEntry(json.load(log, encoding='utf-8'))
            log.close()
            for key in self.raw[uuid]:
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

    def read(self, file):

        csv.register_dialect('tvlog', delimiter='|', quoting=csv.QUOTE_NONE)
        #csvfile = os.path.join(file)
        with codecs.open(file, mode='r', encoding='utf-8') as fh:
            reader = csv.DictReader(fh, dialect='tvlog')
            for entry in reader:
                uuid = entry['uuid']
                # remove uuid from attributes
                del entry['uuid']
                # adjust data type
                for key in ['start', 'stop', 'duration', 'flags', 'season', 'number']:
                    entry[key] = int(entry[key])
                # remove virtual helper attributes
                for key in ['date', 'begin', 'end', 'duration']:
                    if key in entry: del entry[key]
                self._data[uuid] = entry

class TvHeadend():

    def __init__(self, options):

        self._data = None
        self._options = options

        # transformed eval strings
        self._source = None
        self._merge = None
        self._update = None
        self._filter = None
        self._format = None

        # formatted ouput strings
        self._theMerge = None
        self._theUpdate = None
        self._theSource = None
        self._theFilter = None
        self._theFormat = None

        LogEntry.tvHeadend = self

        #self._ppLog = pprint.PrettyPrinter(indent=32)
        self._ppLog = pprint.PrettyPrinter()

    def ppLog(self, obj):
        return self._ppLog.pprint(obj)


#region property definitions

    @property
    def data(self): return self._data

    @data.setter
    def data(self, value): self._data = value

    @property
    def merge(self): return self._merge

    @merge.setter
    def merge(self, value): self._merge = value

    @property
    def options(self): return self._options

    @property
    def logger(self): return self.options.get('logger')

    @property
    def google(self): return self.options.get('google', False)

    @property
    def repair(self): return self.options.get('repair', False)

    @property
    def delete(self): return self.options.get('delete', None)

    @property
    def replace(self): return self.options.get('replace', False)

    @property
    def cwd(self): return self.options.get('cwd')

    @property
    def root(self): return self.options.get('tvheadend')

    @property
    def tvheadend(self): return self.options.get('tvheadend')

    @property
    def recordings(self): return self.options.get('recordings')

    @property
    def mirror(self): return self.options.get('mirror', self.recordings)

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
    def noheader(self): return self.options.get('noheader', False)

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

    def parse_source_spec(self, option):

        source = None; data = None

        if option == 'tvlog':
            source = self.tvlog
            data = LogData(self)
        elif option == 'tvcsv':
            source = self.tvcsv
            data = CsvData(self)
        else:
            source = option
            if os.path.isdir(source):
                data = LogData(self)
            else:
                file, ext = os.path.splitext(source)
                if ext == '.json':
                    data = LogData(self)
                else:
                    data = CsvData(self)

        return source, data

    def run(self):

        self._format = self.parse_output_format()
        self._filter = self.parse_output_filter()

        self._source = self.options['source'].strip('"\'')

        self._theSource, self._data = self.parse_source_spec(self._source)
        self._data.read(self._theSource)

        if self.options['merge']:
            self._merge = self.options['merge'].strip('"\'')
            self._theMerge, self._merge = self.parse_source_spec(self._merge)
            self._merge.read(self._theMerge)

            for key in self.merge.raw:
                if key in self.data.raw:
                    data = self.data[key]
                    merge = self.merge.raw[key]
                    for attr in merge:
                        data[attr] = merge[attr]

        if self.check:
            if self.check in ['conflicts', 'upcoming']:
                self.check_conflicts()
                return
            elif self.check == 'tvdb':
                self.check_tvdb()

        if self.options['update']:
            self._update = self.options['update'].strip('"\'')
            self._theUpdate, self._update = self.parse_source_spec(self._update)
            self._data.write(self._theUpdate, self.replace)

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

            # UTF-8 encode string literals in search expressions
            filter = re.sub("(\'.*?\')", r"u\1.encode('utf-8')", filter)


            self._theFilter = filter

        return "lambda exp, self=self: " + filter

    def parse_output_format(self):

        fmt = self.options['out']
        if fmt.strip('"\'') == 'csv':
            self._theFormat = "CSV"
            fmt = '"{:d}|{:d}|{}|{}|{}|{}|{:d}|{:d}|{}|{}|{}|{}|{}|{}|{}|{:d}|{:d}|{}|{}".format(' \
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

    def _repair(self, raw):

        if 'tvlog' in raw:
            tvlog = raw['tvlog']
            if 'comment' in tvlog:
                del tvlog['comment']

        if 'comment' in raw:
            if raw['comment'] is None:
                raw['comment'] = ''

    def _delete(self, entry):

        for token in self.delete.split(','):
            if token in entry.raw:
                del entry.raw[token]
            else:
                subkey = entry.raw
                top = None
                for key in token.split('.'):
                    if key in subkey:
                        top = key
                        if isinstance(subkey[key], dict):
                            subkey = subkey[key]
                        else:
                            del subkey[key]
                print(top)

    def check_conflicts(self):

        sys.stderr.write("\nChecking for conflicting entries ...\n\n")

        # self.data.read()
        result = self.data.check_conflicts()
        if result:
            counter = 0
            for k in result:
                counter +=1
                print(self.data[k].out(self.format))
                for v in result[k]:
                    print(self.data[v].out(self.format))
                if counter < len(result): print('--')
            print()
            return 1
        else:
            sys.stderr.write("... done!\n")
            return 0

    def list_data(self, reload=False):

        sys.stderr.write("\nSource:\t{0}\nFilter:\t{1}\nFormat:\t{2}\n\n". format(self.theSource, self.theFilter, self.theFormat))

        if self.theFormat == 'CSV' and not self.noheader:
            print(CsvData.header())

        if reload: self.data.read()

        counter = {} ; out = {}
        for k in self.data.filter():

            status = self.data[k].status
            self.data[k]['status'] = status

            if status not in counter:
                counter[status] = 1
            else:
                counter[status] += 1

            if self.delete: self._delete(self.data[k])
            if self.repair: self._repair(self.data[k].raw)

            if self.theFormat == 'JSON':
                # print self.data.merge(k).out(self.format)
                # out.append(self.data[k].raw)
                out[k] = self.data[k].raw
            else:
                print(self.data[k].out(self.format))

        if self.theFormat == 'JSON':
            print(json.dumps(out, indent=4, ensure_ascii=False, encoding='utf-8'))

        sys.stderr.write("\nStatistcs: ")
        for k in counter:
            sys.stderr.write("{0}={1} ".format(k, counter[k]))
        sys.stderr.write("\n\n")

    def check_tvdb(self):

        # self.data.read()
        for k in self.data.filter():
            self.data[k].tvdb()


class LogFileHandler(logging.FileHandler):

    def __init__(self, path, mode='a', endcoding='utf-8'):
        import logging
        path = os.path.expanduser(path)
        logging.FileHandler.__init__(self, path, mode, endcoding)

def main():

    # from six.moves.configparser import ConfigParser
    from ConfigParser import ConfigParser
    from argparse import ArgumentParser

    reload(sys)
    sys.setdefaultencoding('utf-8')

    HOME = os.path.expanduser('~')
    ppLog = pprint.PrettyPrinter(indent=32)

    options = {

        'home':         HOME,
        'tvheadend':    HOME + '/.hts/tvheadend',
        'config':       None,
        'google':       False,
        'recordings':   '/storage/recordings',
        'mirror':       '/storage/recordings',
        'loglevel':     'INFO',
        'out':          '"{} {} {:8} {}".format(.date, .begin, .status, .info)',
        'filter':       'True',
        'source':       'tvlog',
        'merge':        None,
        'delete':       None,
        'update':       None,
        'repair':       False,
        'replace':      False,
        'cwd': os.getcwd()
    }

    # command line arguments
    parser = ArgumentParser(description='TVheadend Toolbox Rev. 0.1 (c) Bernd Strebel')
    parser.add_argument('--tvheadend', type=str, help='tvheadend log directory')
    parser.add_argument('--recordings', type=str, help='recording directory')
    parser.add_argument('--mirror', type=str, help='recordings mirror directory')
    parser.add_argument('--repair', action='store_true', help='repair')
    parser.add_argument('--replace', action='store_true', help='replace')
    parser.add_argument('--delete', type=str, help='delete attributes')
    parser.add_argument('-c', '--config', type=str, help='alternate configuration file')
    parser.add_argument('-v', '--verbose', action='count', help='increasy verbosity')
    parser.add_argument('-s', '--source', type=str, help='data source')
    parser.add_argument('-u', '--update', type=str, help='target directory')
    parser.add_argument('-m', '--merge', type=str, help='merge csv file')
    parser.add_argument('-f', '--filter', type=str, help='filter expression')
    parser.add_argument('-o', '--out', type=str, help='output expression')
    parser.add_argument('-g', '--google', action='store_true', help='use google cse')
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

    if not options['config']:
        script, ext = os.path.splitext(os.path.basename(sys.argv[0]))
        config = script + ".cfg"
        for path in ['./', HOME + '/.', '/etc/']:
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
    for key in ['recordings', 'tvheadend', 'mirror']:
        options[key] = config.get('tvlog', key)
        options[key] = os.getenv(key.upper(), options[key])

    for key in opts:
        if key in options and opts[key] is not None:
            options[key] = opts[key]
        else:
            options.setdefault(key, opts[key])

    options['tvheadend'] = os.path.expanduser(options['tvheadend'])
    options['recordings'] = os.path.expanduser(options['recordings'])
    options['mirror'] = os.path.expanduser(options['mirror'])
    options['tvlog'] = options['tvheadend'] + '/dvr/log'
    options['tvcsv'] = options['tvheadend'] + '/dvr/log.csv'

    options['logger'] = logger

    new_level = getattr(logging, options['loglevel'].upper(), None)
    if new_level:
        logger.setLevel(new_level)

    logger.debug("args: {}".format(' '.join(sys.argv[1:])))
    logger.debug("options:\n" + pp.pformat(options))

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
