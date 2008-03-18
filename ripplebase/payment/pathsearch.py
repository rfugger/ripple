from decimal import Decimal as D
# *** Make sure decimal module is configured for right precision,
#     and identical to DB precision.  (May have to write our own
#     FixedPoint class???)
# *** Round all numbers to be stored to 12 places.  Write
#     a round function to do this easily.

MAX_HOPS = 1000

class HopLimitReached(Exception):
    pass

class DeadEnd(Exception):
    pass


class Link(object):
    """A path-finding abstraction for holding two account versions
    that make up a link between nodes.
    """
    def __init__(self, src_node, dest_node,
                 src_acct, dest_acct,
                 backward):
        """'src_node/acct' and 'dest_node/acct' refer to direction
        of search.  If search direction is opposite payment direction,
        set backward=True.
        """
        self.src_node = src_node
        self.dest_node = dest_node
        self.src_acct = src_acct
        self.dest_acct = dest_acct
        self.backward = backward
        
    def get_paying_node(self):
        return backward and dest_node or src_node
    paying_node = property(get_paying_node)

    def get_receiving_node(self):
        return backward and src_node or dest_node
    receiving_node = property(get_receiving_node)
    
    def get_paying_acct(self):
        return backward and dest_acct or src_acct
    paying_acct = property(get_paying_acct)
    
    def get_receiving_acct(self):
        return backward and src_acct or dest_acct
    receiving_acct = property(get_receiving_acct)
    
class PathElement(object):
    """Payment abstraction for holding two account versions
    that make up a link between nodes.  
    """
    def __init__(self, link,
                 amount, path_units_amount):
        self.link = link
        self.amount = amount  # in link (account) units

class Path(object):
    def __init__(self, amount, element_list=[]):
        self.amount = amount  # in path units
        self.element_list = element_list

    def prepend_link(self, link, path_to_link_exchange_rate):
        link_amount = self.amount * path_to_link_exchange_rate
        elt = PathElement(link, link_amount)
        if link.backwards:
            self.element_list.append(elt)
        else:
            self.element_list.insert(0, elt)
        
class PathSet(object):
    """Set of paths for payment.
    """
    def __init__(self, path_list=[])
        self.path_list = path_list

    def merge(self, path_set):
        self.path_list += path_set.path_list

    def prepend_link(self, link, path_to_link_exchange_rate):
        for path in self.path_list:
            path.prepend_link(link, path_to_link_exchange_rate)

    def get_total_amount(self):
        total = D('0.0')
        for path in self.path_list:
            total += path.amount
        return total
    amount = property(get_total_amount)
    
        
class Hop(object):
    "A potential search direction."
    def __init__(self, link,
                 available_credit,
                 exchange_rate,  # from previous link
                 distance_list):
        self.link = link
        self.available_credit = available_credit
        self.exchange_rate = exchange_rate
        self.distance_list = distance_list


class PathSearch(object):
    def __init__(self, payer_nodes, recipient_nodes, amounts,
                 src_accts, backward=True):
        self.payer_nodes = payer_nodes
        self.recipient_nodes = recipient_nodes
        self.amounts = amounts
        self.src_accts = src_accts
        assert len(amounts) = len(src_accts)
        
        self.backward = backward
        if backward:
            self.src_nodes = recipient_nodes
            self.dest_nodes = payer_nodes
        else:
            self.src_nodes = payer_nodes
            self.dest_nodes = recipient_nodes
        assert len(amounts) = len(src_accts)
        assert len(amounts) = len(src_nodes)

    def find_pathset(self, hops_to_live=MAX_HOPS):
        """Searches src_nodes in order until the required
        amount is found.  Returns a list of PathSets, one
        for each src_node.
        Raises HopLimitReached when hops_to_live runs out.
        """
        # init search data
        self.credit_used = {}  # dict indexed by Link
        self.exhausted_nodes = set()
        self.hops_to_live = hops_to_live

        pathset_list = []
        remaining_proportion = D('1.0')
        for node, amount in zip(self.src_nodes, self.amounts):
            search_amount = amount * remaining_proportion
            found_pathset = self.search(node, search_amount, in_acct)
                                                backward=self.backward)
            pathset_list.append(found_pathset)
            remaining_proportion -= found_pathset.amount / amount
            if remaining_proportion == D('0.0'):
                break
        return pathset_list


    def search(self, node, amount, path_amount, src_acct, curr_path_nodes=[]):
        """Returns a hopset, with amount of credit in src_acct
        units.
        """
        self.hops_to_live -= 1
        if self.hops_to_live == 0:  # give up
            raise HopLimitReached()

        next_hop_list = self.get_next_hop_list(node, amount,
                                               src_acct)
        
        pathset = PathSet()
        remaining_path_amount = path_amount
        path_exchange_rate = amount / path_amount
        for hop in next_hop_list:
            # Avoid searching already-exhausted accounts,
            # or going in loops
            if hop.src_node_acct in exhausted_accts or \
                    hop.dest_node in curr_path_nodes:
                continue

            if hop.available_credit > D('0.0'):
                # compute amount to search for in this direction
                path_to_hop_exchange_rate = path_exchange_rate * hop.exchange_rate
                remaining_hop_amount = path_remaining_amount * path_to_hop_exchange_rate
                search_hop_amount = min(hop.available_credit, remaining_hop_amount)
                # convert search_hop_amount to path units
                search_path_amount = search_hop_amount / path_to_hop_exchange_rate

                # *** make sure decimal precision is high enough here so that
                #     we get the original remaining_path_amount back exactly
                #     if that's what we're looking for.
                if search_hop_amount == remaining_hop_amount:
                    assert search_path_amount = remaining_path_amount

                # check if we've reached destination
                if hop.dest_node in self.dest_nodes:
                    found_pathset = PathSet([Path(search_path_amount)])
                else:
                    # recursive call to search
                    try:
                        found_pathset = self.search(
                            hop.next_node,
                            search_hop_amount,
                            search_path_amount,
                            hop.dest_node_acct,
                            cur_path_nodes + [node])
                    except DeadEnd:
                        continue
                    
                found_pathset.prepend(hop.link, path_to_hop_exchange_rate)
                pathset.merge(found_pathset)
                if pathset.amount == path_amount:
                    return pathset
                remaining_amount -= search

        if pathset.amount < path_amount:
            self.exhausted_nodes.add(node)
        if pathset.amount == D('0.0'):
            raise DeadEnd()
            
        return pathset
                
            
    def sort_next_hop_list(self, next_hop_list, amount):
        pass

    def get_next_hop_list(self, node, in_acct, dest_list):
        pass

