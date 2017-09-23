#-------------------------------------------------------------------------------
# Name:        database.py
# Purpose:     Abstract the database interface currently uses amazon SDB
#
# Author:      Douma
#
# Created:     21/05/2012
# Copyright:   (c) Douma 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python
# Python imports
import boto

class Query(object):
    """ Class defining a database query
    """
    domain = None
    query  = ""

    def __init__( self, db, domain ):
        """ Keep the domain and database
        """
        self.db     = db
        self.domain = domain
        self.token  = None

    def __iter__(self):
        """ Forces the query to execute and returns query results
        """
        for result in QueryResult( self.db, self.domain, self.query ):
            yield result

    def list(self):
        """ Returns all the results of a query, does not use a generator
        """
        data = QueryResult( self.db, self.domain, self.query )
        self.results = [ r for r in data ]
        return self.results

    def last( self ):
        """ Return the last value of the query
        """
        ret = list()
        self.results = self.list()
        if self.results:
            ret = self.results[-1]
        return ret

    def first(self):
        """Return the first value of the query
        """
        ret = list()
        self.results = self.list()
        if self.results:
            ret = self.results[0]
        return ret

    def reverse(self):
        """ Reverse the results by adding desc
        """
        self.query += 'desc '
        return self

    def order_by( self, name ):
        """ Add order by a field
        """
        self.query += 'order by %s ' % name
        return self

    def limit( self, number ):
        """ Add page limit
        """
        self.query += 'limit %s ' % (int( number),)
        return self

    def select( self, *values ):
        """ Initiate the select sequence
        """
        self.query = 'select '
        self.query = self.query + ','.join(values)
        self.query += ' from `%s` ' % self.domain.name
        return self

    def _add(self):
        """ Add and operator to query
        """
        self.query += 'and '
        return self

    def _expression(self, expression, operator = '=' ):
        """ Evaluate the expressions and add them to query
        """
        first = True
        if isinstance( expression, dict ):
            for key, val in expression.items():
                if not first:
                    self._add()
                else:
                    first = False
                self.query += '%s %s "%s" '% (key, operator, val )

        elif isinstance(expression, str ):
            self.query += expression
        return self

    def where( self, expression, operator = '=' ):
        """ Add where clauses
        """
        if not 'where' in self.query:
            self.query += 'where '
        else:
            self.query += 'and '

        self._expression( expression, operator )
        return self

    def either(self, *expressions ):
        """ Add where clause with or instead of and
        """
        if len(expressions) == 0:
            self.query += 'or '
            return self

        for expression in expressions:
            if not 'where' in self.query:
                self.query += 'where'
            else:
                self.query += 'or '
            self.query += '( '
            self._expression( expression )
            self.query +=') '
        return self


    def intersection(self, *expressions ):
        """ Add intersection to expression
        """
        first = True
        for expression in expressions:
            if first:
                self.query += 'where '
                first = False
            else:
                self.query += 'intersection '
            self.query += '( '
            self._expression( expression )
            self.query +=') '

        return self

    def NOT( self, expression ):
        """ NOT expression
        """
        if 'where' in self.query:
            self.query += 'and '
        else:
            self.query += 'where '

        self.query += 'NOT '
        self._expression( expression  )
        return self

    def every(self, keyword, value):
        """ Every comparision eg.
            select * from mydomain where every(keyword) = 'Book'
        """
        self.query += "where every(%s) = '%s' "%(keyword,value)
        return self

    def between(self, *value):
        """ Add between operator eg.
            select * from mydomain where year between '1998' and '2000'
        """
        self.query += 'between %s and %s '%(value[0],value[1])
        return self

    def like(self, keyword, value):
        """Every comparision eg.

        select * from mydomain where keyword like 'value'
        """
        if 'where' in self.query:
            self.query += 'and '
        else:
            self.query += 'where '

        self.query += "%s like '%s' " % (keyword, value)
        return self

    def is_null(self, name ):
        if not 'where' in self.query:
            self.query += 'where '
        else:
            self.query += 'and '

        self.query += '%s is null '%name
        return self

    def is_not_null(self, name):
        if not 'where' in self.query:
            self.query += 'where '
        else:
            self.query += 'and '

        self.query += '%s is not null '%name
        return self

    def __repr__(self):
        return self.query

    def __unicode__(self):
        return self.query

class QueryResult(object):
    """ Hold on to the results of a query
        Use the boto db select, not the domain select
    """
    token = None
    domain_search = False

    def __init__(self, db, name, query ):
        self.db    = db
        self.name  = name
        self.query = query
        self.token = None
        self._fetch()

    def _fetch(self):
        self.result = self.db.select( self.name,
                                      self.query,
                                      next_token = self.token
                                    )
        self.token = self.result.next_token

    def __unicode__(self):
        return self.query

    def __iter__(self):
        while True:
            for item in self.result:
                yield item
            if self.token:
                self._fetch()
            else:
                break

    def __getitem__(self, index):
        return self.result[index]

    def __setitem__(self, name, value):
        self.result[name] = value

    def __len__(self):
        if self.domain_search:
            return True

        if self.result:
            return len(self.result)
        return 0

    def last(self):
        ret = list()
        if self.result:
            ret = self.result[-1]
        return ret

    def first(self):
        ret = list()
        if self.result:
            ret = self.result[0]
        return ret

    def next_token(self):
        return self.token


class Domain(object):
    """
    Domain level api
    """
    token      = None
    max_items  = None

    def __init__(self, db, name ):
        self.db     = db
        self.name   = name
        self.domain = db.get_domain( name )
        pass

    def select(self, *values):
        # Use db reads rather than domain reads
        self.query = Query( self.db, self.domain )
        self.query.select(*values)
        return self.query

    def get(self, name, consistent_read=True):
        return self.domain.get_item(name, consistent_read=consistent_read)

    def new(self, name, values ):
        self.domain.new_item( name )
        return self.domain.put_attributes( name, values, replace = False )

    def update( self, name, values ):
        return self.domain.put_attributes( name, values, replace = True )

    def new_item( self, name ):
        return self.domain.new_item( name )

    def delete_item( self, item ):
        return self.domain.delete_item(item)

    def delete_attributes( self, name, attributes ):
        """Remove attributes specified in `attributes` from the given item.

        Args:
            name (string): the name/primary key of the target item
            attributes (list): the attributes to be removed from the item.
        """
        return self.domain.delete_attributes(name, attributes=attributes)

    def __unicode__(self):
        return self.name

class Database(object):
    query = ""
    token = None
    def __init__(self,key, secret):
        self.sdb = boto.connect_sdb( key, secret )

    def domain(self, name):
        return Domain( self.sdb, name )

