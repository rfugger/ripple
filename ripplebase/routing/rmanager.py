"""
Module for performing routing operations. For now:
  # - routing table is stored in memory.
  - routing table is stored in database
Future versions could support work with persistent storage.
"""
import thread
from psycopg import connect, ProgrammingError   # current implementation uses DBAPI for DB access
from routing.smallworld import get_neighbors, ids


class RoutingTableEx(Exception):
    pass

# Database tables model & connection information
ROUTING_DB_CONNECT_STR = "dbname=routing_dev_db user=dev password=devdevdev host=localhost"
# connect to the routing DB and clear the tables
try:
    conn = connect(ROUTING_DB_CONNECT_STR)
    curs = conn.cursor() # connect to the routing table storage database
except:
    raise RoutingTableEx(e)
conn.autocommit()

DROP_NODES_TABLE_STATEMENT = """
DROP TABLE nodes_table
"""
DROP_ROUTING_TABLE_STATEMENT = """
DROP TABLE routing_table
"""
CLEAR_NODES_TABLE_STATEMENT = """
DELETE FROM nodes_table
"""
CLEAR_ROUTING_TABLE_STATEMENT = """
DELETE FROM routing_table
"""
CREATE_NODES_TABLE_STATEMENT = """
CREATE TABLE nodes_table(
    id int4 PRIMARY KEY,
    routing_id varchar(10) UNIQUE
)
"""
# no foreign key constraint checked - due to performance issues
CREATE_ROUTING_TABLE_STATEMENT = """
CREATE TABLE routing_table(
    id bigserial PRIMARY KEY,
    src_node_id int4,
    dest_node_id int4,
    distance int4
)
"""
# *** CREATE INDEX for src_node_id and dest_node_id - very significant performance improvement
#     for the pathfinder


# *** Ryan: Can we do this in-memory, or should we use db?  space = O(n^2)
#           Ah, fcn calls allow for that.  Great.
# _routingTable = {}

# Create a lock for thread synchronization
# *** Ryan: When do multiple threads operate on routing table?
#           What happens to accessors when new table is being computed?
#           Won't routing table be in db?  (Would use transactions in that case.)
#           Probably better to do with cron job in separate process.
# *** Jevgenij: in our release version, routing table will indeed have to be stored 
#           in db; also, it is good if only computation cron job has write access
#           to routing table. 
#           Another thought is: it is prudent to eventually allow 
#           routing table computation in several parallel threads (manually 
#           adjustable number) - to take advantage of multiprocessor server systems
#           for this CPU-intensive job.
#
# _synLock = thread.allocate_lock()

def prepare_tables():
    #try:
    global conn, curs
    if True:
        try:
            curs.execute(CLEAR_NODES_TABLE_STATEMENT)    # try to delete contents of nodes_table
        except ProgrammingError:    # corresponds to "No relation nodes_table" error - the table does not exist
            curs.execute(CREATE_NODES_TABLE_STATEMENT)    # create nodes_table
            try:
                curs.execute(DROP_ROUTING_TABLE_STATEMENT)    # Attempt to drop routing_table, if it exists
            except:
                pass    # the table does not exist - that's good, so we just pass
            curs.execute(CREATE_ROUTING_TABLE_STATEMENT)
        finally:
            try:
                curs.execute(CLEAR_ROUTING_TABLE_STATEMENT)
            except ProgrammingError:
                curs.execute(CREATE_ROUTING_TABLE_STATEMENT)
        conn.commit()
#    except:
#        conn.rollback()
#        raise RoutingTableEx
    
def populate_nodes_table(idList):
    global curs
    if not idList: return # the list is empty - there is nothing to do
    addNodeStatement = "INSERT INTO nodes_table(id, routing_id) VALUES " 
    for id in idList:
        addNodeStatement = addNodeStatement + "(%d, 'node_%d')," % (id, id) # *** can be comparatively slow
    stLength = len(addNodeStatement)
    addNodeStatement = addNodeStatement[:stLength-1] # remove trailing comma
    curs.execute(addNodeStatement)
#def create_routing_table():
#    """
#    Create routing_table. in DB. This function is used in two branches of table 
#    initialization logic, so exists for convenience.
#    """
    

def add_distance(nodeID, otherNodeIDs, distance):
    """
    A handy method for updating routing table nested dictionary.
    Takes current node ID and list/set of other nodes', that have fixed distance 'distance'
    from the current node, IDs.  
    """
    global curs
    # debug:
    # print "rmanager.add_distance(): nodeID: %s, otherNodeIDs: %s,\n\ndistance: %s" % (nodeID, otherNodeIDs, distance)
    # 1) check if 'nodeID' is present in the table; if no, create it;
    # Ryan: Use setdefault here.
    # Jevgenij: I agree, corrected
# ------------- changing this to DB storage ----------------
#    _routingTable.setdefault(nodeID, {})
#    # 2) update the inner dict
#    for onID in otherNodeIDs:
#        _routingTable[nodeID].update({onID: distance})
# -----------------------------------------------------
    if not otherNodeIDs: return # the list is empty - there is nothing to do
    addDistanceStatement = "INSERT INTO routing_table(src_node_id, dest_node_id, distance) VALUES " 
    for onID in otherNodeIDs:
        addDistanceStatement = addDistanceStatement + "(%s, %s, %d)," % (nodeID, onID, distance) # *** can be comparatively slow
    stLength = len(addDistanceStatement)
    addDistanceStatement = addDistanceStatement[:stLength-1] # remove trailing comma
    #try:
    curs.execute(addDistanceStatement)
    #except:
    #raise RoutingTableEx
        
