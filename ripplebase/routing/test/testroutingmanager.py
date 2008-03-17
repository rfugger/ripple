from twisted.trial import unittest
from routing.smallworld import ids, populate_sw, get_neighbors, \
                    InvalidGraphEx
from routing.rmanager import refresh_routing_table, add_distance,\
                    RoutingTableEx
from psycopg import connect

class RoutingManagerTest(unittest.TestCase):
    
    ROUTING_DB_CONNECT_STR = "dbname=routing_dev_db user=dev password=devdevdev host=localhost"
    # connect to the routing DB and clear the tables
    
    conn = connect(ROUTING_DB_CONNECT_STR)
    curs = conn.cursor() # connect to the routing table storage database
    conn.autocommit()
    
    def setUp(self):
        self.testAdjTable = {
            0: [1],
            1: [0, 2, 8],
            2: [1, 3, 9],
            3: [2, 10],
            4: [7, 8],
            5: [8, 9, 11, 12],
            6: [9, 10],
            7: [4, 11],
            8: [1, 4, 5],
            9: [2, 5, 6],
            10: [3, 6, 12],
            11: [5, 7],
            12: [5, 10]
        }
        
        self.controlRTable = {
            0 : {      1: 1, 2: 2, 3: 3, 4: 3, 5: 3, 6: 4, 7: 4, 8: 2, 9: 3, 10: 4, 11: 4, 12: 4},
            1 : {0: 1,       2: 1, 3: 2, 4: 2, 5: 2, 6: 3, 7: 3, 8: 1, 9: 2, 10: 3, 11: 3, 12: 3},
            2 : {0: 2, 1: 1,       3: 1, 4: 3, 5: 2, 6: 2, 7: 4, 8: 2, 9: 1, 10: 2, 11: 3, 12: 3},
            3 : {0: 3, 1: 2, 2: 1,       4: 4, 5: 3, 6: 2, 7: 5, 8: 3, 9: 2, 10: 1, 11: 4, 12: 2},
            4 : {0: 3, 1: 2, 2: 3, 3: 4,       5: 2, 6: 4, 7: 1, 8: 1, 9: 3, 10: 4, 11: 2, 12: 3},
            5 : {0: 3, 1: 2, 2: 2, 3: 3, 4: 2,       6: 2, 7: 2, 8: 1, 9: 1, 10: 2, 11: 1, 12: 1},
            6 : {0: 4, 1: 3, 2: 2, 3: 2, 4: 4, 5: 2,       7: 4, 8: 3, 9: 1, 10: 1, 11: 3, 12: 2},
            7 : {0: 4, 1: 3, 2: 4, 3: 5, 4: 1, 5: 2, 6: 4,       8: 2, 9: 3, 10: 4, 11: 1, 12: 3},
            8 : {0: 2, 1: 1, 2: 2, 3: 3, 4: 1, 5: 1, 6: 3, 7: 2,       9: 2, 10: 3, 11: 2, 12: 2},
            9 : {0: 3, 1: 2, 2: 1, 3: 2, 4: 3, 5: 1, 6: 1, 7: 3, 8: 2,       10: 2, 11: 2, 12: 2},
            10: {0: 4, 1: 3, 2: 2, 3: 1, 4: 4, 5: 2, 6: 1, 7: 4, 8: 3, 9: 2,        11: 3, 12: 1},
            11: {0: 4, 1: 3, 2: 3, 3: 4, 4: 2, 5: 1, 6: 3, 7: 1, 8: 2, 9: 2, 10: 3,        12: 2},
            12: {0: 4, 1: 3, 2: 3, 3: 2, 4: 3, 5: 1, 6: 2, 7: 3, 8: 2, 9: 2, 10: 1, 11: 2       },
        }
        
        self.controlDBRep = [
            (0, 1, 1), (0, 2, 2), (0, 3, 3), (0, 4, 3), (0, 5, 3), (0, 6, 4), 
            (0, 7, 4), (0, 8, 2), (0, 9, 3), (0, 10, 4), (0, 11, 4), (0, 12, 4), 
            (1, 0, 1), (1, 2, 1), (1, 3, 2), (1, 4, 2), (1, 5, 2), (1, 6, 3),
            (1, 7, 3), (1, 8, 1), (1, 9, 2), (1, 10, 3), (1, 11, 3), (1, 12, 3), 
            (2, 0, 2), (2, 1, 1), (2, 3, 1), (2, 4, 3), (2, 5, 2), (2, 6, 2), 
            (2, 7, 4), (2, 8, 2), (2, 9, 1), (2, 10, 2), (2, 11, 3), (2, 12, 3), 
            (3, 0, 3), (3, 1, 2), (3, 2, 1), (3, 4, 4), (3, 5, 3), (3, 6, 2), 
            (3, 7, 5), (3, 8, 3), (3, 9, 2), (3, 10, 1), (3, 11, 4), (3, 12, 2), 
            (4, 0, 3), (4, 1, 2), (4, 2, 3), (4, 3, 4), (4, 5, 2), (4, 6, 4), 
            (4, 7, 1), (4, 8, 1), (4, 9, 3), (4, 10, 4), (4, 11, 2), (4, 12, 3), 
            (5, 0, 3), (5, 1, 2), (5, 2, 2), (5, 3, 3), (5, 4, 2), (5, 6, 2), 
            (5, 7, 2), (5, 8, 1), (5, 9, 1), (5, 10, 2), (5, 11, 1), (5, 12, 1), 
            (6, 0, 4), (6, 1, 3), (6, 2, 2), (6, 3, 2), (6, 4, 4), (6, 5, 2), 
            (6, 7, 4), (6, 8, 3), (6, 9, 1), (6, 10, 1), (6, 11, 3), (6, 12, 2), 
            (7, 0, 4), (7, 1, 3), (7, 2, 4), (7, 3, 5), (7, 4, 1), (7, 5, 2), 
            (7, 6, 4), (7, 8, 2), (7, 9, 3), (7, 10, 4), (7, 11, 1), (7, 12, 3), 
            (8, 0, 2), (8, 1, 1), (8, 2, 2), (8, 3, 3), (8, 4, 1), (8, 5, 1), 
            (8, 6, 3), (8, 7, 2), (8, 9, 2), (8, 10, 3), (8, 11, 2), (8, 12, 2), 
            (9, 0, 3), (9, 1, 2), (9, 2, 1), (9, 3, 2), (9, 4, 3), (9, 5, 1), 
            (9, 6, 1), (9, 7, 3), (9, 8, 2), (9, 10, 2), (9, 11, 2), (9, 12, 2), 
            (10, 0, 4), (10, 1, 3), (10, 2, 2), (10, 3, 1), (10, 4, 4), (10, 5, 2), 
            (10, 6, 1), (10, 7, 4), (10, 8, 3), (10, 9, 2), (10, 11, 3), (10, 12, 1), 
            (11, 0, 4), (11, 1, 3), (11, 2, 3), (11, 3, 4), (11, 4, 2), (11, 5, 1), 
            (11, 6, 3), (11, 7, 1), (11, 8, 2), (11, 9, 2), (11, 10, 3), (11, 12, 2), 
            (12, 0, 4), (12, 1, 3), (12, 2, 3), (12, 3, 2), (12, 4, 3), (12, 5, 1), 
            (12, 6, 2), (12, 7, 3), (12, 8, 2), (12, 9, 2), (12, 10, 1), (12, 11, 2)]

        
    def testRefresh(self):
        populate_sw(self.testAdjTable)
        refresh_routing_table(ids, get_neighbors)
        # self.assertEquals(get_table(), self.controlRTable)
        self.curs.execute("SELECT src_node_id, dest_node_id, distance FROM routing_table ORDER BY src_node_id, dest_node_id")
        self.assertEquals(self.curs.fetchall(), self.controlDBRep)
        
#    def testAdd_distance(self):
#        # *** the function add_distance does not check whether nodeID is valid kind
#        # of ID - it only cares it's immutable;
#        # does not in any way care about what the distance is;
#        # 1) check if performs as expected with correct data
#        add_distance(1, [2, 3, 4], 5)
#        self.assertEquals(get_table(), {1: {2: 5, 3: 5, 4: 5}})
#        # 2) check if old distance of node 3 will be replaced by new distance
#        add_distance(1, [5, 6, 3], 4)
#        self.assertEquals(get_table(), {1: {2: 5, 3: 4, 4: 5, 5: 4, 6: 4}})
#        # 3) passing a mutable object as nodeID will raise TypeError
#        self.assertRaises(TypeError, add_distance, [1, 2], [7, 8, 9], 5)
#        self.assertRaises(TypeError, add_distance, 1, [[7, 8], 9], 5)
#        # print "%s" % get_table()