
def _save_edge(eid, v1, v2, label, attrs, exclusive) {
	/**
	 * Saves an edge between two vertices
	 * 
	 * :param eid: edge id, if null, a new vertex is created
	 * :param v1: edge inv id
	 * :param v2: edge outv id
	 * :param attrs: map of parameters to set on the edge
	 * :param exclusive: if true, this will check for an existing edge of the same label and modify it, instead of creating another edge
	 */
	try{
		try {
			e = g.e(eid)
		} catch (err) {
			existing = g.v(v1).out(label).filter{it.id == v2}
			if(existing.count() > 0 && exclusive) {
				e = existing[0]
			} else {
				e = g.addEdge(g.v(v1), g.v(v2), label)
			}
		}
		for (item in attrs.entrySet()) {
			e.setProperty(item.key, item.value)
		}
		g.stopTransaction(SUCCESS)
		return g.getEdge(e.id)
	} catch (err) {
		g.stopTransaction(FAILURE)
		throw(err)
	}
}