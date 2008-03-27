from psycopg import connect
# from routing.rmanager import ROUTING_DB_CONNECT_STR
import time
import sys
from operator import getitem, setitem, add, getslice

ROUTING_DB_CONNECT_STR = "dbname=routing_dev_db1 user=dev1 password=devdevdevdev host=localhost"

conn = connect(ROUTING_DB_CONNECT_STR)
curs = conn.cursor()
conn.autocommit()

RESULT_NODE_EXHAUSTED = 0
RESULT_PATH_FOUND = 1
RESULT_ALL_PATHS_FOUND = 2
RESULT_GOING_UP_REGRESSION_CHAIN = 4 # the node wasn't the destination node, nor has it exhausted
RESULT_INTERMEDIARY_HOP = 8          # nothing special about this hop
RESULT_PATH_GENERATOR_EXHAUSTED = 16 # sick and tired; let's give up :) travelled through maximum specified nr of nodes

# a bit of magic, to allow passing either object or its certain attribute to a function;
# meta_to_attr returns decorator corresponding to provided lists:
#   - argument position in args list arg_pos_list;
#   - corresponding attribute name list attr_name_list.
# The returned decorator will attempt to get the corresponding attributes of objects in
#   args at given positions, and pass to the decorated function;
# If AttributeError is risen, gives up and passes raw objects.
def meta_deco_to_attr(arg_pos_list, attr_name_list):
    """
    Return the object-to-attribute argument conversion decorator
    """
    def deco(fn):
        def fn_wrapper(cls, *args, **kwargs):
            #print "deco: args: %s" % args
            args_list = list(args)
            #print "deco: args_list = %s" % args_list
            args_tobe_changed_list = map(getitem, (args_list,)*len(arg_pos_list), arg_pos_list)
            try:
                changed_args_list = map(getattr, args_tobe_changed_list, attr_name_list)
            except:
                return fn(cls, *args, **kwargs)
            changed_args = tuple(changed_args_list)
            return fn(cls, *changed_args, **kwargs)
        return fn_wrapper
    return deco

hop_to_id = meta_deco_to_attr([0], ['id'])

def edge_to_src_dest(fn):
    """
    Decorator function which, if argument is of _Edge type, converts it into
    two CONTEXTED _Hop type arguments.
    """
    def fn_wrapper(cls, arg1, arg2, *args, **kwargs):
        args_list = list(args)
        if arg1.__class__ == Edge.underlying_type:
            src_hop = Hop(arg1.src, context = arg2)
            dest_hop = Hop(arg1.dest, context = arg2)
            context = arg2
            return fn(cls, src_hop, dest_hop, context, *args, **kwargs)
        else:
            return fn(cls, arg1, arg2, *args, **kwargs)
    return fn_wrapper

def cr_autonext(cr_gen):
    """
    Coroutine decorator function. Auto-executes ".next()" method upon creation of the "cr_gen" coroutine.
    (so that ".send" method can be used immediately)
    """
    def cr_wrapper(*args, **kwargs):
        cr = cr_gen(*args, **kwargs)
        cr.next()
        return cr
    return cr_wrapper

    
class EGSException(Exception):
    pass

class EdgeException(Exception):
    pass

class Edge(object):
    """
    Smart proxy for object representation of edge between nodes. If instance of edge, queried in
    the constructor call, already exists - returns existing edge; creates new instance otherwise.
    Edges can be bound to specific context, by passing context parameter to the constructor.
    The same edge is represented by distinct objects in different contexts. Context parameter
    is arbitrary hashable parameter. I use id(context_object)
    """
    global mao
    _edge_dict = {}
    _contextual_edge_dicts = {}
    mao_synced = False
    
    class _Edge(object):
        # underlying edge representation
        def __init__(self, src, dest, credit_limit, context = None):
            self.src = Hop(src, context)
            self.dest = Hop(dest, context)
            
            self.credit_limit = credit_limit

    underlying_type = _Edge     # for @edge_to_src_dest decorator to access the underlying type
            
    @edge_to_src_dest
    def __new__(cls, src, dest, context = None):
        # src and dest are expected to be Hop's, not ids
        if not cls.mao_synced:
            mao.synchronize_with_metric_db_table()
            cls.mao_synced = True
        if context is None:
            edge_dict = cls._edge_dict
        else:
            edge_dict = cls._contextual_edge_dicts.setdefault(context, {})
        try:
            return edge_dict[src.id][dest.id]
        except KeyError:
            try:
                credit_limit = mao.metric_cache[src.id][dest.id]
            except KeyError:
                raise EdgeException("No such edge")
            edge_dict.setdefault(src.id, {})
            res = edge_dict[src.id][dest.id] = cls._Edge(src, dest, credit_limit)
            return res

    @classmethod    
    def print_dicts(cls):
        print "_edge_dict: %s" % cls._edge_dict
        print "_contextual_edge_dicts: %s" % cls._contextual_edge_dicts
        
