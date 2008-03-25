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

######### old stuff #############
    
class ObjectResource(object):
    """Resource for actions on a single object.
    """
    allowedMethods = ('GET', 'POST', 'DELETE')

    # set in subclasses
    DAO = None
    
    def __call__(self, request, *keys):
        print keys
        if request.method == 'GET':
            response = self.get(request, *keys)
        elif request.method == 'POST':
            raise NotImplemented
        elif request.method == 'DELETE':
            raise NotImplemented
        else:
            raise server.UnsupportedMethod(getattr(self, 'allowedMethods', ()))
        return response
    
    def get(self, request, *keys):
        "Returns data_dict for object."
        keys = [unicode(key) for key in keys]
        return self.DAO.get(*keys).data_dict()
    

class ObjectListResource(resource.Resource):
    "Resource for CRUD on a particular API data model."
    allowedMethods = ('GET', 'POST')

    # Set in subclasses
    DAO = None

    def __call__(self, request):
        if request.method == 'GET':
            response = self.get(request)
        elif request.method == 'POST':
            response = self.post(request)
        else:
            raise server.UnsupportedMethod(getattr(self, 'allowedMethods', ()))
        return response
    
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
            
        
def de_unicodify_keys(d):
    return dict((str(key), value) for key, value in d.items())

