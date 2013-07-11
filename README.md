litesimple
==========

Litesimple is a simple ORM micro-library for sqlite3. It offers mapping
between attributes (or fields as it's named here) to table columns with 
conversion support from different formats, querying, saving and other simple
task.

Installation and dependencies
-----------------------------

To install litesimple, either run ``pip install litesimple`` or download [litesimple.py](https://github.com/TheThing/litesimple) directly in your browser or with wget.

Litesimple has no dependancy requirements other than is included in the Python Standard Library.

Example
-------

First create your models:

``` python
from litesimple import Model, FieldInteger, FieldText, FieldDateTime

class car(Model):
    id = FieldInteger(is_key=True)
    text = FieldText()
    time_created = FieldDateTime(auto_now_add=True)
    time_updated = FieldDateTime(auto_now=True)

    def __str__(self):
        return "car (%s)" % self.make
```

Then play with it:

``` python
>>> from models import car
>>> car(make="Opel").save()
>>> car(make="Hyundai").save()
>>> car(make="BMW").save()
>>> print car.get(1)
car (Opel)
>>> for x in car.filter(): print x
car (Opel)
car (Hyundai)
car (BMW)
>>> c = car.get(2)
>>> print c
car (Hyundai)
>>> c = car.get(id=2)
>>> print c
car (Hyundai)
>>> c.delete()
>>> for x in car.filter(): print x
car (Opel)
car (BMW)
>>> car.delete(make="Opel")
>>> for x in car.filter(): print x
car (BMW)
```

That's it.