class Hop(object):
    """
    Hop representation. For each given context, a singleton. The constructor can
    accept both 'Hop' (usually to clone a hop in another context) or 'hop id'.
    """
    _hop_dict = {}
    _contextual_hop_dicts = {}
    class _Hop(object):
        """
        Path hop representation - collection of edges to neighbors
        """
        # This object is not in any way obliged to have edges. Has to be properly filled with list of
        # outgoing edges, before trying to route through it.
        global mao
        edge_list = []
        dist_to_dest = -1       # not determined by default
        
        def __init__(self, hop_id, context = None):
            self.id = hop_id
            self.context = context
            
        def query_and_register_outw_edges(self):
            #if not self.edge_list: # *** was buggy, find out why
            if True:
                neigh_id_list = mao.get_neighbor_list(self.id)
                neigh_list = map(Hop, neigh_id_list, (self.context,)*len(neigh_id_list))
                self.edge_list[:] = map(Edge, (self,)*len(neigh_list), neigh_list)

    @hop_to_id
    def __new__(cls, hop_id, context = None):
        if context is None:
            hop_dict = cls._hop_dict
        else:
            hop_dict = cls._contextual_hop_dicts.setdefault(context, {})
        try:
            return hop_dict[hop_id]
        except KeyError:
            res = hop_dict[hop_id] = cls._Hop(hop_id)
            return res

    @classmethod    
    def print_dicts(cls):
        print "_hop_dict: %s" % cls._hop_dict
        print "_contextual_hop_dicts: %s" % cls._contextual_hop_dicts

    @classmethod
    def register_distance_to_dest(cls, dest, hop_list, reset = False):
        if not reset:
            affected_hop_list = filter(lambda x: x.dist_to_dest < 0, hop_list)
        else:
            affected_hop_list = hop_list
        # result, returned by mao.get_nodes_distances_to_dest is not
        # guaranteed to be sorted in any way; workaround: sort both
        # hop and distance lists by corresponding hop.id, and then
        # combine.
        affected_id_list = map(getattr, affected_hop_list, ('id',)*len(affected_hop_list))

        if affected_id_list:
            id_hop_tuple_list = zip(affected_id_list, affected_hop_list)
        
            id_hop_tuple_list.sort()
            id_dist_tuple_list = mao.get_nodes_distances_to_dest(dest.id, affected_id_list)
            id_dist_tuple_list.sort()

            ordered_hop_list = list(zip(*id_hop_tuple_list)[1])
            ordered_dist_list = list(zip(*id_dist_tuple_list)[1])

            map(setattr, ordered_hop_list, ('dist_to_dest',)*len(ordered_hop_list), ordered_dist_list)
        else:
            ordered_hop_list = []
            ordered_dist_list = []
            
        return zip(ordered_hop_list, ordered_dist_list)
        
class ExploredGraphSegment(object):
    """
    Auxillary storage object which provides temporary storage for path hop and edge candidates.
    The object is tied to particular src_node_id and dest_node_id
    """
    global mao
    edge_storage = {}
    hop_storage = {}
    added_edges_src_dict = {}       # hashmap for indexing edges by source
    added_edges_dest_dict = {}      # hashmap for indexing edges by destination
    edge_id_serial = 0          # integer used to uniquely identify next edge; increased when a new edge is registered;
    
    def __init__(self, src_node_id, dest_node_id):
        self.mao = MetricAccessObject()
        self.mao.synchronize_with_metric_db_table()
        self.src = self.hop_storage[src_node_id] = Hop(src_node_id)
        self.src.query_and_register_outw_edges()
        self.dest = self.hop_storage[dest_node_id] = Hop(dest_node_id)

        
    def reset(self):
        """
        Reset data tables to default values. Warning: names are rebound - old references become obsolete.
        """
        self.edge_storage = {}
        self.node_storage = {}
        self.added_edges_src_dict = {}
        self.added_edges_dest_dict = {}
        self.edge_id_serial = 0

    def adjust_metrics_according_to_path(self, path, affected_contexts_list):
        edge_list = list(zip(*path.hop_edge_sequence)[0])
        contexted_edge_lists = map(Edge, (edge_list,)*len(affected_contexts_list))
        

        
