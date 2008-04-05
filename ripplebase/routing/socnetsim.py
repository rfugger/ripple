##################
# Copyright 2008, Jevgenij Solovjov
#
# This file is part of Ripplebase.
#
# Ripplebase is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as 
# published by the Free Software Foundation, either version 3 of the 
# License, or (at your option) any later version.
#
# Ripplebase is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public 
# License along with Ripplebase, in the file LICENSE.txt.  If not,
# see <http://www.gnu.org/licenses/>.
##################

from random import random

adjTable = {}

def sample_prob_fn():
    #while 1:
    #    yield random() - 0.499
    return random() - 0.495
def compose_adj_table(numNodes, prob_gen):
    rangeGen = xrange(numNodes)
    nodeSet = set(rangeGen)
    #randIter = sample_prob_fn()
    count = 0
    while nodeSet:
        count += 1
        res, rem = divmod(count,100)
        if rem == 0: print "%d" % count
        srcNode = nodeSet.pop()
        adjTable.setdefault(srcNode, [])
        for node in nodeSet:
            #rand = randIter.next()
            rand = prob_gen()
            if int(rand + 0.5):
                adjTable[srcNode].append(node)
                adjTable.setdefault(node, [])
                adjTable[node].append(srcNode)
                
#compose_adj_table(10000, sample_prob_fn)
#print "%s" % adjTable
