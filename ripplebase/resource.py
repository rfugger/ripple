##################
# Copyright 2008, Ryan Fugger
#
# This file is part of Ripplebase.
#
# Ripplebase is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as 
# published by the Free Software Foundation, either version 3 of the 
# License, or (at your option) any later version.
#
# Ripplebase is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public 
# License along with Ripplebase, in the file LICENSE.txt.  If not,
# see <http://www.gnu.org/licenses/>.
##################

import re
import traceback

from twisted.web import resource, http, server
from twisted.internet import threads

from ripplebase import db, json, settings
from ripplebase.account.mappers import Client

class Http404(Exception):
    pass

class URL(object):
    def __init__(self, regex_src, callback):
        self.regex = re.compile(regex_src)
        self.callback = callback

def compile_urls(raw_urls):
    urls = []
    for raw_url in raw_urls:
        urls.append(URL(raw_url[0], raw_url[1]))
    return urls

class SiteResource(resource.Resource):
    """Implements a framework for storing URLs in django-like fashion,
    as regex's, and dispatches calls to the corresponding resources.
    """
    isLeaf = True
    
    def __init__(self, urls):
        resource.Resource.__init__(self)
        self.urls = compile_urls(urls)

    def render(self, request):
        "Render using urls list like django."
        for url in self.urls:
            match = url.regex.search(request.path)
            if match:
                # if there are named groups, use those
                kwargs = match.groupdict()
                if kwargs:
                    args = ()  # empty tuple
                else:
                    args = match.groups()
                if issubclass(url.callback, RequestHandler):
                    callable = url.callback(request)
                else:
                    callable = url.callback
                content = callable(request, *args, **kwargs)
                return content
        raise Http404("No resource at '%s'." % request.path)

class JSONSiteResource(SiteResource):
    "Automatically handles JSON encoding and decoding and headers."
    def render(self, request):
        try:
            # handle incoming data
            if settings.DEBUG: print '\n', request.path
            content = request.content.read()
            if content:
                request.parsed_content = json.decode(content)
                if settings.DEBUG: print content
            if settings.DEBUG: print db.session
            # handle outgoing data
            request.setHeader("Content-type",
                          'application/json; charset=utf-8')
            body = SiteResource.render(self, request)
        except Http404, h:
            if settings.DEBUG: traceback.print_exc()
            request.setResponseCode(http.NOT_FOUND)
            body = str(h)
        except Exception, e:  # *** this might catch too much
            if settings.DEBUG: traceback.print_exc()
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            body = str(e)
        # close out db session -- very important with threads
        db.commit()
        db.close()
        if body not in (None, ''):
            json_body = encode_response(body)
            if settings.DEBUG:
                print json_body
            return json_body
        return ''

def encode_response(response):
    # twisted web expects regular str, which encode('utf-8') gives
    return json.encode(response).encode('utf-8')
    
class ThreadedJSONSiteResource(JSONSiteResource):
    "Run each request in its own thread."
    def render(self, request):
        d = threads.deferToThread(JSONSiteResource.render, self, request)
        def callback(response):
            request.write(response)
            request.finish()
        def errback(failure):
            request.write(encode_response(str(failure)))
            request.finish()
        d.addCallbacks(callback, errback)
        return server.NOT_DONE_YET
        

class RequestHandler(object):
    "Generic HTTP resource callable from url framework."
    allowedMethods = ('GET', 'POST', 'DELETE', 'PUT', 'HEAD')
    
    def __init__(self, request):
        self.request = request
        # *** replace with actual requesting client
        self.client = db.query(Client).filter_by(name=settings.TEST_CLIENT).one()
    
    def __call__(self, request, *args, **kwargs):
        "Creates resource object and calls appropriate method for this request."
        if request.method not in self.allowedMethods:
            raise server.UnsupportedMethod(getattr(self, 'allowedMethods', ()))
        return getattr(self, request.method.lower())(*args, **kwargs)

    def get(self, *args, **kwargs):
        return NotImplemented
    def post(self, *args, **kwargs):
        return NotImplemented
    def delete(self, *args, **kwargs):
        return NotImplemented
    def put(self, *args, **kwargs):
        return NotImplemented
    def head(self, *args, **kwargs):
        # Twisted handles HEAD internally if we just do a GET.
        return self.get(request, *args, **kwargs)


# *** add validators to request handlers below
class ObjectListHandler(RequestHandler):
    "Handler for CRUD on a particular API data model."
    allowedMethods = ('GET', 'POST', 'HEAD')
    
    # Set in subclasses
    DAO = None

    def get(self):
        "Render list of objects."
        # *** here is where filter params would be gotten from request URI
        return list(self.filter())

    def post(self):
        "Create new object."
        data_dict = de_unicodify_keys(self.request.parsed_content)
        self.create(data_dict)
        #db.commit()

    def create(self, data_dict):
        obj = self.DAO.create(**data_dict)
        return obj

    def filter(self, **kwargs):
        for obj in self.DAO.filter(**kwargs):
            data_dict = obj.data_dict()
            yield data_dict

class ObjectHandler(RequestHandler):
    """Handler for actions on a single object.
    """
    allowedMethods = ('GET', 'POST', 'DELETE', 'HEAD')

    # set in subclasses
    DAO = None

    def get(self, *keys):
        "Returns data_dict for object."
        keys = [unicode(key) for key in keys]
        dao = self._get_dao(*keys)
        return dao.data_dict()

    def post(self, *keys):
        "Update existing object."
        keys = [unicode(key) for key in keys]
        data_dict = de_unicodify_keys(self.request.parsed_content)
        self.update(keys, data_dict)
        #db.commit()

    def delete(self, *keys):
        # don't forget to commit here
        return NotImplemented

    def _get_dao(self, *keys):
        return self.DAO.get(*keys)

    def update(self, keys, data_dict):
        obj = self._get_dao(*keys)
        obj.update(**data_dict)

def de_unicodify_keys(d):
    "Makes dict keys regular strings so it can be used for kwargs."
    return dict((str(key), value) for key, value in d.items())


class RippleObjectListHandler(ObjectListHandler):
    "Handle client field."
    def create(self, data_dict):
        """Need to give ref to client even if this DAO doesn't use it --
        may be needed to look up a foreign object reference.
        """
        data_dict['client'] = self.client
        return super(RippleObjectListHandler, self).create(data_dict)

    # filter should be OK here because it traverses DB relationships,
    # which use DB keys, not natural keys involving the client.
    
class RippleObjectHandler(ObjectHandler):
    def _get_dao(self, *keys):
        if self.DAO.has_client_as_key:
            return self.DAO.get(*keys, **dict(client=self.client))
        else:
            return super(RippleObjectHandler, self)._get_dao(*keys)

    def update(self, keys, data_dict):
        """Need to give ref to client even if this DAO doesn't use it --
        may be needed to look up a foreign object reference.
        """
        data_dict['client'] = self.client
        super(RippleObjectHandler, self).update(keys, data_dict)