class MetricAccessObject(object):
    # should not use Hop or Edge objects at this level of abstraction; id's instead.
    # *** can probably be a singleton?
    distinct_hops_set = set([])
    metric_cache = {}

    def get_neighbor_list(self, node_id):
        metric_cache_entry = self.metric_cache[node_id]
        return metric_cache_entry.keys()

    def synchronize_with_metric_db_table(self):
        """
        Loads edge metric data from database into self.metric_cache dictionary.
        """
        SQL_GET_METRICS = "SELECT * FROM metrix_table"
        self.metric_cache.clear()
        curs.execute(SQL_GET_METRICS)
        metrics_tuple_list = curs.fetchall()
        self.distinct_hops_set.clear()
        for metric_tuple in metrics_tuple_list:
            self.distinct_hops_set.add(metric_tuple[1])
        for hop in self.distinct_hops_set:
            self.metric_cache[hop] = {}
        while metrics_tuple_list:
            metric_tuple = metrics_tuple_list.pop()
            self.metric_cache[metric_tuple[1]][metric_tuple[2]] = metric_tuple[3]
            
    def get_node_closest_to_dest(self, dest_id, node_list):
        if not node_list: return []
        dest_present = False      # flag, saying whether dest_node is among neighbors - False by default
        if dest_id in node_list:
            return dest_id
        NODE_LIST = "src_node_id = %s" % node_list[0]
        for n in node_list[1:]:
            NODE_LIST = NODE_LIST + " OR src_node_id = %s" % n
        SQL_GET_NODE_CLOSEST_TO_DEST = "SELECT src_node_id FROM routing_table WHERE dest_node_id = %s AND (" % dest_id\
            + "%s) ORDER BY distance ASC LIMIT 1" % NODE_LIST
        #print SQL_GET_NODE_CLOSEST_TO_DEST
        curs.execute(SQL_GET_NODE_CLOSEST_TO_DEST)
        result = curs.fetchone()
        #print "get_node_closest_to_dest: result is %s" % result
        return result[0]

    def get_nodes_distances_to_dest(self, dest_id, node_list):
        # in general, DOES NOT sort the list according to distances
        if not node_list: return []
        dest_present = False      # flag, saying whether dest_node is among neighbors - False by default
        if dest_id in node_list:
            dest_present = True
            node_list.remove(dest_id)
        NODE_LIST = "src_node_id = %s" % node_list[0]
        for n in node_list[1:]:
            NODE_LIST = NODE_LIST + " OR src_node_id = %s" % n
        SQL_GET_NODE_CLOSEST_TO_DEST = "SELECT src_node_id, distance FROM routing_table WHERE dest_node_id = %s AND (" % dest_id\
            + "%s)" % NODE_LIST
        curs.execute(SQL_GET_NODE_CLOSEST_TO_DEST)
        result = curs.fetchall()
        if dest_present: result.append((dest_id, 0))
        return result
    
mao = MetricAccessObject()
mao.synchronize_with_metric_db_table()

STATUS_PATH_NEUTRAL = 0
STATUS_PATH_SUCCESSFUL = 1
STATUS_PATH_EXHAUSTED = 2

class Path(object):
    hop_edge_sequence = []      # stores (curr_hop, next_edge) tuples
    #edge_id_sequence = []      
    status = STATUS_PATH_NEUTRAL
    credit_limit = 0.0
    
class PathScope(object):
    """
    Describes sequence of hops and their outward traversable edges' characteristics
    """
    step_data_sequence = []     # [[(edge1, edge2, ..), (hop1, hop2, ..), (dist1, dist2, ..),\
                                #  (cred_lim1, cred_lim2, ..), (<dist1+step_nr>, <dist2+step_nr>, ..)],..].
    
    def _prune_path_scope_leaf(self):
        # made private - should only be executed within self.process_path_scope
        length = len(self.step_data_sequence)
        last_step_data = self.step_data_sequence[length - 1]
        zip_lsd_list = list(zip(*last_step_data))
        zip_lsd_list.pop(0)
        self.step_data_sequence[length - 1] = list(zip(*zip_lsd_list))

    def worsen_hop_distances(self, step, best_prev_step_dist_value):
        step_data = self.step_data_sequence[step]
        #print "step_data: %s" % step_data
        dist_data = step_data[2]
        step_dist_data = step_data[4]
        dist_data[0] = best_prev_step_dist_value - step
        step_dist_data[0] = best_prev_step_dist_value
        
    def process_path_scope(self):
        self._prune_path_scope_leaf()
        curr_hop_nr = len(self.step_data_sequence) - 1 
        best_prev_step_distance = self.find_best_step_dist_value(curr_hop_nr)
        curr_hop_nr -= 1
        while curr_hop_nr >= 0:
            self.worsen_hop_distances(curr_hop_nr, best_prev_step_distance)
            best_prev_step_distance = self.find_best_step_dist_value(curr_hop_nr)
            curr_hop_nr -= 1
            #print "now list(step_dist data) is: %s" % list(self.step_data_sequence[curr_hop_nr][4])
            
    def find_best_step_dist_value(self, step):
        step_data = self.step_data_sequence[step]
        step_dist_data = step_data[4]
        best_sd_value = min(step_dist_data)
        return best_sd_value

    def get_steps_best_values(self):
        dist_array = map(self.find_best_step_dist_value, xrange(0, len(self.step_data_sequence)))
        return dist_array

    def switch_to_contexted_scope_data(self, nsteps, context):
        """
        Transforms all the Hop data within self.step_data_sequence[:nsteps]:
          - for all hops: hop -> Hop(hop, context)
          - for all edges: edge -> Edge(edge, context)
          - sets hops' attribute 'dist_to_dest' according to self.step_data_sequence[step][2]
        """
        for edge_list, hop_list, dist_list, cr_lim_list, step_dist_list in self.step_data_sequence[:nsteps]:
            edge_list[:] = map(Edge, edge_list, (context,)*len(edge_list))
            hop_list[:] = map(Hop, hop_list, (context,)*len(hop_list))
            map(setattr, hop_list, ('dist_to_dest',)*len(hop_list), dist_list)
            
    def convert_to_path(self):
        """
        Returns Path object corresponding to 'nsteps' slice of PathScope(self) object.
        """
        # 1) take all 0-th hops and edges from step_data_sequence, for all previous
        #    steps NOT including the best_step
        # 2) pick hop and edge from best_step data, having the best (minimum) step_nr + dist_to_dest value
        # 3) that's it, return!

        path = Path()
        
        best_step, best_value = self.get_best_dist_step()

        self.switch_to_contexted_scope_data(best_step, id(path))

        if best_step > 0:            
            same_path_segment_scope_edge_data = map(getitem, self.step_data_sequence[:best_step], (0,)*(best_step))
            same_path_segment_edge_data = map(getitem, same_path_segment_scope_edge_data, (0,)*len(same_path_segment_scope_edge_data))
            same_path_segment_hop_data = map(getattr, same_path_segment_edge_data, ('src',)*(best_step))
            same_path_segment_data = zip(same_path_segment_hop_data, same_path_segment_edge_data)
        else:
            same_path_segment_data = []
               
        best_step_data = self.step_data_sequence[best_step]
        best_step_dist_list = list(best_step_data[4])
        i = best_step_dist_list.index(best_value)
        same_path_segment_data.append((best_step_data[0][i].src, best_step_data[0][i]))
        next_hop = best_step_data[0][i].dest
    
        path.hop_edge_sequence = same_path_segment_data

        new_path_scope = PathScope()
        new_path_scope.step_data_sequence[:] = self.step_data_sequence[:best_step + 1]
        
        return path, next_hop, new_path_scope

    def get_best_dist_step(self):
        steps_best_values = self.get_steps_best_values()
        best_value = steps_best_values[0]
        nsteps = len(steps_best_values)
        for i, val in zip(xrange(len(steps_best_values)), steps_best_values):
            if val > best_value: break
        i -= 1
        return i, best_value
    
