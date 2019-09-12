#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import datetime
from concurrent.futures import ThreadPoolExecutor

import tornado.web
import tornado.ioloop
import tornado.options
import tornado.httpserver
from tornado import gen, escape
from tornado.options import define, options
from tornado.concurrent import run_on_executor

from elasticsearch_dsl import Search
from elasticsearch import Elasticsearch
from elasticsearch_dsl.query import Term, Match, Wildcard, Regexp, Fuzzy


INDEX = 'pwd_*'
DOC_TYPE = 'account'
LOG_INDEX = 'pwdlogs'
LOG_DOC_TYPE = 'log'

QUERY_KINDS = {
    'term': Term,
    'match': Match,
    'fuzzy': Fuzzy,
    'regexp': Regexp,
    'wildcard': Wildcard
}


class BaseHandler(tornado.web.RequestHandler):
    # A property to access the first value of each argument.
    arguments = property(lambda self: dict([(k, v[0].decode('utf-8'))
                                            for k, v in self.request.arguments.items()]))

    @property
    def clean_body(self):
        """Return a clean dictionary from a JSON body, suitable for a query on MongoDB.

        :returns: a clean copy of the body arguments
        :rtype: dict"""
        return escape.json_decode(self.request.body or '{}')

    def initialize(self, **kwargs):
        """Add every passed (key, value) as attributes of the instance."""
        for key, value in kwargs.items():
            setattr(self, key, value)


class RootHandler(BaseHandler):
    """Handler for the / path."""
    app_path = os.path.join(os.path.dirname(__file__), "dist")

    @gen.coroutine
    def get(self, *args, **kwargs):
        # serve the ./app/index.html file
        with open(self.app_path + "/index.html", 'r') as fd:
            self.write(fd.read())


class PasswordsHandler(BaseHandler):
    executor = ThreadPoolExecutor(max_workers=8)

    def _to_dict(self, results):
        ret = []
        for result in results:
            item = dict([(k, result[k]) for k in dir(result) if k != 'meta'])
            item['score'] = result.meta.score
            item['id'] = result.meta.id
            ret.append(item)
        return ret

    @run_on_executor
    def log(self, log):
        try:
            self.es.index(index=LOG_INDEX, doc_type=LOG_DOC_TYPE, body=log)
        except Exception as e:
            print('Error logging: %s' % e)

    @run_on_executor
    def query(self, q, kind='term', field='email.raw',
              offset=0, limit=20, index=INDEX, doc_type=DOC_TYPE):
        search = Search(using=self.es, index=index, doc_type=doc_type)
        if isinstance(q, dict):
            search.update_from_dict(q)
        else:
            if kind == 'default':
                search.query = (Term(**{'email.raw': {'value': q, 'boost': 3}}) |
                    Term(**{'username.raw': {'value': q, 'boost': 2}}) |
                    Match(username={'query': q}))
            else:
                cls_ = QUERY_KINDS[kind]
                search = search.query(cls_(**{field: q}))
        results = search[offset:offset+limit].execute()
        return dict(results=results, total=results.hits.total,
                    took=results.took, timed_out=results.timed_out)

    @gen.coroutine
    def get(self):
        args = self.clean_body
        args.update(self.arguments)
        if '' in args:
            del args['']
        for key in 'offset', 'limit', 'page':
            if key in args:
                args[key] = int(args[key])
        do_log = True
        if 'nolog' in args:
            if args['nolog']:
                do_log = False
            del args['nolog']
        if args.get('page') not in (None, 1):
            do_log = False
        if 'page' in args and 'limit' in args:
            args['offset'] = (args['page'] - 1) * args['limit']
            del args['page']
        if 'q' not in args:
            new_args = {}
            for arg in 'offset', 'limit', 'page':
                try:
                    new_args[arg] = args.pop(arg)
                except KeyError:
                    pass
            new_args['q'] = args.copy()
            args = new_args
        if args.get('q'):
            try:
                res = yield self.query(**args)
            except Exception as e:
                self.logger.error('query error: %s' % e)
                res = {'results': [], 'total': 0}
        else:
            do_log = False
            res = {'results': [], 'total': 0}
        res['results'] = self._to_dict(res['results'])
        if do_log:
            try:
                q = args.get('q') or ''
                if isinstance(q, dict):
                    q = repr(q)
            except Exception as e:
                self.logger.info('unable to get q: %s' % e)
                q = '-missing-'
            log = {
                'timestamp': datetime.datetime.utcnow(),
                'q': q,
                'kind': args.get('kind') or '',
                'field': args.get('field') or '',
                'limit': args.get('limit') or 0,
                'took': res.get('took') or 0,
                'timed_out': res.get('timed_out') or False,
                'hits': res.get('total') or 0
            }
            self.log(log)
        self.write(res)


def run():
    # command line arguments; can also be written in a configuration file,
    # specified with the --config argument.
    define("port", default=12345, help="run on the given port", type=int)
    define("address", default='', help="bind the server at the given address", type=str)
    define("ssl_cert", default=os.path.join(os.path.dirname(__file__), 'ssl', 'elastipass_cert.pem'),
            help="specify the SSL certificate to use for secure connections")
    define("ssl_key", default=os.path.join(os.path.dirname(__file__), 'ssl', 'elastipass_key.pem'),
            help="specify the SSL private key to use for secure connections")
    define("debug", default=False, help="run in debug mode")
    define("config", help="read configuration file",
            callback=lambda path: tornado.options.parse_config_file(path, final=False))
    tornado.options.parse_command_line()

    #es = Elasticsearch(['elasticsearch'], timeout=240, http_auth=('elastic', 'changeme'))
    es = Elasticsearch(['elasticsearch'], timeout=240)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if options.debug:
        logger.setLevel(logging.DEBUG)

    ssl_options = {}
    if os.path.isfile(options.ssl_key) and os.path.isfile(options.ssl_cert):
        ssl_options = dict(certfile=options.ssl_cert, keyfile=options.ssl_key)

    init_params = dict(es=es, logger=logger)
    application = tornado.web.Application([
            (r'/api/?', PasswordsHandler, init_params),
            (r'/(?:index.html)?', RootHandler, init_params),
            (r'/?(.*)', tornado.web.StaticFileHandler, {'path': 'dist'})
        ],
        static_path=os.path.join(os.path.dirname(__file__), "dist/static"),
        debug=options.debug)

    http_server = tornado.httpserver.HTTPServer(application, ssl_options=ssl_options or None)
    logger.info('Start serving on %s://%s:%d', 'https' if ssl_options else 'http',
                                                 options.address if options.address else '127.0.0.1',
                                                 options.port)
    http_server.listen(options.port, options.address)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        print('Stop server')
