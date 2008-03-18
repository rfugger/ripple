from twisted.web import resource, http

from ripplebase import db, json

def render_json(self, request):
    request.setHeader("Content-type",
                      'application/json; charset=utf-8')
    body = resource.Resource.render(self, request)
    return body.encode('utf-8')  # twisted web expects regular str
    
class ObjectResource(json.JSONResource):
    """Resource for actions on a single object.
    Automatically created by ObjectListResource init.
    """
    isLeaf = True
    allowedMethods = ('GET', 'POST', 'DELETE')
    
    def __init__(self, DAO=None):
        resource.Resource.__init__(self)
        self.DAO = DAO

    render = render_json
    
    def render_GET(self, request):
        "Return object data."
        key = unicode(request.prepath[-1])
        return json.encode(self.get(key))

    def get(self, *keys):
        "Returns data_dict for object."
        return self.DAO.get(*keys).data_dict()
    
    def render_POST(self, request):
        "Update object."

    def render_DELETE(self, request):
        "Delete object."

class ObjectListResource(json.JSONResource):
    "Resource for CRUD on a particular API data model."
    allowedMethods = ('GET', 'POST')

    # Set in subclasses
    DAO = None
    resource_instance_class = ObjectResource

    def __init__(self):
        resource.Resource.__init__(self)
        self.res_instance = self.resource_instance_class(self.DAO)

    def getChild(self, name, request):
        if name == '':  # indicates trailing slash on path
            return self
        else:  # Single object resource
            return self.res_instance
    
    render = render_json
        
    def render_GET(self, request):
        "Render list of objects."
        return json.encode(list(self.filter()))

    def render_POST(self, request):
        "Create new object."
        content = request.content.read()
        data_dict = de_unicodify_keys(json.decode(content))
        self.create(data_dict)
        request.setResponseCode(http.CREATED)
        return ''

    def create(self, data_dict):
        obj = self.DAO.create(**data_dict)
        db.commit()
        return obj

    def filter(self):
        for obj in self.DAO.filter():
            yield obj.data_dict()
            
        
def de_unicodify_keys(d):
    return dict((str(key), value) for key, value in d.items())