class PathSetCr(object):
    found_paths_list = []
    exhausted_paths_list = []
    path_scopes_list = []
    
    def __init__(self, src_node, dest_node):
        """
        Initialize the object
        """
        self.egs = ExploredGraphSegment(src_node, dest_node)
        self.src_node = Hop(src_node)
        self.dest_node = Hop(dest_node)
        self.search_agent = self.cr_search()
        self.hop_edge_registrar = self.cr_register_hops_edges()
        self.traversable_neighbor_explorer = self.cr_find_traversable_neighbor_hop_list()
        self.dist_crlim_sorting_agent = self.cr_arrange_by_cred_lim_within_same_dists()

    @cr_autonext
    def cr_find_next_path(self, max_path_length = 10, max_total_hops = 1000):
        #path = None
        total_hops = 0
        path = Path()
        curr_hop = self.src_node
        path_scope = PathScope()
        while True:
            yield path
            res = (None,)*5
            while res[2] != RESULT_PATH_FOUND:
                res = self.search_agent.send((path, path_scope, curr_hop, max_path_length))
                total_hops += 1
                if total_hops >= 1000: yield RESULT_PATH_GENERATOR_EXHAUSTED
                curr_hop = res[0][1]
            self.found_paths_list.append(path)
            self.path_scopes_list.append(path_scope)
            path_scope.process_path_scope()
            path, curr_hop, path_scope = path_scope.convert_to_path()
            res = (None,)*5
        
    @cr_autonext
    def cr_search(self):
        next_vector, credit_limit, result_flag = (None, 1000000000000000000.0, None)
        while True:
            path, path_scope, curr_hop, max_path_length = yield next_vector, credit_limit, result_flag
            if curr_hop.id == self.dest_node.id:
                path.hop_edge_sequence.append((curr_hop, None))
                path.credit_limit = credit_limit
                path, curr_hop, max_path_length = (curr_hop, credit_limit, RESULT_PATH_FOUND)
                result_flag = RESULT_PATH_FOUND
                continue

            contexted_curr_hop = Hop(curr_hop, id(path)) # create context-bound (current path-bound) clone of the hop
            
            step_nr = len(path.hop_edge_sequence)

            
            contexted_curr_hop.query_and_register_outw_edges()
            
            traversable_neighbor_list = self.traversable_neighbor_explorer.send((path, curr_hop))
            
            context_tr_neighbor_list = map(Hop, traversable_neighbor_list)
            
            
            edge_list, context_tr_neighbor_list = self.hop_edge_registrar.send((path, contexted_curr_hop, context_tr_neighbor_list))

            Hop.register_distance_to_dest(self.dest_node, context_tr_neighbor_list)
            
            
            dist_list = map(getattr, context_tr_neighbor_list, ('dist_to_dest',)*len(context_tr_neighbor_list))
            cred_lim_list = map(getattr, edge_list, ('credit_limit',)*len(edge_list))
            # *** modify the cred_lim_list according to current credit_limit value
            cred_lim_list[:] = map(min, cred_lim_list, (credit_limit,)*len(cred_lim_list))
            
            step_dist_list = map(add, dist_list, (step_nr,)*len(dist_list))
            
            # DONE. implement: sort these lists 1) according to distances; 2) according to cred_limit (within same distances).
            # *** send these lists to PathScope-registering coroutine
            #self.arrange_by_distances.send(edge_list, context_tr_neighbor_list, dist_list, credit_limit, step_dist_list)

            self.dist_crlim_sorting_agent.send((edge_list, context_tr_neighbor_list, dist_list, cred_lim_list, step_dist_list))

            next_vector = zip(edge_list, context_tr_neighbor_list, dist_list, cred_lim_list, step_dist_list)[0]
            credit_limit = path.credit_limit = next_vector[3]
            print "cr_search: credit_limit = %s" % credit_limit

            # *** I'd prefer sending relevant info to path object - let it deal with it... but ok for now :)
            appendable_to_path = (contexted_curr_hop, next_vector[0])
            path.hop_edge_sequence.append(appendable_to_path)

            # and now record this information in path_scope
            path_scope.step_data_sequence.append([edge_list, context_tr_neighbor_list, dist_list, cred_lim_list, step_dist_list])
            result_flag = RESULT_INTERMEDIARY_HOP
            
    @cr_autonext
    def cr_register_hops_edges(self):
        edge_list, traversable_neighbor_list = (None, None)
        while True:
            path, hop, traversable_neighbor_list = yield edge_list, traversable_neighbor_list
            edge_list = map(Edge, (hop,)*len(traversable_neighbor_list), traversable_neighbor_list, \
                                                       (id(path),)*len(traversable_neighbor_list))
            hop.edge_list = edge_list

    @cr_autonext
    def cr_warrant_hops_dists(self):
        """
        Check if specified hops have valid "dist_to_dest attribute".
        If not, provide them with what's stored in routing table.
        """
        hop_list, dist_list = (None, None)
        while True:
            hop_list = yield hop_list, dist_list
            invalid_dist_hops = filter(lambda x: x.dist_to_dest < 0, hop_list)
            
        
            
    @cr_autonext
    def cr_find_traversable_neighbor_hop_list(self):
        traversable_hop_list = None
        while True:
            path, curr_hop = yield traversable_hop_list
            curr_hop_all_neighbors_list = map(getattr, curr_hop.edge_list, ('dest',)*len(curr_hop.edge_list))
            curr_hop_all_neighbors_set = set(curr_hop_all_neighbors_list)
            
            if path.hop_edge_sequence:
                all_traversed_hop_set = set(zip(*path.hop_edge_sequence)[0])
            else:
                all_traversed_hop_set = set([])

            traversable_hop_list = list(curr_hop_all_neighbors_set - all_traversed_hop_set)
            
            
    @cr_autonext
    def cr_arrange_by_distances(self):
        # redundant generator: better see arrange_by_cr_lim_within_same_dists
        edge_list, context_tr_neighbor_list, dist_list, credit_limit, step_dist_list = (None, None, None, None, None)
        while True:
            edge_list, context_tr_neighbor_list, dist_list, credit_limit, step_dist_list\
                = yield edge_list, context_tr_neighbor_list, dist_list, credit_limit, step_dist_list
            aggregate_tuple_list = zip(edge_list, context_tr_neighbor_list, dist_list, credit_limit, step_dist_list)
            aggregate_tuple_list.sort(lambda x,y: cmp(x[2], y[2]))
            edge_list[:], context_tr_neighbor_list[:], dist_list[:], credit_limit[:], step_dist_list[:] = zip(*aggregate_tuple_list)

    @cr_autonext
    def cr_arrange_by_cred_lim_within_same_dists(self):
        # side effect is sorting by distance first! (that's good)
        edge_list, context_tr_neighbor_list, dist_list, credit_limit, step_dist_list = (None,)*5
        while True:
            edge_list, context_tr_neighbor_list, dist_list, credit_limit, step_dist_list\
                = yield edge_list, context_tr_neighbor_list, dist_list, credit_limit, step_dist_list
            dset = set(dist_list)
            dvalues = list(set(dist_list))
            dvalues.sort()
            aggregate_list = zip(edge_list, context_tr_neighbor_list, dist_list, credit_limit, step_dist_list)
            cp = 0              # current position in list
            sorted_aggregate_list = []
            for d in dvalues:
                aggregate_slice = filter(lambda x: x[2] == d, aggregate_list)
                aggregate_slice.sort(lambda x, y: cmp(x[3], y[3]), reverse = True)
                map(sorted_aggregate_list.append, aggregate_slice)
            edge_list[:], context_tr_neighbor_list[:], dist_list[:], credit_limit[:], step_dist_list[:] = zip(*sorted_aggregate_list)
            
    


    

    

