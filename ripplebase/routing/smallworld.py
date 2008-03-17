"""
Small World information provision module
"""
class InvalidGraphEx(Exception):
    pass

"""
The graph knowledge is in _swGraph adjacency list, of
the form:
_swGraph = [
    [<first node's neighbor 1>, <first node's neighbor 2>, ..., <first node's neighbor n1>],
    [<second node's neighbor 1>, <second node's neighbor 2>, ..., <second node's neighbor n2>],
    ...,
    [<m'th node's neighbor 1>, <m'th node's neighbor 2>, ..., <m'th node's neighbor nm>]
]
"""

swGraph = {}
def get_neighbors(id):
    """
    Returns the list of id'th node's neighbors
    Exceptions: will pass raised IndexError if no element with index id is present
    """
    global swGraph
    temp = swGraph[id]
    return temp

def nodes_count():
    """
    Returns number of nodes with non-empty corresponding entries in adjacency list
    """
    pass
    
def ids():
    """
    Returns list of ids of nodes with non-empty corresponding entries in adjacency list
    """
    global swGraph
    allIDs = swGraph.keys()
    #print "smallworld.py, ids(): _swGraph is: %s" % swGraph
    #print "smallworld.py, ids(): allIDs = %s" % allIDs
    return filter(lambda x: swGraph[x] != [], allIDs)

def maxId():
    """
    Returns maximum node id with non-empty corresponding entry in adjacency list
    """
    pass
def appendNodes(nodesDict):
    """
    WARNING: NO CHECK OF NEIGHBORING NODE PRESENCE IS PERFORMED (yet?)
    Appends nodes listed in nodesDict to _swGraph. nodesDict format:
    nodesDict = {
        '<node id>': [<list of neighbor nodes>],
        ...
    }
    """
    pass
    
def appendEdges(id, edges):
    """
    Add 'edges' to node 'id' neighbors
    """
    pass
    
def deleteEdges(id, edges):
    """
    Delete 'edges' from node's 'id' neighbors
    """
    pass

def deleteNodes(nodeIds):
    """
    WARNING: NO CHECK OF NEIGHBORING NODE PRESENCE IS PERFORMED (yet?)
    Replaces neighbor lists (in _swGraph) corresponding to node ids in 
    'nodeIds' with empty lists.
    """
    pass
def populate_sw(adjTable, validate = True):
    """
    Copies adjTable dictionary into _swGraph after performing validation
    Will pass GraphInvalid exception in case of invalid graph
    """
    global swGraph
    #print "smallworld.populate_sw(): adjTable is: %s" % adjTable
    if validate:
        validate_graph(adjTable)
    #print "smallworld.populate_sw(): _swGraph before assignment is: " % swGraph
    swGraph = adjTable.copy()
    #print "smallworld.populate_sw(): _swGraph is: %s" % swGraph
    #print "smallworld.populate_sw(): _swGraph.keys() is: %s" % swGraph.keys()
    
def validate_graph(graph):
    """
    Check if graph is valid (e.g. there are no references to nonexistent nodes).
    Directional edges allowed.
    *** NOTE: perhaps should also check:
        - if negative value supplied (could this be dangerous in certain cases?);
        - if lists an entry itself among its neighbors.
    """
    #print "%s" % graph
    # maxNode = len(graph)
    try:
        for node in graph.keys():
            #print "%s" % node
            if len(graph[node]) != 0:
                for neighbor in graph[node]:
                    graph[neighbor]
    except IndexError, e:
        raise InvalidGraphEx(e) # neighbor does not exist
    except TypeError, e:
        raise InvalidGraphEx(e) # neighbor entry has invalid type, or neighbors' list 
    except KeyError, e:
        raise InvalidGraphEx(e) 
    