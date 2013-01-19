
def _save_edge(eid, outV, inV, label, attrs, exclusive) {
	/**
	 * Saves an edge between two vertices
	 * 
	 * :param eid: edge id, if null, a new vertex is created
	 * :param inV: edge inv id
	 * :param outV: edge outv id
	 * :param attrs: map of parameters to set on the edge
	 * :param exclusive: if true, this will check for an existing edge of the same label and modify it, instead of creating another edge
	 */
	try{
		try {
			e = g.e(eid)
		} catch (err) {
			existing = g.v(outV).outE(label).as('edge').inV().filter{it.id == inV}.back('edge').toList()
			if(existing.size() > 0 && exclusive) {
				e = existing.first()
			} else {
				e = g.addEdge(g.v(outV), g.v(inV), label)
			}
		}
		for (item in attrs.entrySet()) {
            if (item.value == null) {
                e.removeProperty(item.key)
            } else {
                e.setProperty(item.key, item.value)
            }
		}
		g.stopTransaction(SUCCESS)
		return g.getEdge(e.id)
	} catch (err) {
		g.stopTransaction(FAILURE)
		throw(err)
	}
}


def _get_edges_between(outV, inV, label, page_num, per_page) {
  try {
    results = g.v(outV).outE(label).as('e').inV().filter{it.id == inV}.back('e')
    if (page_num != null && per_page != null) {
        start = (page_num - 1) * per_page
        end = start + per_page
        return results[start..<end]
    } else {
        return results
    }
  } catch(err) {
    g.stopTransaction(FAILURE)
    throw(err)
  }
}