# *** Ryan: Why pass in fcns here?  In the regular course of the program, 
#           will there be different ones passed in?  If not, why not just
#           call the canonical one, wherever it lives?
def refresh_routing_table(get_ids_fn, get_neighbors_fn):
    """
    Refresh routing table. Takes a graphObject, which must have get_neighbors(self, id)
    method, to provide list of adjacent nodes.
    'waitflag' defines behavior in case _synLock is locked. If True, RoutingTableLockEx
    is raised. If False, waits until the lock gets unlocked.
    If get_neighbors() causes IndexError, it is passed further.
    _routingTable is a dictionary of dictionaries of form:
        
        _routingTable = {
            ...
            <nodeID>: {<otherNodeID>: <shortestPathLength>}
            ...
        }
    ----    
    The algorithm performs Breadth-First-Search (BFS) graph traversal for every node 
    (as initial) of the graph. It uses "black", "white", "grey" and "all white neighbor" 
    sets of nodes:
        - "black" set contains nodes with no unvisited neighbors;
        - "white" set contains unvisited nodes;
        - "grey" set contains visited nodes, which have unvisited neighbors;
        - "all white neighbor" set contains all white neighbors of currently "grey"
          nodes - this set will be copied into "grey" in the end of each iteration.
    After choosing the initial node, it is put into "grey" set. "white" set
    contains all the remaining nodes, and "black" set is empty.
    While "grey" set contains nodes:
        1) for every node on the "grey" set:
            i) find its "white" neighbors;
            ii) move them to "all white neighbor" set;
        2) append all "grey" nodes to "black" set;
        3) put "all white neighbor" nodes into "grey" set
    
    The algorithm is something like: 
    http://www.boost.org/libs/graph/doc/breadth_first_search.html
    """
    # *** Ryan: What is the algorithm?  Document.
    # Jevgenij: done. Hope the documentation is enough comprehensive   
           
#    # first, acquire the lock
#    if _synLock.acquire(waitflag) != 1:
#        raise RoutingTableLockEx("RoutingManager.refresh_routing_table(): Unable to acquire lock")
    _routingTable = {}
    prepare_tables()
    # *** perhaps, should validate the adjacency list here???
    # retrieve the list of nodes in graph
    nodeList = get_ids_fn()
    populate_nodes_table(nodeList)
    
    # *** Ryan: Why go through every node recreating the whole table?  
    #           Shouldn't we just start at nodes that have gained or lost an edge since the last
    #             refresh, and propagate changes outward from there, stopping when we aren't changing 
    #             anything anymore?
    # *** Jevgenij: incremental approach is indeed better if just one or two edges appear. Recalculating
    #             from scratch can be useful too, e.g. to recover from failures.
    for node in nodeList:
        # set initial white, grey and black sets
        # *** Ryan: What are these?  Document.
        # Jevgenij: done.
        _greySet = set([node])
        # _whiteSet = set([])
        _whiteSet = set(nodeList[:])
        _whiteSet.discard(node)
        _blackSet = set([])
        # traverse every other reachable node, registering minimum distance to it 
        # (white-grey-black coloring)
            
        distance = 0
        while True:
            # checking if greySet contains values
            if not _greySet: 
                break          
            # assemble a union of 'white' neighbors, which will be then 'repainted' in 'grey'
            distance += 1
            allWhiteNeighbors = set([])
            for greyNode in _greySet:
                neighbors = set(get_neighbors_fn(greyNode)) # get list of all immediate neighbors
                # *** Ryan: Use python 'set' primitive below
				# *** Jevgenij: yes, use sets! has to be reworked.
                # *** Jevgenij: Done.
                whiteNeighbors = _whiteSet & neighbors # leave only neighbors that are 'white' (intersection of sets)
                allWhiteNeighbors.update(whiteNeighbors) # append the new white neighbors to allWhiteNeighbors set
            
            _blackSet.update(_greySet) # 'repaint' 'grey' nodes in 'black'
            _greySet = allWhiteNeighbors.copy() # 'repaint' 'white' neighbors in grey
            for whiteNode in allWhiteNeighbors:
                _whiteSet.discard(whiteNode)
                
            add_distance(node, allWhiteNeighbors, distance)

def close_db_conn():
    conn.close()

#    # release the lock
#    _synLock.release()
    # debug - print the routing table
    # print "\nRouting table:\n%s" % self._routingTable

# *** Ryan: Does app need whole table, or just one node's portion at a time?
# Jevgenij: apparently, several nodes that take part in the transaction is enough
# *** - rework
#def get_table():
#    # *** Ryan: If we can't fit table in memory, certainly can't fit multiple copies.
#    return _routingTable.copy()
    
####def find_optimal_path(self, sourceID, destinationID, waitflag = 0):
####    """
####    Find optimal path between nodes 'sourceID' and 'destinationID'. Returns
####    list of nodes to be traversed from source to destination. Empty list if
####    no route exists. Raise an exception if sourceID == destinationID.
####    'waitflag' defines behavior in case _synLock is locked. If True, RoutingTableLockEx
####    is raised. If False, waits until the lock gets unlocked.
####    """
####    # first, acquire the lock
####    if not self._synLock.acquire(waitflag):
####        raise RoutingTableLockEx("RoutingManager.find_optimal_path(): Unable to acquire lock")
####    # release the lock
####    self._synLock.release()
####def getDiam(self):
####    """
####    Get the diameter of graph corresponding to _routingTable
####    """
####def nodeCount(self):
####    """
####    Return how many nodes the graph has
####    """

def incremental_add_edge(nodeID1, nodeID2):
    # 1) check the nodes in the nodes_table
    # 2) issue an update statement to update routing table entries 
    #    with min(distance, d11 + d22 + 1, d12 + d21 + 1)
    ROUTING_TABLE_UPDATE_ON_ADD_EDGE_STATEMENT ="""
        UPDATE routing_table SET distance TO min(distance, )
    """
     