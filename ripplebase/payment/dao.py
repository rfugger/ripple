"API resource -> data object mappers."

from mappers import *
from ripplebase import db

class PaymentDAO(db.DAO):
    model = Payment
    fields = {}
    keys = []

    @classmethod
    def api_to_db(cls, **kwargs):
        pass

    