###################################################################################################
###### -------------------------------OBSOLETE (non-coroutine)------------------------------ ######
###################################################################################################

class PathSet(object):
#    list_of_successful_paths = []
#    list_of_exhausted_paths = []
    def __init__(self, src_node, dest_node):
        """
        Initialize the object
        """
        self.egs = ExploredGraphSegment(src_node, dest_node)
        self.src_node = Hop(src_node)
        self.dest_node = Hop(dest_node)

    #def path_to_path_segment(self, path):
    #    pass
        
    def find_path(self, max_path_length):
        print "Pathset.find_path(): now starting the search"
        path = Path()
        path_scope = PathScope()
        curr_hop = Hop(self.src_node)
        #path.hop_sequence.append(curr_hop)
        path_explorer = self.search(path, max_path_length, path_scope)
        while True:
            res = path_explorer.next()
            if res == RESULT_PATH_FOUND or res == RESULT_NODE_EXHAUSTED:
                print "got the result %s" % res
                break
        print zip(path.hop_edge_sequence)
        res =  map(getattr, zip(*path.hop_edge_sequence)[0], ('id',)*len(path.hop_edge_sequence))
        #print "path.hop_sequence[1].id = %s" % path.hop_sequence[1].id
        print "res = %s" % res
        print path.credit_limit

        ##### SOME PLAY HERE - the part below of the function doesn't influence anything
        #print "And now some play with path_scope:"
        #print "path_scope.step_data_sequence before add_step_dist_data:"
        #print path_scope.step_data_sequence

        path_scope.add_step_dist_data()
        path_scope.prune_path_scope_leaf()

        print "\n\nlen(path_scope.step_data_sequence): %s" % len(path_scope.step_data_sequence)
        #print "\n\npath_scope.step_data_sequence:"
        #print path_scope.step_data_sequence
        
        curr_hop_nr = len(path_scope.step_data_sequence) - 2 # *** just won't work if it's shorter than 2 elems :) - check
        
        while curr_hop_nr >= 0:
            best_prev_distance = path_scope.find_best_step_dist_value(curr_hop_nr + 1)
            path_scope.worsen_hop_distance(curr_hop_nr, best_prev_distance)
            curr_hop_nr -= 1
        
        dist_array = map(path_scope.find_best_step_dist_value, xrange(0, len(path.hop_edge_sequence) - 1))

        print "dist_array: %s" % dist_array

        dist_array_2 = path_scope.get_steps_best_values()
        print "dist_array_2: %s" % dist_array_2

        new_path = path_scope.convert_to_path()
        print "\n\nnew_path:"
        print new_path
        print "\n\nnew_path.hop_edge_sequence:"
        print new_path.hop_edge_sequence
        
        #print "path_scope.step_data_sequence after add_step_dist_data:"
        #print path_scope.step_data_sequence
