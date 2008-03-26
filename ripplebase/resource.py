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
                return url.callback(request, *args, **kwargs)

class JSONSiteResource(SiteResource):
    def render(self, request):
        request.setHeader("Content-type",
                          'application/json; charset=utf-8')
        body = SiteResource.render(self, request)
        json_body = json.encode(body)
        return json_body.encode('utf-8')  # twisted web expects regular str

class ObjectListResource(object):
    "Resource for CRUD on a particular API data model."
    allowedMethods = ('GET', 'POST')

    # Set in subclasses
    DAO = None

    def __call__(self, request):
        if request.method not in self.allowedMethods:
            raise server.UnsupportedMethod(getattr(self, 'allowedMethods', ()))
        return getattr(self, request.method.lower())(request)
    
    def get(self, request):
        "Render list of objects."
        return list(self.filter())

    def post(self, request):
        "Create new object."
        content = request.content.read()
        data_dict = de_unicodify_keys(json.decode(content))
        self.create(data_dict)
        request.setResponseCode(http.CREATED)

    def create(self, data_dict):
        obj = self.DAO.create(**data_dict)
        db.commit()
        return obj

    def filter(self):
        for obj in self.DAO.filter():
            yield obj.data_dict()

class ObjectResource(object):
    """Resource for actions on a single object.
    """
    allowedMethods = ('GET', 'POST', 'DELETE')

    # set in subclasses
    DAO = None
    
    def __call__(self, request, *keys):
        "Calls appropriate method for this request."
        if request.method not in self.allowedMethods:
            raise server.UnsupportedMethod(getattr(self, 'allowedMethods', ()))
        return getattr(self, request.method.lower())(request, *keys)
    
    def get(self, request, *keys):
        "Returns data_dict for object."
        keys = [unicode(key) for key in keys]
        return self.DAO.get(*keys).data_dict()

    def post(self, request, *keys):
        raise NotImplemented

    def delete(self, request, *keys):
        raise NotImplemented
        
def de_unicodify_keys(d):
    "Makes dict keys regular strings so it can be used for kwargs."
    return dict((str(key), value) for key, value in d.items())


class ClientFieldAwareObjectListResource(ObjectListResource):
    """For DAOs that have a client field, which is implicit
    in the API, since the server knows who the client is already.
    """
    def create(self, data_dict):
        "Add client key to data_dict."
        # *** replace with actual client
        from ripplebase import settings
        data_dict['client'] = settings.TEST_CLIENT
        super(ClientFieldAwareObjectListResource, self).create(data_dict)

    def filter(self):
        # *** replace with actual client
        from ripplebase import settings
        client = settings.TEST_CLIENT
        for obj in self.DAO.filter(client=client):
            d = obj.data_dict()
            del d['client']
            yield d
    
class ClientFieldAwareObjectResource(ObjectResource):
    def get(self, request, key):
        "Restrict to calling client; remove client field."
        # *** replace with actual client
        from ripplebase import settings
        client = settings.TEST_CLIENT
        d = super(ClientFieldAwareObjectResource, self).get(request, key, client)
        del d['client']
        return d
    
