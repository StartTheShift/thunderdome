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