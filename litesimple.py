#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Litesimple is a simple ORM micro-library for sqlite3. It offers mapping
between attributes (or fields as it's named here) to table columns with 
conversion support from different formats, querying, saving and other simple
task.

Homepage and documentation: https://github.com/TheThing/snapshot-agent

Copyright (c) 2012, Marcel Hellkamp.
License: WTFPL (see LICENSE for details)

"""

import sqlite3
import functools
import settings

######################################################################3###
### 

class SQLite(object):
    """A Singleton class that, once called, creates a single sqlite
    connection and reuses it everytime it's called.

    The name of the database is retrieved from a named variable
    SQLITE_FILE from a module called settings.

    """

    _connection = None
    def __new__(cls, *args, **kwargs):
        """Gets an SQLite singleton instance. If one doesn't exist, one is
        created automatically.

        """

        if not cls._connection:
            #Create a new sqlite3 instance and save it into the class,
            #effectively making it permanent.
            cls._connection = sqlite3.connect(settings.SQLITE_FILE)

            #Call the checkdb to make sure all tables exist.
            #This will automatically create the tables for us
            #if they don't exist.
            cls.check_db(cls._connection)

        #Return the sqlite3 singleton instance saved inside the class.
        return cls._connection

    @staticmethod
    def check_db(connection):
        """Check the database to make sure all tables exist and
        automatically create them if they don't.

        Args:
            connection: The SQLite connection database to check.

        """

        cursor = connection.cursor()

        #loop over each and every subclass that inherits Model
        for c in Model.__subclasses__():
            #We only check if the table exists and not the columns.
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (c._tablename,))

            #If the table doesn't exist, this will return None.
            if cursor.fetchone() == None:
                SQLite.create_table(cursor, c)

        connection.commit()
        cursor.close()

    @staticmethod
    def create_table(cursor, model):
        """Wrapper for getting and executing the model's
        create table statement.

        Args:
            cursor: Current open database cursor to use.
            model: The model for the table.

        """

        cursor.execute(model.get_create_statement())

class Field(object):
    """A simple basic database field descriptor that is used to
    map property of an object to a column in the database table.

    The descriptor relies on the principle that the object that uses it
    has ModelMeta as the metaclass. This is important for proper
    initialization of the descriptor so the descriptor knows the attribute
    it's being mapped as.

    The value of the descriptor is, incidentally, not stored in itself
    but inside the instance's __dict__. This is done because descriptors
    are by nature singleton for all instances.

    An excellent guide on this behavior and more detailed look into
    how it works can be found here: http://bit.ly/15gunlo

    Attributes:
        column_name: Name of the table column. Defaults to property name.
        is_key: Specify whether the current column is the primary key.
        is_unique: Specify whether the current column is unique
        allow_null: Specify whether current column allows null. Default: True.
        check: Specify whether sqlite should run check on current column.
        default: The default value this column will have.

    """

    def __init__(self, column_name=None, is_key=False, is_unique=False,
            allow_null=True, check=False, default=None):
        """Initializes Field with specified options.

        Parameters:
            column_name: The name of the database column field maps to.
                This defaults to the attribute name.
            is_key: Boolean specifying whether the field is primary key.
            is_unique: Boolean specifying whether the field is unique or not.
            allow_null: Boolean specifying if the column allows None values.
                This is by default allowed unless otherwise specified.
            check: Boolean specifying whether to 'check' the field (see CHECK
                in the SQLite documentation).
            default: The default value for the field.

        """
        self.column_name = column_name
        self.is_key = is_key
        self.is_unique = is_unique
        self.allow_null = allow_null
        self.check = check
        self.default = default
        self.attr = None

    def __get__(self, instance, owner):
        """Get the current value from the instance's __dict__."""
        if instance == None:
            return self

        return instance.__dict__[self.attr]

    def __set__(self, instance, value):
        """Save the passed value to the instance's __dict__."""
        instance.__dict__[self.attr] = self.validate(value)

    def validate(self, value):
        """Method to validate the value. This should be overridden
        when required.

        Special fields that expect objects of specific types can
        ovverride this.

        Parameters:
            value: The value to validate.

        Returns:
            The value after it has been validated.

        """
        return value

    def to_db_format(self, value, first_time, is_query):
        """Method to convert the current value to a format that will
        be used to store inside the sqlite database.

        Special fields in format unsupported by sqlite can override
        this and perform the conversion to a supported format.

        Parameters:
            value: The value to convert to db format.
            first_time: Boolean signifying if the value is from an instance
                that is being saved for the first time or not.
            is_query: Specifies whether the conversion is happening during
                a query creation or not.

        Returns:
            The value in a format that is accepted by the db.

        """
        return value

    def from_db_format(self, value):
        """Method to convert the value from the database.

        Special fields that need to do conversion to save an object to
        the database can do the conversion again here to it's original
        state.

        Parameters:
            value: The value from the database.

        Returns:
            The value after it has been converted from the database
            format to it's real form.

        """
        return value

    def _get_column_statement(self):
        """Private method used to get the column definition for the current field.
        Used for creating the field's column inside the database table.

        """
        statement = "%s %s" % (self.column_name, self.column_type)
        if self.is_key:
            statement += " PRIMARY KEY"
        elif not self.allow_null:
            statement += " NOT NULL"
        elif self.is_unique:
            statement += " UNIQUE"
        elif self.check:
            statement += " CHECK"
        else:
            from numbers import Number
            statement += " DEFAULT "

            #Whatever the default object may be, we have to make sure
            #it is in a format supported by the database.
            default = self.to_db_format(self.default, False, False)

            #Simple (ugly) check for how the default is formatted in
            #SQL statement.
            if isinstance(default, Number):
                statement += default
            elif default == None:
                statement += "%s" % default
            else:
                statement += "\"%s\"" % default
        return statement

class FieldInteger(Field):
    """A Database Field to hold normal integers.

    Inherits most of the functionality from Field
    and only overrides some of the default configuration.

    """

    def __init__(self, *args, **kwargs):
        """Initialises the FieldInteger."""
        self.column_type = "INTEGER"
        if 'default' not in kwargs:
            kwargs['default'] = 0
        super(FieldInteger, self).__init__(*args, **kwargs)

    def validate(self, value):
        """Override the parent validate and make sure the value passed
        is cast to a proper int.

        """
        return int(value)

class FieldDecimal(Field):
    """A Database Field to hold normal decimal values.

    Inherits most of the functionality from Field
    and only overrides some of the default configuration.

    """

    def __init__(self, *args, **kwargs):
        """Initialises the FieldDecimal."""
        from decimal import Decimal as D
        self.column_type = "NUMERIC"
        if 'default' not in kwargs:
            kwargs['default'] = D(0)
        super(FieldDecimal, self).__init__(*args, **kwargs)

    def validate(self, value):
        """Override the parent validate and make sure the value passed
        is cast to a proper decimal.

        """
        from decimal import Decimal as D
        return D(value)

class FieldText(Field):
    """A Database Field to hold normal text.

    Inherits most of the functionality from Field
    and only overrides some of the default configuration.

    """

    def __init__(self, *args, **kwargs):
        """Initialises the FieldText."""
        self.column_type = "TEXT"
        if 'default' not in kwargs and 'allow_null' in kwargs:
            if not kwargs['allow_null']:
                kwargs['default'] = ''
        super(FieldText, self).__init__(*args, **kwargs)

    def validate(self, value):
        """Override the parent validate and make sure the value passed
        will always turn into a text (string).

        """
        return "%s" % value

class FieldDateTime(Field):
    """A Database Field to hold a datetime value.

    Inherits most of the functionality from Field
    and only overrides some of the default configuration.

    """

    def __init__(self, auto_now=False, auto_now_add=False, *args, **kwargs):
        """Initialises the FieldDateTime."""
        import datetime

        self.column_type = "TEXT"
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

        kwargs['allow_null'] = False
        if 'default' not in kwargs:
            kwargs['default'] = datetime.datetime.min
        super(FieldDateTime, self).__init__(*args, **kwargs)

    def validate(self, value):
        """Override the parent validate and make sure the value passed
        will always turn into a text (string).

        """
        import datetime

        if isinstance(value, datetime.datetime):
            return value
        else:
            raise TypeError("Attempted to assign a non datetime value" +
                            " to a datetime field.")

    def to_db_format(self, value, first_time, is_query):
        """Override the to_db_format to convert the datetime.datetime
        value to string.

        """
        import datetime

        #Override the value if either auto_now is specified or auto_now_add
        #is specified and it is a new item.
        if is_query and (self.auto_now or (first_time and self.auto_now_add)):
            value = datetime.datetime.now()
        return datetime.datetime.strftime(value, "%Y-%m-%d %H:%M:%S.%f")

    def from_db_format(self, value):
        """Override the from_db_format from field to convert the string
        from the database to a datetime.datetime object.

        """
        import datetime

        return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")


class ModelMeta(type):
    """The meta class for the model class used to properly Initialize
    the fields for the models as well as doing other checks.

    For sql, the meta class creates static variables inside
    the model class for easier lookuping on column names and such.

    """

    def __new__(cls, name, bases, dct):
        """Initialize the new model and add appropriate static variables
        to it.

        Among the things it does, it adds private properties containing the
        name of the primary key, the column names and table name as well
        as few other handy private variables.

        It also scans each field belonging in the class and initializes them
        appropriately. If a primary key field is not found, one is created
        automatically with the default sqlite id column name (_rowid_).

        """

        #Initialize and/or override some of the static class variables
        #inside the class
        dct["_columns"] = []
        dct["_tablename"] = None
        dct["_primary_key"] = None
        dct['_tablename'] = name

        found_primary = False

        #dct contains a list of all the attributes inside the current model
        #class so we can effectively loop through it and chech which ones are
        #fiels and initialize them appropriately.
        for attr, value in dct.items():
            if isinstance(value, Field):
                #We need to store the attribute name the descriptor is
                #attached as so it can safely store the value inside the
                #instance __dict__ among other things.
                value.attr = attr

                if value.column_name == None:
                    #By default, we turn the column name of the field to
                    #the attribute name if none is specified.
                    value.column_name = attr

                if value.is_key:
                    if found_primary:
                        #SQLite only supports a single primary key.
                        raise TypeError("Expected a single primary key Field" +
                                        " but found two.")

                    #Mark that a field belonging as the primary key was found
                    #and store the column name for it.
                    found_primary = True
                    dct["_primary_key"] = value.column_name

                #Store the column name inside the _columns private array.
                #This is used to fast generate sql statements without having
                #to loop through the attributes.
                dct["_columns"].append(value.column_name)
                dct[attr] = value


        if dct["_primary_key"] == None:
            #In case where not a single primary key is specified, we can use
            #the internal rowid that sqlite provides to reference our model
            #class during saving and geting. As such, we need to create that
            #field here and add it to the class.
            dct["_columns"].insert(0, "_rowid_")
            dct["_primary_key"] = "_rowid_"
            dct["_rowid_"] = FieldInteger(is_key=True)

        return super(ModelMeta, cls).__new__(cls, name, bases, dct)

class class_or_instance(object):
    """A descriptor that allows a function to both be called with an
    instance and straight from the class.

    """
    def __init__(self, func):
        """Initialize the descriptor."""
        self.func = func

    def __get__(self, instance, owner):
        """When called, calls the function it's tied to with the instance
        if called from within an instance, otherwise calls it with the owner
        class type.

        """
        return functools.partial(self.func, instance if instance else owner)

class Model(object):
    """A base model class to be inherited and used to map objects to tables.

    Contains static functions for retrieving and filtering objects as well
    as other common ORM functionality.

    """

    __metaclass__ = ModelMeta
    _saved = False
    
    def __init__(self, *args, **kwargs):
        """Initialize the model class."""

        #Go over all the attributes and initalize the descriptors
        #with the default values.
        for attr, value in self.__class__.__dict__.items():
            if isinstance(value, Field):
                if attr in kwargs:
                    setattr(self, attr, kwargs[attr])
                else:
                    setattr(self, attr, value.default)

    def save(self):
        """Save all the data in current instance to database. If the
        instance is new, it is inserted and the primary key saved.
        Otherwise it updates the record in database.

        """

        #A holder that will contain all the data to be saved.
        data = {}

        #Loop over every attribute in the class, check if it's a field and
        #if so, save it to the dict. We call the to_db_format in the field
        #to make sure the data is in format compatible with sqlite.
        for attr, value in self.__class__.__dict__.items():
            if isinstance(value, Field) and value.is_key == False:
                data[value.column_name] = value.to_db_format(getattr(self, attr),
                                                             not self._saved,
                                                             True)

        if self._saved:
            #We are updating a previous record in the database so we call
            #an upate with the primary key field as the where statement.
            cursor = self._generate_query("UPDATE", where={
                    self._primary_key: getattr(self, self._primary_key)
                 }, data=data)
        else:
            #Since this is a new object, we simply insert it into the
            #database and make sure to get the rowid for it.
            cursor = self._generate_query("INSERT", {}, data=data)
            setattr(self, self._primary_key, cursor.lastrowid)

        #Make sure the changes are commited before the close the cursor.
        SQLite().commit()
        cursor.close()
        self._saved = True

    @class_or_instance
    def delete(self, **kwargs):
        """Delete current instance from database when called through an instance.
        Otherwise deletes any entries that match the lookup parameters when
        called through the class.

        Parameters:
            Lookup field parameters for the delete statement.

        """
        if isinstance(self, type):
            #When self is None, this function is being called from the
            #class and as such, we run the delete query with the lookup
            #parameters.
            cursor = self._generate_query("DELETE", where=kwargs)
        elif self._saved:
            #The delete function was called from an instance, delete
            #it using the primary key lookup field.
            cursor = self._generate_query("DELETE", where={
                    self._primary_key: getattr(self, self._primary_key)
                 })

    @classmethod
    def get(cls, id=None, **kwargs):
        """Get a single object from the database either with a lookup
        on the primary key or a lookup field parameter. Returns the first
        instance if found or None.

        Parameters:
            id: The primary key of the object to get.
            **kwargs: Named fields and values of the object to get.

        Returns:
            A model instance of the object if found or None.

        """
        if id != None:
            #To save time, you can call the class directly with the id or
            #primary key of the object without naming the field specificly.
            kwargs = {cls._primary_key: id}

        #Query the database with the selected fields and get the first
        #instance. If many are found, only the first one is returned.
        cursor = cls._generate_query("SELECT", where=kwargs)
        result = cls._result_to_model(cursor.fetchone())

        cursor.close()
        return result

    @classmethod
    def filter(cls, **kwargs):
        """Get all objects from the database that match the named parameters
        values.

        Parameters:
            **kwargs: Named fields and values of objects to search for.

        Returns:
            Array of model instances of all the results found.

        """
        result = []
        cursor = cls._generate_query("SELECT", where=kwargs)
        for row in cursor:
            result.append(cls._result_to_model(row))
        cursor.close()
        return result

    @classmethod
    def _generate_query(cls, query, where={}, data={}):
        """A hidden method to generate the requested sql query based on the
        parameters requested and returns the resulting cursor.

        Parameters:
            query: A string containing either of the case insensitive values
                'SELECT', 'UPDATE', 'INSERT' or 'DELETE' based on what the 
                intended action is.
            where: Dict containing the named fields and values to put in the
                WHERE of the sql statement.
            data: Dict containing the named fields and values of the intended
                values to udpate or insert into database.

        Returns:
            The cursor of the executed statement.

        """

        #Loop over both the where and the data dict and make sure the data
        #or the where statement contains supported columns or fields.
        for attr in dict(where.items() + data.items()):
            if attr not in cls._columns:
                raise TypeError("Found unknown column %s. Model only supports columns %s." %
                                    (attr, ', '.join(cls._columns)))

        #Ugly workaround so our where statement doesn't fail even
        #if the where dict is empty.
        where["1"] = 1

        #Generates a nice "field1 = ?, field2 = ?" array that we can
        #quickly join in however we want in the statement.
        where_query = ' AND '.join(["%s = ?" % x for x in where])

        #The query list contains a list of data that will be inserted
        #as parameters into the execute statement for safe inserting.
        query_list = [where[x] for x in where]

        query = query.upper()

        if query == "SELECT":
            #The join takes all the column names and adds a comma between
            #each one. This makes sure our select statement has the data
            #in the same order as our columns.
            statement = "SELECT %s FROM %s WHERE %s" % (', '.join(cls._columns),
                                                        cls._tablename,
                                                        where_query)
        elif query == "UPDATE":
            #Go over the data dict and generate a query string containing
            #the field names. A dict with the fields "id" and "text" will
            #generate a string containing "id = ? and text = ?"
            data_query = ' AND '.join(["%s = ?" % x for x in data])

            #Take all the data and add it to the query list
            query_list = [data[x] for x in data] + query_list

            statement = "UPDATE %s SET %s WHERE %s" % (cls._tablename,
                                                       data_query,
                                                       where_query)
        elif query == "INSERT":
            #Go over the data dict and generate a query string containing
            #the field names with a comma inbetween each name.
            data_query = ', '.join([x for x in data])

            #Take all the data and add it to the query list
            query_list = [data[x] for x in data]

            #The join statement takes the length of the query list array
            #and generates same amount of "?" with comma inbetween.
            statement = "INSERT INTO %s (%s) VALUES (%s)" % (cls._tablename,
                                                             data_query,
                                                             ', '.join("?" * len(query_list)))
        elif query == "DELETE":
            statement = "DELETE FROM %s WHERE %s" % (cls._tablename,
                                                     where_query)
        else:
            raise TypeError("Requested query was of unknown type. Only supports " +
                            "SELECT, UPDATE, INSERT and DELETE but got '%s'" % query)

        #Create our cursor and execute the statement with the query list
        #as parameters. This guarantees protection against sql injection
        #for all data. finally returns the cursor.
        cursor = SQLite().cursor()
        return cursor.execute(statement, query_list)

    @classmethod
    def _result_to_model(cls, result):
        """Class functino that accepts an array of tuples and creates an
        instance of the current model class and fills its attributes with
        the values from the array.

        Parameters:
            result: An array of tuple containing the values for the model's
                attributes in the order of the model's _columns private
                attribute.

        Returns:
            An instance of the model with the filled attributes.

        """
        if result == None:
            return None

        #Create an instance of the model.
        out = cls()
        out._saved = True

        #Go over the _columns, find the attribute for it and
        #assign the value from the result to the attribute.
        for i in range(0, len(cls._columns)):
            for attr, value in out.__class__.__dict__.items():
                if isinstance(value, Field):
                    if value.column_name == cls._columns[i]:
                        setattr(out,
                                attr,
                                value.from_db_format(result[i]))
        return out

    @classmethod
    def get_create_statement(cls):
        """Helper method that generates a CREATE TABLE statement
        based on the current model specification.

        Returns:
            A string containing the full CREATE TABLE statement for
            the current model.

        """
        statement = "CREATE TABLE %s (" % cls._tablename
        col_statements = []

        #Make sure our primary key is first column if one is defined.
        if cls._primary_key != None and cls._primary_key != "_rowid_":
            col_statements.append(cls.__dict__[cls._primary_key]._get_column_statement())

        #Loop over the rest of the attributes of the model and get the column
        #statement for each one and store it in our col_statements array.
        for attr, value in cls.__dict__.items():
            if isinstance(value, Field) and attr != cls._primary_key:
                col_statements.append(value._get_column_statement())

        #Take all the statements in col_statements and join them as comma
        #seperated and add it to our statement.
        statement += "%s)" % ', '.join(col_statements)
        return statement 
