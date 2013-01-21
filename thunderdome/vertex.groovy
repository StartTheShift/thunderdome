
def _save_vertex(eid, attrs) {
    /**
     * Saves a vertex
     *
     * :param eid: edge id, if null, a new vertex is created
     * :param attrs: map of parameters to set on the edge
     */
    try {
        v = eid == null ? g.addVertex() : g.v(eid)

        for (item in attrs.entrySet()) {
            if (item.value == null) {
                v.removeProperty(item.key)
            } else {
                v.setProperty(item.key, item.value)
            }
        }
        g.stopTransaction(SUCCESS)
        return g.getVertex(v.id)
    } catch (err) {
        g.stopTransaction(FAILURE)
        throw(err)
    }
}

def _traversal(eid, operation, label, start, end, element_types) {
    /**
     * performs vertex/edge traversals with optional edge labels and pagination
     * :param eid: vertex eid to start from
     * :param operation: the traversal operation
     * :param label: the edge label to filter on
     * :param page_num: the page number to start on (pagination begins at 1)
     * :param per_page: number of objects to return per page
     * :param element_types: list of allowed element types for results
     */
    results = g.v(eid)
    label_args = label == null ? [] : [label]
    switch (operation) {
        case "inV":
            results = results.in(*label_args)
            break
        case "outV":
            results = results.out(*label_args)
            break
        case "inE":
            results = results.inE(*label_args)
            break
        case "outE":
            results = results.outE(*label_args)
            break
        case "bothE":
            results = results.bothE(*label_args)
            break
        case "bothV":
            results = results.both(*label_args)
            break
        default:
            throw NamingException()
    }
    if (start != null && end != null) {
        results = results[start..<end]
    }
    if (element_types != null) {
      results = results.filter{it.element_type in element_types}
    }
    return results
}

def _delete_related(eid, operation, label) {
  try{
    /**
     * deletes connected vertices / edges
     */
    results = g.v(eid)
    label_args = label == null ? [] : [label]
    vertices = true
    switch (operation) {
    case "inV":
    results = results.in(*label_args)
    break
    case "outV":
    results = results.out(*label_args)
    break
    case "inE":
    results = results.inE(*label_args)
    vertices = false
    break
    case "outE":
    results = results.outE(*label_args)
    vertices = false
    break
    default:
    throw NamingException()
    }
    if (vertices) {
      results.each{g.removeVertex(it)}
    } else {
      results.each{g.removeEdge(it)}
    }
    g.stopTransaction(SUCCESS)
  } catch (err) {
    g.stopTransaction(FAILURE)
    raise(err)
  }
}