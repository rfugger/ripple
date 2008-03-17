"API resource -> data object mappers."

from ripplebase.account.mappers import *
from ripplebase import db

class ClientDAO(db.DAO):
    model = Client
    db_fields = {
        'name': 'name',
    }
    keys = ['name']

class NodeDAO(db.DAO):
    model = Node
    db_fields = {
        'name': 'name',
        'client': 'client',  # maps to Client.name
    }
    keys = ['name']
    fk_daos = {
        'client': ClientDAO,
    }

    @classmethod
    def _get_data_obj(cls, *keys, **kwargs):
        "Client filter may be passed in kwargs."
        client = kwargs.get('client')        
        if client is None:
            return super(NodeDAO, cls)._get_data_obj(*keys)
        return cls.filter(name=keys[0], client=client)[0].data_obj
        
class AddressDAO(db.DAO):
    model = Address
    db_fields = {
        'address': 'address',
        'client': 'client',  # maps to Client.name
        'nodes': None,  # maps to m2m association table
    }
    keys = ['address']
    fk_daos = {
        'client': ClientDAO,
    }

    def __setattr__(self, attr, value):
        if attr == 'nodes':
            self.data_obj.nodes = []
            for node_name in value:  # value is list of node names
                node_dao = NodeDAO.get(node_name)
                # ensure node client matches address client
                # *** maybe better done elsewhere?
                if self.client:
                    assert self.client == node_dao.client, \
                        "Invalid node: '%s'." % node_name
                self.data_obj.nodes.append(node_dao.data_obj)
        else:
            # check that self.client matches all node clients
            # *** maybe better done elsewhere?
            if attr == 'client':
                for node in self.data_obj.nodes:  # list of Node
                    # value is client name
                    assert value == node.client.name, \
                        "Invalid node: '%s'." % node.name
            super(AddressDAO, self).__setattr__(attr, value)

    def __getattr__(self, attr):
        if attr == 'nodes':
            return [node.name for node in self.data_obj.nodes]
        else:
            return super(AddressDAO, self).__getattr__(attr)
    
class AccountDAO(db.DAO):
    model = Account
    db_fields = {
        'name': 'name',
        'node': 'node',
        'balance': 'balance',
        'upper_limit': None,  # maps to AccountLimits.upper_limit
        'lower_limit': None,  # maps to AccountLimits.lower_limit
        'limits_effective_time': None,  # maps to AccountLimits.effective_time
        'limits_expiry_time': None, # maps to AccountLimits.expiry_time
    }
    keys = ['name']
    fk_daos = {
        'node': NodeDAO,
    }

    limits_map = {
        'upper_limit': 'upper_limit',
        'lower_limit': 'lower_limit',
        'limits_effective_time': 'effective_time',
        'limits_expiry_time': 'expiry_time',
    }

    def get_active_limits(self):
        if not hasattr(self, '_limits'):
            db_limits = db.query(AccountLimits).filter_by(
                account=self.data_obj, is_active=True).all()
            if db_limits:
                self._limits = db_limits[0]
            else:
                self._limits = None
        return self._limits
    def set_active_limits(self, limits):
        self._limits = limits
    limits = property(get_active_limits, set_active_limits)
    
    def new_limits(self):
        """Call every time new limits are set.
        Sets old limits (if they exist) to inactive, creates
        new active limits record.
        Must then set upper, lower limits and effective,
        expiry times before flushing sessions to db.
        """
        # *** maybe better to set limit attributes in this
        # function to make sure?
        # nah, probably ok to treat these attributes like other
        # account attributes
        # but maybe should copy old limits attribute values?
        if self.limits:
            self.limits.is_active = False
        self.limits = AccountLimits()
        self.limits.is_active = True
        self.limits.account = self.data_obj
    
    def __setattr__(self, attr, value):
        if attr in self.limits_map:
            # make new limits obj if one doesn't exist
            if not self.limits:
                self.new_limits()
            setattr(self.limits, self.limits_map[attr], value)
        else:
            super(AccountDAO, self).__setattr__(attr, value)

    def __getattr__(self, attr):
        if attr in self.limits_map:
            return getattr(self.limits, self.limits_map[attr])
        else:
            return super(AccountDAO, self).__getattr__(attr)

class ExchangeDAO(db.DAO):
    model = Exchange
    db_fields = {
        'source_account': 'source_account',
        'target_account': 'target_account',
        'rate': 'rate',
    }
    # nothing refers to this, so don't need keys
    fk_daos = {
        'source_account': AccountDAO,
        'target_account': AccountDAO,
    }
        

class ExchangeRateDAO(db.DAO):
    model = ExchangeRate
    db_fields = {
        'name': 'name',
        'rate': 'rate',  # maps to ExchangeRateEntry.rate
        'effective_time': 'effective_time',  # maps to ExchangeRateEntry.effective_time 
        'expiry_time': 'expiry_time',  # maps to ExchangeRateEntry.expiry_time
    }
    keys = ['name']

    # *** handle nonstandard fields
