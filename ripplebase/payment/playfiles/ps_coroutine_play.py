from ripplebase.pathsetv1 import Path, PathSetCr, Hop, RESULT_PATH_FOUND
import sys

src_id, dest_id = (int(sys.argv[1]), int(sys.argv[2]))
ps = PathSetCr(src_id, dest_id)
#ps.find_path(10)

#sc = ps.search_coroutine()
#res = sc.next()

#print res

curr_hop = src_hop = Hop(src_id)
path = Path()
res = (None,)*5

while res[2] != RESULT_PATH_FOUND:
    res = ps.search_agent.send((path, curr_hop, 10))
    print res[0]
    curr_hop = res[0][1]
