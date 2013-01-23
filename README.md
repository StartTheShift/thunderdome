thunderdome
===========

thunderdome is an object-graph mapper (OGM) designed specifically for use with Titan (https://github.com/thinkaurelius/titan).
Thunderdome supports easily integrating Gremlin graph-traversals with vertex and edge models. For those already familiar with
Blueprints (https://github.com/tinkerpop/blueprints/wiki) the following is a simple example:

./enrollments.groovy:

```
def all_students(eid) {
    g.v(eid).out('teaches').in('enrolled_in')
}
```

./enrollments.py:

```
from thunderdome.connection import setup
import thunderdome

setup(['localhost'], 'mygraph')

# simple types
class Person(thunderdome.Vertex):
    # All gremlin paths are relative to the path of the file where the class
    # is defined.
    gremlin_path = 'enrollments.groovy'
    
    # vid is added automatically
    name          = thunderdome.Text()
    age           = thunderdome.Integer()
    date_of_birth = thunderdome.DateTime()
    
    # Gremlin methods (automatically parsed and attached from Groovy file)
    all_students  = thunderdome.GremlinMethod()


class Class(thunderdome.Vertex):
    name          = thunderdome.Text()
    credits       = thunderdome.Decimal()

# edges
class EnrolledIn(thunderdome.Edge):
    date_enrolled = thunderdome.DateTime()

class Teaches(thunderdome.Edge):
    overall_mood = thunderdome.Text(default='Grumpy')


prof = Person.create(name='Professor Professorson',
                     age=300,
                     date_of_birth=datetime.datetime(1, 1, 1982))
student = Person.create(name='Johnny Boy',
                        age=56,
                        date_of_birth=datetime.datetime(1, 1, 1990))


# Print UUID for object
print prof.vid
# Print Titan-specific id for object
print prof.eid

physics = Class.create(name='Physics 264', credits=6426.3)
beekeeping = Class.create(name='Beekeeping', credits=23.3)

# Enroll student in both classes
EnrolledIn.create(student, physics, date_enrolled=datetime.datetime.now())
EnrolledIn.create(student, beekeeping, date_enrolled=datetime.datetime.now())

# Set professor as teacher of both classes
Teaches.create(prof, physics, overall_mood='Pedantic')
Teaches.create(prof, beekeeping, overall_mood='Itchy')

# Get all teachers of a given class
physics.inV(Teaches)

# Get all students for a given class
physics.inV(EnrolledIn)

# Get all classes for a given student
student.outV(EnrolledIn)

# Get all moods for a list of teachers
class_moods = [x.overall_mood for x in prof.outE(Teaches)]

# Execute Gremlin method
# The eid is passed in automatically by thunderdome
all_students = prof.all_students()
for x in all_students:
    print x.name

```


To get thunderdome unit tests running you'll need a rexster server configured with a thunderdome graph.  

```
<graph>
    <graph-name>thunderdome</graph-name>
    <graph-type>com.thinkaurelius.titan.tinkerpop.rexster.TitanGraphConfiguration</graph-type>
    <graph-read-only>false</graph-read-only>
    <graph-location>/tmp/thunderdome</graph-location>
    <properties>
          <storage.backend>local</storage.backend>
  <storage.directory>/tmp/thunderdome</storage.directory>
          <buffer-size>100</buffer-size>
    </properties>

    <extensions>
      <allows>
        <allow>tp:gremlin</allow>
      </allows>
    </extensions>
</graph>
```
