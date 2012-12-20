
def _save_edge(eid, inV, outV, label, attrs, exclusive) {
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
			existing = g.v(inV).out(label).filter{it.id == outV}
			if(existing.count() > 0 && exclusive) {
				e = existing[0]
			} else {
				e = g.addEdge(g.v(inV), g.v(outV), label)
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