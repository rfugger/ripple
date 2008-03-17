from twisted.trial import unittest
from routing.smallworld import populate_sw, validate_graph, ids, \
                                InvalidGraphEx

class SWInfoValidateGraphTest(unittest.TestCase):
    def setUp(self):
        pass
#    def testPopulateSW(self):
#        validGraph = {
#            0: [1,2,3],
#            1: [0,3,2],
#            2: [0,3],
#            3: [4],
#            4: []
#        }
#        populate_sw(validGraph)
#        
    def testIDS(self):
        validGraph = {
            0: [1,2,3],
            1: [0,3,2],
            2: [0,3],
            3: [4],
            4: []
        }
        populate_sw(validGraph)
        self.assertEquals(ids(), [0, 1, 2, 3])
    def testCheckValid(self):
        validGraph = {
            0: [1,2,3],
            1: [0,3,2],
            2: [0,3],
            3: [4],
            4: []  
        }
        validate_graph(validGraph)
        self.assert_(True)
    
    def testInvalidRaises(self):
        invalidGraph1 = {
            0: [1,2,3],
            1: [0,10,2],
            2: [0,3],
            3: [4],
            4: [5]  
        }
        self.assertRaises(InvalidGraphEx, validate_graph, invalidGraph1)
        invalidGraph2 = {
            0: [1,'2',3],
            1: [0,10,2],
            2: [0,3],
            3: [4],
            4: [5]  
        }
        self.assertRaises(InvalidGraphEx, validate_graph, invalidGraph2)
        invalidGraph3 = {
            0: [1,1.2,3],
            1: [0,10,2],
            2: [0,3],
            3: [4],
            4: [5]  
        }
        self.assertRaises(InvalidGraphEx, validate_graph, invalidGraph3)
        invalidGraph4 = {
            0: [1,2],
            1: 0,
            2: [1]
        }
        self.assertRaises(InvalidGraphEx, validate_graph, invalidGraph4)