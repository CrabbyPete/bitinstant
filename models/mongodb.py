#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Douma
#
# Created:     26/01/2013
# Copyright:   (c) Douma 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

# Python imports
import pymongo


# This causes Mongodb to use async reads. Comment it out to disable
#from gevent import monkey; monkey.patch_all()


class DBError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Query(object):
    """ Converts a SDB select into a mongodb query
        http://docs.mongodb.org/manual/applications/read/#crud-read-find
    """
    DIRECTION  = pymongo.ASCENDING

    def __init__( self, domain  ):
        """ Keep the domain, database and cache if any
        """
        self.domain  = domain
        self.max     = None

    def __iter__(self):
        """ Forces the query to execute and returns query results
            pymongo returns a collection which is a generator
        """
        if not hasattr(self,'results'):
            self.results = QueryResult(
                                        self.domain,
                                        self.query,
                                        self.projection,
                                        self.sort,
                                        self.max
                                      )
        return self.results

    def list(self):
        """ Returns a list of all the results of a query
            It does not use a generator
            token is legacy
        """
        self.results = QueryResult( self.domain,
                                    self.query,
                                    self.projection,
                                    self.sort,
                                    self.max
                                  )
        return self.results


    def __len__(self):
        """ Return the length of the query
        """
        return len( self.results )

    def count(self):
        """ Return the number of items retrieved
        """
        if not hasattr( self, 'results' ):
            return None
        return len( self.results )

    def last(self):
        """ Return the last value of the query
        """
        return self.results[-1]

    def select( self, *values ):
        """ Initiate the select sequence
        """
        self.query = {}
        self.projection = None
        for value in values:
            if value == '*':
                break

            if not self.projection:
                self.projection = {}

            self.projection[value] = 1
        self.sort = ()
        return self

    OPERATORMAP = { '='  :  None,
                    '!=' : '$ne',
                    '>'  : '$gt',
                    '>=' : '$gte',
                    '<'  : '$lt',
                    '<=' : '$lte',
                    'or' : '$or',
                    'not': '$not'
                   }

    def _expression(self, expression, operator = '=' ):
        """ Evaluate the expressions and add them to query
        """
        operator = self.OPERATORMAP[operator]
        for key, value in expression.items():
            if operator:
                value = {operator:value}
        return key, value

    def where( self, expressions, operator = '=' ):
        """ Add where clauses
        """
        if len( expressions) == 1:
            expressions = [expressions]
        for expression in expressions:
            key, value = self._expression(expression, operator)
            if not key in self.query:
                self.query[key] = value
            else:
                self.query[key].update(value)


        return self

    def either(self, expressions, operator = '=' ):
        """ Add where clause with or instead of and
        """
        _or = {'$or':[]}
        if len( expressions ) == 1:
            expressions = [expressions]

        for expression in expressions:
            key, value = self._expression(expression, operator)
            _or['$or'].append( {key, value} )

        self.query.update(_or)
        return self


    def intersection(self, *expressions ):
        """ Add intersection to expression
        """
        first = True
        for expression in expressions:
            pass

        return self

    def NOT( self, expression ):
        """ NOT expression
        """
        for key, value in expression.items():
            self.query.update( {key:{'$ne':value}} )
        return self

    def every(self, keyword, value):
        """ Every comparision eg.
            select * from mydomain where every(keyword) = 'Book'
        """
        return self

    def between(self, *value):
        """ Add between operator eg.
            select * from mydomain where year between '1998' and '2000'
        """
        return self

    def reverse(self):
        """ Reverse the results by adding desc
        """
        self.DIRECTION = pymongo.DESCENDING
        if hasattr(self, 'sort'):
            self.sort = (self.sort[0],self.DIRECTION)
        return self

    def order_by( self, name ):
        """ Add order by a field
        """
        self.sort = (name,self.DIRECTION)
        return self

    def limit( self, number ):
        """ Add page limit
        """
        self.max = number
        return self

    def is_not_null(self, key ):
        self.query[key] = {'$exists':True}
        return self


    def __repr__(self):
        return str(self.query)

    def __unicode__(self):
        return str(self.query)

class QueryResult(object):
    """ Hold on to the results of a query
    """
    def __init__(self, name, query, projection, sort, limit ):
        if len(sort) > 0:
            if limit:
                self.results = name.find( query,
                                          projection,
                                          timeout = False,
                                          sort = [sort] ).limit(limit)
            else:
                self.results = name.find( query,
                                          projection,
                                          timeout = False,
                                          sort = [sort] )
        else:
            if limit:
                self.results = name.find( query,
                                          projection,
                                          timeout = False ).limit(limit)
            else:
                self.results = name.find( query, projection, timeout = False )

    def __iter__(self):
        return self.results

    def next(self):
        return self.results.next()

    def __len__(self):
        """ Return the size of the result array, or the size of what is in the
            queue
        """
        return self.results.count()


    def _all(self):
        """ Return an array of all the results at one time
        """
        return self.results



class Domain(object):
    """
    Domain level api
    """
    def __init__(self, db, name ):
        """ Initialize the domain
            Save database, mongo collection, and collection name
        """
        self.db           = db
        self.collection   = db[name]
        self.name         = name

    def select( self, *values):
        """ Run a search based on a query select
        """
        self.query = Query( self.collection )
        self.query.select(*values)
        return self.query

    def get( self, name ):
        item = self.collection.find_one( name )
        return item

    def new( self, values ):
        item = self.collection.insert( values )
        return item

    def new_item( self, values ):
        item = self.collection.insert( values )
        return item

    def update( self, values ):
        item = self.collection.update( {'pk':values['pk']}, values )
        return item

    def save(self, values ):
        item = self.collection.save( values )
        return self.collection.find_one(item)

    def __unicode__(self):
        return self.name


class MongoDatabase(object):
    def __init__(self, db, **options ):
        if not 'host' in options:
            options['host'] = 'localhost'

        if not 'port' in options:
            options['port'] = 27017

        try:
            connection = pymongo.MongoClient(options['host'],options['port'])
            self.db = connection[db]
            if 'username' in options and 'password' in options:
                self.db.authenticate(options['username'],options['password'])
        except:
            raise DBError('Database did not connect')

    def domain(self, name):
        return Domain( self.db, name )