#         print "And now the 'path' object contents:"
#         print "\n----------------------------------"
#         print "path.__dict__:\n"
#         print path.__dict__
#         print "\n----------------------------------"
#         print "dir(path):\n"
#         print dir(path)
#         #print "\n----------------------------------"
#         #print "path.__class__.__dict__:\n"
#         #print path.__class__.__dict__
#         print "\n----------------------------------"
#         print "path.hop_sequence contents:\n"
#         print path.hop_edge_sequence
        #Edge.print_dicts()
        #Hop.print_dicts()
        
        
    def search(self, path, max_path_length, path_scope):
        # register the current hop with traversable edges within given Path object
        # ask sort_hops_edges for advice on which edge to take;
        curr_hop = self.src_node
        credit_limit = None
        while 1:
            #print "path: %s" % map(getattr, path.hop_sequence, ('id',)*len(path.hop_sequence))
            if curr_hop.id == self.dest_node.id:
                path.hop_edge_sequence.append((curr_hop, None))
                path.credit_limit = credit_limit
                yield RESULT_PATH_FOUND
                break
            else:
                contexted_curr_hop = Hop(curr_hop, id(path)) # create context-bound (current path-bound) clone of the hop
                
                curr_hop_all_neighbors_list = map(getattr, curr_hop.edge_list, ('dest',)*len(curr_hop.edge_list))
                curr_hop_all_neighbors_set = set(curr_hop_all_neighbors_list)

                if path.hop_edge_sequence:
                    all_traversed_hop_set = set(zip(path.hop_edge_sequence)[0])
                else:
                    all_traversed_hop_set = set([])

                traversable_neighbor_set = curr_hop_all_neighbors_set - all_traversed_hop_set
                traversable_neighbor_list = list(traversable_neighbor_set)
                
                contexted_curr_hop.edge_list = map(Edge, (curr_hop,)*len(traversable_neighbor_list), traversable_neighbor_list, \
                                                       (id(path),)*len(traversable_neighbor_list))

                # *** since anyway required, perhaps give this argument to new_sort_hops_edges
                neighbor_hops = map(getattr, contexted_curr_hop.edge_list, ('dest',)*len(contexted_curr_hop.edge_list))

                self.egs.query_and_set_hops_distances(neighbor_hops)

                # *** work out the case when the returned result is empty list!
                sorted_aggregate_tuple_list = zip(*self.new_sort_hops_edges(contexted_curr_hop.edge_list))
                sorted_edge_list, sorted_hop_list, dist_list, cred_limit_list = map(list, sorted_aggregate_tuple_list)

                path_scope.step_data_sequence.append(sorted_aggregate_tuple_list)
                
                try:
                    next_hop = sorted_hop_list[0]
                    print next_hop.id
                except:
                    path.edge_hop_sequence.append((contexted_curr_hop, None))
                    yield RESULT_NODE_EXHAUSTED # no more edges here
                    break

                curr_edge = Edge(contexted_curr_hop, next_hop, context = id(path))
                path.hop_edge_sequence.append((contexted_curr_hop, curr_edge))

                if credit_limit is not None:
                    credit_limit = min(credit_limit, curr_edge.credit_limit)
                else:
                    credit_limit = curr_edge.credit_limit
                
                curr_hop = Hop(next_hop, None)  # current hop is fine, so rebind this name to 'None' context object, for the next iteration
                curr_hop.query_and_register_outw_edges()
                yield RESULT_INTERMEDIARY_HOP

    #def sort_hops_edges(self, hop_list):
    #    temp, dummy = sort_objects_by_attr('dist_to_dest', hop_list)
    #    # now sort all the objects with best distance value by credit_limit
    #    return temp

    def new_sort_hops_edges(self, edge_list):
        if not edge_list: return []
        hop_list = map(getattr, edge_list, ('dest',)*len(edge_list))
        dist_list = map(getattr, hop_list, ('dist_to_dest',)*len(hop_list))
        cred_limit_list = map(getattr, edge_list, ('credit_limit',)*len(edge_list))
        aggregate_list = zip(edge_list, hop_list, dist_list, cred_limit_list)
        aggregate_list.sort(lambda x, y: cmp(x[2], y[2]))
        best_distance = aggregate_list[0][2]
        dist_list = list(zip(*aggregate_list)[2])
        aggregate_sublist = aggregate_list[0:dist_list.count(best_distance) - 1]
        aggregate_sublist.sort(lambda x, y: cmp(x[3], y[3]), reverse = True)
        return aggregate_list
