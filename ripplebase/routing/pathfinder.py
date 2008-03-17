from psycopg import connect
from routing.rmanager import ROUTING_DB_CONNECT_STR

class PathFinderEx(Exception):
    pass

class PathFinderNoEntryEx(Exception):
    pass

# transaction start and commit statements
# *** check with manual on postgres concurrency, how this will actually work
SQL_START_TRANS = "START TRANSACTION"
SQL_COMMIT_TRANS = "COMMIT TRANSACTION"
SQL_ROLLBACK_TRANS = "ROLLBACK TRANSACTION"

# connect to the routing DB
try:
    conn = connect(ROUTING_DB_CONNECT_STR)
    curs = conn.cursor() # connect to the routing table storage database
except:
    raise RoutingTableEx(e)
conn.autocommit()

def find_shortest_path(src_node_id, dest_node_id):
    """
    Issues a series of queries to the DB, to find:
      - the length of shortest path between src_node_id and dest_node_id;
      - the nodes - "milestones" of the shortest path;
      - the sequence of traversing the nodes.
    WARNING! INPUT INVALIDATED!!! - *** to be fixed (SQL_GET_DISTANCE, SQL_GET_MILESTONES)
    """
    global conn, curs

    # check if source and destination coincide; return 0 and empty path if they do
    if src_node_id == dest_node_id: return 0, []    
    
    # begin a transaction - work on a database snapshot
    curs.execute(SQL_START_TRANS)
    
    # issue SQL statement to fetch distance between source and destination 
    SQL_GET_DISTANCE = "SELECT distance FROM routing_table WHERE src_node_id = %s AND dest_node_id = %s" %\
        (src_node_id, dest_node_id)
    try:
        curs.execute(SQL_GET_DISTANCE)
        distance = curs.fetchone()[0]
    except:
        curs.execute(SQL_ROLLBACK_TRANS)
        raise PathFinderNoEntryEx("No appropriate DB entry")
    
    # check the distance for validity
    try:
        if distance != int(distance): raise
        if distance < 1: raise
    except:
        curs.execute(SQL_ROLLBACK_TRANS)
        raise PathFinderEx("Fetched distance is not integer or non-positive - routing DB damaged!")
    
    # if distance == 1
    if distance == 1: 
        
        return 1, [[src_node_id, dest_node_id]]
    
    #print "%s" % distance
    
    # distance > 1 -- there is some work to do, hey...
    hopsIterator = xrange(1, distance)        # will iterate through the milestones
    curr_node_id = src_node_id
    path = []
    # iteratively, i = 1..distance-1:
    #   -- take a (current) hop;
    #   -- find a routing_table entry, which is 1 hop away from current hop and <distance - i> away
    #      from dest_node_id
    #   -- return
    for i in hopsIterator:
        #print "i = %s" % i
        SQL_FIND_NEXT_HOP = "SELECT hop_id FROM" \
                            + " (SELECT dest_node_id AS hop_id FROM routing_table" \
                            + " WHERE src_node_id = %s" % curr_node_id \
                            + " AND distance = 1) AS source_part JOIN" \
                            + " (SELECT src_node_id AS hop_id FROM routing_table" \
                            + " WHERE dest_node_id = %s" % dest_node_id \
                            + " AND distance = %s) AS dest_part" % (distance - i) \
                            + " USING (hop_id) LIMIT 1"  # finds first suitable node
        curs.execute(SQL_FIND_NEXT_HOP)
        #print "%s" % SQL_FIND_NEXT_HOP
        try:
            next_node_id = curs.fetchone()[0]
        except TypeError:
            raise PathFinderEx("Failed to fetch next hop!")
        
        path.append([curr_node_id, next_node_id])
        curr_node_id = next_node_id
    
    path.append([curr_node_id, dest_node_id])
    curs.execute(SQL_COMMIT_TRANS)
    
#    # just get the points, through which it's possible to travel 'distance' hops from source to
#    # destination. Not of a big practical use here.
#    SQL_GET_MILESTONES = "SELECT rt1.pathpoint_id FROM (SELECT src_node_id, dest_node_id AS pathpoint_id, distance" + \
#        " FROM routing_table) AS rt1 JOIN (SELECT src_node_id AS pathpoint_id, dest_node_id, distance" +\
#        " FROM routing_table) AS rt2 ON (rt1.src_node_id = %s AND rt2.dest_node_id = %s"\
#        % (src_node_id, dest_node_id) +\
#        " AND rt1.pathpoint_id = rt2.pathpoint_id) WHERE rt1.distance+rt2.distance <= %d"\
#        % distance
    
#    curs.execute(SQL_GET_MILESTONES)
#    milestones = curs.fetchall()
    
    return distance, path

def shutdown():
    """
    Shutdown pathfinder module. Essentially, close DB connection.
    """
    global conn
    conn.close()