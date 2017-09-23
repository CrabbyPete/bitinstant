#-------------------------------------------------------------------------------
# Name:        queue.py
# Purpose:     Use sdb as a persitant delay queue
#
# Author:      Douma
#
# Created:     26/02/2013
#-------------------------------------------------------------------------------
import collections

# Define the schema
QUEUED = (
    'OrderID',
    'SendAt',
    'Cancel'
)

from models     import QUEUE, DoesNotExist


class Manager( object ):
    """ Class for doing searches and gets for database items
    """
    operators = {'eq' :  '=',
                 'gt' :  '>',
                 'gte':  '>=',
                 'lt' :  '<' ,
                 'lte':  '<='
                }

    def __init__( self ):
        """ Initialize
        """
        return

    def all( self ):
        query = QUEUE.select('*')
        self.result = query.list()
        return self.result

    def get( self, name ):
        """ Find one and only one
        """
        return QUEUE.get( name )


class Queue(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, *args, **kwargs):
        super(Queue,self).__init__(*args, **kwargs)

    objects = Manager()

    def save(self):
        """ Save the record make sure all parameters are set
        """
        return STD.update(self['OrderID'], self )


if __name__ == '__main__':
    main()
