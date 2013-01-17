
def get_map(eid) {
    /**
     * returns the given vertex nested in a map
     */
    v = g.v(eid)
    [vertex:v, number:5]
}

def get_list(eid) {
    /**
     * returns the given vertex nested in a list
     */
    v = g.v(eid)
    [null, 0, 1, [2, v, 3], 5]
}


