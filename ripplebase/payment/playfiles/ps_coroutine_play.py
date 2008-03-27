from ripplebase.pathsetv1 import Path, PathScope, PathSetCr, Hop, Edge, RESULT_PATH_FOUND
import sys

src_id, dest_id = (int(sys.argv[1]), int(sys.argv[2]))
ps = PathSetCr(src_id, dest_id)
#ps.find_path(10)

#sc = ps.search_coroutine()
#res = sc.next()

#print res

curr_hop = src_hop = Hop(src_id)
path = Path()
path_scope = PathScope()
#path.hop_edge_sequence.append((src_hop))
res = (None,)*5

while res[2] != RESULT_PATH_FOUND:
    #print "playfile: curr_hop.id is: %s" % curr_hop.id
    res = ps.search_agent.send((path, path_scope, curr_hop, 10))
    #print res[0]
    curr_hop = res[0][1]
    print "res[1] = %s" % res[1]
    #path.hop_edge_sequence.append(res[0:2])

print "\n\nheyheyhey! path found!!!"
for entry in path.hop_edge_sequence:
	print entry[0].id

print "credit_limit = %s" % path.credit_limit

#print "\n\nAnd path_scope.step_data_sequence contains: \n%s" % path_scope.step_data_sequence

#path_scope.prune_path_scope_leaf()

#print "\n\npath_scope overall distance picture before processing:"
#for data_lists in path_scope.step_data_sequence:
#    print data_lists[4]

path_scope.process_path_scope()

#print "\n\npath_scope overall distance picture after processing:"
#for data_lists in path_scope.step_data_sequence:
#    print data_lists[4]

#print "\n\npath_scope.step_data_sequence before switching to contexted data:"
#print path_scope.step_data_sequence

#path = Path()
#path_scope.switch_to_contexted_scope_data(3, id(path))

#print "\n\npath_scope.step_data_sequence after switching to contexted data:"
#print path_scope.step_data_sequence

new_path, curr_hop, new_path_scope = path_scope.convert_to_path()
#print "====================================="
#Edge(path.hop_edge_sequence[0][1], id(new_path))
#print "====================================="
#print "\n\nComputed new_path:\n" 
#for tup in new_path.hop_edge_sequence:
#    print "list(tup) is: %s" % list(tup)
#    print "hop id:"
#    print tup[0].id
#print "curr_hop.id: %s" % curr_hop.id

res = (None,)*5
#new_path_scope = PathScope()



while res[2] != RESULT_PATH_FOUND:
    #print "playfile: curr_hop.id is: %s" % curr_hop.id
    res = ps.search_agent.send((new_path, new_path_scope, curr_hop, 10))
    #print res[0]
    curr_hop = res[0][1]
    print "res[1] = %s" % res[1]


print "\n\nheyheyhey! path found!!!"
for entry in new_path.hop_edge_sequence:
	print entry[0].id
print "credit_limit = %s" % path.credit_limit

path_scope.process_path_scope()
new_path, curr_hop, new_path_scope = path_scope.convert_to_path()
res = (None,)*5

while res[2] != RESULT_PATH_FOUND:
    #print "playfile: curr_hop.id is: %s" % curr_hop.id
    res = ps.search_agent.send((new_path, new_path_scope, curr_hop, 10))
    #print res[0]
    curr_hop = res[0][1]
    print "res[1] = %s" % res[1]


print "\n\nheyheyhey! path found!!!"
for entry in new_path.hop_edge_sequence:
	print entry[0].id
print "credit_limit = %s" % path.credit_limit

