"Site URL configuration"

from ripplebase.account import resources as acct

urls = (
    ('^/nodes/?$', acct.nodes),
    ('^/nodes/([^/]+)/?$', acct.node),
)
