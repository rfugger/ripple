from twisted.web import resource

from ripplebase.resource import ObjectListResource
from dao import *

pmt_root = resource.Resource()

class PaymentResource(ObjectListResource):
    DAO = PaymentDAO
pmt_root.putChild('payment', PaymentResource())