#    def find_path_coroutine(self, max_path_length):
        
    
def sort_objects_by_attr(attr, object_list, in_place = True):
    """
    attr, object_list -> object_list
    Sorting (in place) by attribute utility function.
    """
    #print type(attr)
    attr_list = map(getattr, object_list, (attr,)*len(object_list))
    attr_obj_tuple_list = zip(attr_list, object_list)
    attr_obj_tuple_list.sort()
    temp = zip(*attr_obj_tuple_list)
    obj_list = list(temp[1])
    attr_list = list(temp[0])
    if in_place:
        object_list[:] = obj_list[:]
    else:
        object_list = obj_list
    return object_list, attr_list






            
#     def add_edge(self, src, dest, credit_limit):
#         temp_edge_ref = self.edge_storage[self.edge_id_serial] = Edge(src, dest, credit_limit)
#         self.added_edges_src_dict.setdefault(src, set([]))
#         self.added_edges_src_dict[src].add(temp_edge_ref)
#         self.added_edges_dest_dict.setdefault(dest, set([]))
#         self.added_edges_dest_dict[dest].add(temp_edge_ref)
#         self.edge_id_serial += 1

    #def register_hop(self, hop_id):
    #    temp_hop_ref = self.hop_storage[hop_id] = Hop(hop_id)
        #temp_hop_ref.register_edges(edge_set)
        #self.edge_id_serial += 1


#     def suggest_next_edge(self, curr_hop, shortest_path = False):
#         """
#         suggest_next_edge(curr_hop [,shortest_path = False]) -> Edge

#         Return Edge, which is the best to follow from curr_hop, based on certain metrics
#         (currently - available credit limit). If shortest_path == True, though, returns
#         the edge to follow if shortest path needed.
#         """
#         if shortest_path:
#             # examine the routing table; return next edge to follow for the shortest path
#             #print "suggest_next_edge: curr_hop.id = %s" % curr_hop.id
#             #print "suggest_next_edge: self.dest.id is %s" % self.dest.id
#             #print "suggest_next_edge: map = %s" % map(getattr, curr_hop.edge_list, ('dest',)*len(curr_hop.edge_list))
#             #print "suggest_next_edge: curr_hop.edge_list = %s" % curr_hop.edge_list
#             next_edge_id = mao.get_node_closest_to_dest(self.dest.id, map(getattr, curr_hop.edge_list, ('dest',)*len(curr_hop.edge_list)))
#             next_edge = Edge(curr_hop.id, next_edge_id)
#             return next_edge
#         # make a list of tuples that include edge credit limit and edge object itself;
#         # find edge with maximum credit limit
#         aux_edge_list = map(None, map(getattr, curr_hop.edge_list, ('credit_limit',)*len(curr_hop.edge_list)))
#         #print "suggest_next_edge: aux_edge_list is: %s" % aux_edge_list
#         return min(aux_edge_list)[1]


#    def search(self, path, )
        
    # def search(self, path_storage, credit_limit_storage, max_path_length):
#         """
        
#         """
#         # * queries path hop metrics from ExploredGraphSegment;
#         # * in case a path is found or exhausted - reports to ExploredGraphSegment; possibly, reserving some credit
#         curr_hop = self.src_node
        
