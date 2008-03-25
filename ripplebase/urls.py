"Site URL configuration"

from ripplebase.account import resources as acct

urls = (
    # nodes
    ('^/nodes/?$', acct.node_list),
    ('^/nodes/([^/]+)/?$', acct.node),

    # addresses
    ('^/addresses/?$', acct.address_list),
    ('^/addresses/([^/]+)/?$', acct.address),
)
