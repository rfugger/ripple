from twisted.trial import unittest
from psycopg import connect, ProgrammingError
from routing.rmanager import prepare_tables, RoutingTableEx

class TablePrepareTest(unittest.TestCase):
    ROUTING_DB_CONNECT_STR = "dbname=routing_dev_db user=dev password=devdevdev host=localhost"
    # connect to the routing DB and clear the tables
    
    conn = connect(ROUTING_DB_CONNECT_STR)
    curs = conn.cursor() # connect to the routing table storage database
    conn.autocommit()
    
    def setUp(self):
        pass
        
    def testPrepare(self):
        # 1) test if preparation works when no nodes_table or routing_table exist
        # make sure there are no tables
        try:
            self.curs.execute("DROP TABLE nodes_table CASCADE")
        except ProgrammingError:
            pass
        try:
            self.curs.execute("DROP TABLE routing_table CASCADE")
        except ProgrammingError:
            pass
        prepare_tables()
        self.curs.execute("INSERT INTO nodes_table (id, routing_id) VALUES (1, 'node_1')")
        self.curs.execute("INSERT INTO nodes_table (id, routing_id) VALUES (2, 'node_2')")
        self.curs.execute("INSERT INTO routing_table (src_node_id, dest_node_id, distance) VALUES (1, 2, 3)")
        
        self.curs.execute("SELECT routing_id FROM nodes_table ORDER BY routing_id ASC")
        nodes_table_contents = self.curs.fetchall()
        self.assertEquals(nodes_table_contents, [('node_1',),('node_2',)])
        
        self.curs.execute("SELECT src_node_id, dest_node_id, distance FROM routing_table")
        routing_table_contents = self.curs.fetchall()
        self.assertEquals(routing_table_contents, [(1, 2, 3)])
        
        # 2) test if prepare works when the tables exist
        prepare_tables()
        
        self.curs.execute("SELECT routing_id FROM nodes_table ORDER BY routing_id ASC")
        nodes_table_contents = self.curs.fetchall()
        self.assert_(not nodes_table_contents)
        
        self.curs.execute("SELECT src_node_id, dest_node_id, distance FROM routing_table")
        routing_table_contents = self.curs.fetchall()
        self.assert_(not routing_table_contents)

        # 3) test if prepare works when only one table (the nodes_table) exists
        
        self.curs.execute("DROP TABLE routing_table")
        
        prepare_tables()
        
        self.curs.execute("SELECT routing_id FROM nodes_table ORDER BY routing_id ASC")
        nodes_table_contents = self.curs.fetchall()
        self.assert_(not nodes_table_contents)
        
        self.curs.execute("SELECT src_node_id, dest_node_id, distance FROM routing_table")
        routing_table_contents = self.curs.fetchall()
        self.assert_(not routing_table_contents)
        
        # 4) test if prepare works when only one table (wrong routing_table - should drop) exists
        
        self.curs.execute("DROP TABLE routing_table")
        self.curs.execute("DROP TABLE nodes_table")
        self.curs.execute("CREATE TABLE routing_table (id int4 PRIMARY KEY, trash VARCHAR(20))")
        
        prepare_tables()
        self.curs.execute("INSERT INTO nodes_table (id, routing_id) VALUES (1, 'node_1')")
        self.curs.execute("INSERT INTO nodes_table (id, routing_id) VALUES (2, 'node_2')")
        self.curs.execute("INSERT INTO routing_table (src_node_id, dest_node_id, distance) VALUES (1, 2, 3)")
        
        self.curs.execute("SELECT routing_id FROM nodes_table ORDER BY routing_id ASC")
        nodes_table_contents = self.curs.fetchall()
        self.assertEquals(nodes_table_contents, [('node_1',),('node_2',)])
        
        self.curs.execute("SELECT src_node_id, dest_node_id, distance FROM routing_table")
        routing_table_contents = self.curs.fetchall()
        self.assertEquals(routing_table_contents, [(1, 2, 3)])
        
        self.conn.close()