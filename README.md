thunderdome
===========

thunderdome is an object-graph mapper (OGM) designed specifically for use with Titan (https://github.com/thinkaurelius/titan)


```
from thunderdome.connection import setup
import thunderdome

setup(['localhost'])

# simple types
class Person(thunderdome.Vertex):
    # vid is added automatically
    name          = thunderdome.Text()
    age           = thunderdome.Interger()
    date_of_birth = thunderdome.DateTime()


class Class(thunderdome.Vertex):
    credits       = thunderdome.Decimal()

# edges
class Enrollment(thunderdome.Edge):
    date_enrolled = thunderdome.DateTime()


```
