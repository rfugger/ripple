from routing.pathfinder import find_shortest_path
import sys

src_node_id = int(sys.argv[1])
dest_node_id = int(sys.argv[2])

#src_node_id = 3339
#dest_node_id = 4867
d, res = find_shortest_path(src_node_id, dest_node_id)

#print "sys.argv = %s" % sys.argv
print "src_node_id = %s" % src_node_id
print "dest_node_id = %s" % dest_node_id
print "Distance: %d" % d
print "%s" % res
