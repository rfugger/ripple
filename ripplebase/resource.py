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

from twisted.web import resource, http, server

from ripplebase import db, json

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
            content = request.content.read()
            if content:
                request.parsed_content = json.decode(content)
        
            # handle outgoing data
            request.setHeader("Content-type",
                          'application/json; charset=utf-8')
            body = SiteResource.render(self, request)
            json_body = json.encode(body).encode('utf-8')  # twisted web expects regular str
        except Http404, h:
            request.setResponseCode(http.NOT_FOUND)
            return str(h)
        except Exception, e:
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            return str(e)
        return json_body


class RequestHandler(object):
    "Generic HTTP resource callable from url framework."
    allowedMethods = ('GET', 'POST', 'DELETE', 'PUT', 'HEAD')
    
    def __init__(self, request):
        self.request = request
        # *** replace with actual client
        from ripplebase import settings
        self.client = settings.TEST_CLIENT
    
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


class ObjectListHandler(RequestHandler):
    "Handler for CRUD on a particular API data model."
    allowedMethods = ('GET', 'POST', 'HEAD')
    
    # Set in subclasses
    DAO = None

    def processing_incoming(self, data_dict):
        "Alter incoming data_dict."
        pass
    def process_outgoing(self, data_dict):
        "Alter outgoing data_dict."
        pass
    
    def get(self):
        "Render list of objects."
        return list(self.filter())

    def post(self):
        "Create new object."
        data_dict = de_unicodify_keys(self.request.parsed_content)
        self.process_incoming(data_dict)
        self.create(data_dict)

    def create(self, data_dict):
        obj = self.DAO.create(**data_dict)
        db.commit()
        return obj

    def filter(self):
        for obj in self.DAO.filter():
            data_dict = obj.data_dict()
            self.process_outgoing(data_dict)
            yield data_dict

class ObjectHandler(RequestHandler):
    """Handler for actions on a single object.
    """
    allowedMethods = ('GET', 'POST', 'DELETE', 'HEAD')

    # set in subclasses
    DAO = None

    def processing_incoming(self, data_dict):
        "Alter incoming data_dict."
        pass
    def process_outgoing(self, data_dict):
        "Alter outgoing data_dict."
        pass
    
    def get(self, *keys):
        "Returns data_dict for object."
        keys = [unicode(key) for key in keys]
        data_dict = self.get_data_dict(*keys)
        self.process_outgoing(data_dict)
        return data_dict

    def post(self, *keys):
        "Update existing object."
        keys = [unicode(key) for key in keys]
        data_dict = de_unicodify_keys(self.request.parsed_content)
        self.process_incoming(data_dict)
        self.update(keys, data_dict)

    def delete(self, *keys):
        return NotImplemented

    def get_data_dict(self, *keys):
        return self.DAO.get(*keys).data_dict()        

    def update(self, keys, data_dict):
        obj = self.DAO.get(*keys)
        obj.update(**data_dict)
        db.commit()

def de_unicodify_keys(d):
    "Makes dict keys regular strings so it can be used for kwargs."
    return dict((str(key), value) for key, value in d.items())


def encode_node_name(node_name, client_id):
    return '%s/%s' % (client_id, node_name)
def decode_node_name(encoded_node_name):
    return encoded_node_name[encoded_node_name.find('/') + 1:]

# for inclusion in classes below
def process_incoming(self, data_dict):
    "Encode node name to make it unique per client."
    if 'node' in data_dict:
        data_dict['node'] = encode_node_name(data_dict['node'], self.client)

def process_outgoing(self, data_dict):
    "Remove client from data_dict, decode node name."
    if 'client' in data_dict:
        del data_dict['client']
    if 'node' in data_dict:
        data_dict['node'] = decode_node_name(data_dict['node'])

class RippleObjectListHandler(ObjectListHandler):
    """For DAOs that have a client field, which is implicit
    in the API, since the server knows who the client is already.
    """
    process_incoming = process_incoming
    process_outgoing = process_outgoing

    def create(self, data_dict):
        "Add client key to data_dict."
        if 'client' in self.DAO.db_fields:
            data_dict['client'] = self.client
        return super(RippleObjectListHandler, self).create(data_dict)

    def filter(self):
        if 'client' in self.DAO.db_fields:
            filter_kwargs = {self.DAO.db_fields['client']: self.client}
        else:
            filter_kwargs = {}
        for obj in self.DAO.filter(**filter_kwargs):
            d = obj.data_dict()
            self.process_outgoing(d)
            yield d
    
class RippleObjectHandler(ObjectHandler):
    # reuse methods
    process_incoming = process_incoming
    process_outgoing = process_outgoing

