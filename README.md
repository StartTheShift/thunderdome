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
    age           = thunderdome.Integer()
    date_of_birth = thunderdome.DateTime()


class Class(thunderdome.Vertex):
    name          = thunderdome.Text()
    credits       = thunderdome.Decimal()

# edges
class Enrollment(thunderdome.Edge):
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
bee_keeping = Class.create(name='Beekeeping', credits=23.3)

# Enroll student in both classes
Enrollment.create(student, physics, date_enrolled=datetime.datetime.now())
Enrollment.create(student, beekeeping, date_enrolled=datetime.datetime.now())

# Set professor as teacher of both classes
Teaches.create(prof, physics, overall_mood='Pedantic')
Teaches.create(prof, beekeeping, overall_mood='Itchy')

# Get all teachers of a given class
physics.inV(Teaches)

# Get all students for a given class
physics.inV(Enrollment)

# Get all classes for a given student
student.outV(Enrollment)

```