#         while 1:
#             print "PathSet.search(): curr_hop.id = %s" % curr_hop.id
#             next_edge = self.egs.suggest_next_edge(curr_hop, shortest_path = True)
#             #print "PathSet.search(): next_edge = %s" % next_edge
#             path_storage.append(next_edge)
#             credit_limit_storage[0] = min(credit_limit_storage[0], next_edge.credit_limit)
#             curr_hop = Hop(next_edge.dest)
#             curr_hop.query_and_register_outw_edges()
#             self.egs.register_hop(next_edge.dest)
#             #print "PathSet.search(): self.egs.hop_storage[next_edge.dest].id = %s" % self.egs.hop_storage[next_edge.dest].id
#             #print "PathSet.search(): self.dest_node.id = %s" % self.dest_node.id
#             #print "PathSet.search(): path_storage id map = %s" % map(getattr, path_storage, ('src',)*len(path_storage))
#             print "curr_hop.id = %s" % curr_hop.id
#             if curr_hop.id == self.dest_node.id:
#                 path_hop_ids = map(getattr, path_storage, ('src',)*len(path_storage))
#                 path_hop_ids.append(self.dest_node.id)
#                 print "path found: %s" % path_hop_ids
#                 yield RESULT_PATH_FOUND
#             else:
#                 yield RESULT_INTERMEDIARY_HOP


#     def add_step_dist_data(self):
#         """
#         Adds step_nr + dist_to_dest to step_data_sequence entries
#         """
#         # print
# #         print "zip(xrange(len(self.step_data_sequence)), self.step_data_sequence):"
# #         #print zip(xrange(len(self.step_data_sequence)), self.step_data_sequence)
# #         print

# #         print "self.step_data_sequence:"
# #         print self.step_data_sequence
# #         print
        
#         for step_nr, step_data in zip(xrange(len(self.step_data_sequence)), self.step_data_sequence):
#             # print
# #             print "step_data:"
# #             print step_data
# #             print
# #             print "zip(*step_data):"
# #             print zip(*step_data)
# #             print
#             characteristics_tuples_list = step_data #list(zip(*step_data)) #### *** DEBUGGING MESS - SOLVE
#             # print
# #             print "characteristics_tuples_list:"
# #             print characteristics_tuples_list
# #             print
#             dist_tuple = characteristics_tuples_list[2]
#             # print
# #             print "dist_tuple:"
# #             print
# #             print dist_tuple
#             step_dist_tuple = tuple(map(add, dist_tuple, (step_nr,)*len(dist_tuple)))
#             characteristics_tuples_list.append(step_dist_tuple)
#             #self.step_data_sequence = zip(*characteristics_tuples_list)
#             self.step_data_sequence[step_nr] = characteristics_tuples_list #### *** DEBUGGING MESS - SOLVE


        ## Moved to Hop classmethod
#     def query_and_set_hops_distances(self, hop_list):
#         #print "hop_list: %s" % hop_list
#         if not hop_list: return
#         hops_w_undet_dist_to_dest_list = filter(lambda x: x.dist_to_dest < 0, hop_list)
#         hop_id_list = map(getattr, hops_w_undet_dist_to_dest_list, ('id',)*len(hops_w_undet_dist_to_dest_list))
#         hop_id_and_hop_list = zip(hop_id_list, hops_w_undet_dist_to_dest_list)
#         hop_id_and_hop_list.sort()

#         if not hop_id_and_hop_list: return
        
#         hop_id_dist_tuple_list = mao.get_nodes_distances_to_dest(self.dest.id, hop_id_list)
#         hop_id_dist_tuple_list.sort()        

#         #print "hop_id_and_hop_list = %s" % hop_id_and_hop_list
        
#         # get temp1 - distinct sorted (on hop_id) list of hop objects and temp2 - distinct sorted (on hop_id) metric list
#         temp1 = list(zip(*hop_id_and_hop_list)[1])
#         temp2 = list(zip(*hop_id_dist_tuple_list)[1])

#         #print "query_and_set_hops_distances: we have:"
        
#         #print "hop_id_dist_tuple_list = %s" % hop_id_dist_tuple_list
        
#         #print "query_and_set_hops_distances: we get:"
#         #print "temp1 = %s" % temp1
#         #print "temp2 = %s" % temp2
        
#         # finalize - set the 'dist_to_dest' attribute
#         map(setattr, temp1, ('dist_to_dest',)*len(temp1), temp2)

#     def worsen_hop_distance(self, step, prev_best_step_distance):
#         print "whd: prev_best_step_distance = %s" % prev_best_step_distance
#         step_data = self.step_data_sequence[step]
#         step_data_list = list(step_data)
        
#         #print "\n\nwhd: type(step_data) is %s, list(step_data) is:\n%s" % (type(step_data), list(step_data))
        
#         zip_lsd_list = list(zip(*step_data))
#         hop_data = zip_lsd_list[0]
#         zip_lsd_list[0] = (hop_data[0], hop_data[1], prev_best_step_distance - step, hop_data[3], prev_best_step_distance)

#         tuple_list = list(zip(*zip_lsd_list))
#         new_lists = map(list, tuple_list)

#         for lst, nlst in zip(step_data, new_lists):
#             print "lst is: %s" % lst
#             print "nlst is: %s" % nlst
#             lst[:] = nlst[:]
            

#         print "whd: new lists[4] is:\n%s\n" % new_lists[4]

#         #map(setitem, self.step_data[:])
        
#         #self.step_data_sequence[step][:] = new_lists[:]
