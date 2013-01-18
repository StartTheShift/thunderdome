def first_method(a1, a2) {
  return something()
}

def second_method(a1, a2, a3) {
  tmp = g.v(a1).outE()
  tmp.filter{it.id == a2}.has('property', a3)
}

def get_self(eid) {
    g.v(eid)
} 

def return_value(eid, val) {
    return val
}

def return_list(eid) {
    return (0..10)
}

def test_mixed_return(eid) {
    return [g.addVertex(), 5, 'string']
}

def long_func(eid) {
	t = g.startTransaction()
	try {
	  if (something) {
	    g.e(e)
	  }
	} catch(e) {
	  throw e
	}
}