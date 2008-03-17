"""
Unit test suite for Path Finder find_shortest_path() function (routing.pathfinder.py)
"""
from twisted.trial import unittest
from psycopg import connect

from routing.pathfinder import find_shortest_path
from routing.rmanager import ROUTING_DB_CONNECT_STR


conn = connect(ROUTING_DB_CONNECT_STR)
curs = conn.cursor()
conn.autocommit()

class FindShortestPathTestSuite(unittest.TestCase):
    def setUp(self):
        pass
    
    def testFSPNormal(self):
        """
        Bunch of tests that check "normal" behaviour of the function (correct inquiry, correct data).
        """
        global conn, curs
        # 1) Supply random src_node_id != dest_node_id, so that the path is at least MIN_DIST) 
        # nodes long. Verify that :
        #   -- check if distance is found correctly;
        #   -- for each path segment, check if end node of the current segment is the start node of
        #      the next segment;
        #   -- check if endpoints of each segment indeed have distance = 1 (by querying DB);
        #   -- do it several times?
        MIN_DIST = 7
        SQL_QUERY_TESTING_SAMPLE = "SELECT DISTINCT src_node_id, dest_node_id, distance "\
        + "FROM routing_table WHERE distance > %s" % MIN_DIST
        curs.execute(SQL_QUERY_TESTING_SAMPLE)
        sample = curs.fetchone()
        src_node_id = sample[0]
        dest_node_id = sample[1]
        distance = sample[2]
        
        d, shortestPath = find_shortest_path(src_node_id, dest_node_id)
        # print "%s" % shortestPath
        self.assertEquals(d, len(shortestPath))
        self.assertEquals(d, distance)
        
        print "FOR GOD'S SAKE, FINISH THIS FREAKIN' TEST CODE!!! :)"
        raise
        
#        prev_edge_endpoint = shortestPath[0][0]
#        curr_edge_startpoint
#        
#        l = xrange(len(shortestPath))
#        
#        for indexes in shortestPath:
            
        
        
    def testFSPExceptions(self):
        """
        Bunch of tests that check behaviour of the function in exceptional situations.
        """
        pass