
def _traversal(eid, operation, label, page_num, per_page) {
    /**
     * performs vertex/edge traversals with optional edge labels and pagination
     * :param eid: vertex eid to start from
     * :param operation: the traversal operation
     * :param label: the edge label to filter on
     * :param page_num: the page number to start on (pagination begins at 1)
     * :param per_page: number of objects to return per page
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
        default:
            throw NamingException()
    }
    if (page_num != null && per_page != null) {
        start = (page_num - 1) * per_page
        end = start + per_page
        results = results[start..<end]
    }
    return results
}

def _delete_related(eid, operation, edge_label) {
    /**
     * deletes connected vertices / edges
     */
}