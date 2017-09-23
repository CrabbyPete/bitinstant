import time
import json

from models import SESSION, DoesNotExist


class SessionManager(object):
    """ Query User database
    """
    operators = {
                    'eq'  :'=',
                    'gt'  :'>',
                    'gte' :'>=',
                    'lt'  :'<' ,
                    'lte' :'<='
                 }

    def get(self, pk=None):
        """ Get a user record
        """
        item = None

        # If you have a pk just get the record
        item = SESSION.get(pk, consistent_read=True)

        # Check that you got an item
        if not item:
            raise DoesNotExist("Session does not exist.")
        return Session(item)

    def filter(self, **kwargs):
        """Find one and only QuoteID a list of items found
        """
        # Try doing a get, if you don't get it search
        if 'pk' in kwargs:
            try:
                ret = [self.get(kwargs['pk'])]
            except DoesNotExist:
                ret = []
            return ret

        query = SESSION.select('*')
        for (key, value) in kwargs.items():
            if '__' in key:
                key, op = key.split('__')
            else:
                op = 'eq'

            if not isinstance(value, basestring):
                value = str(value)

            query = query.where({key: value}, self.operators[op])

        items = query.list()
        return items


class Session(dict):
    """ Define attributes for a User
    """
    objects = SessionManager()

    def save(self):
        """Save the current Session instance.  If it doesn't exist, create a new object in the datastore.
        """
        self['atime'] = self['atime'] if 'atime' in self else time.time()
        self['data'] = self['data'] if 'data' in self else json.dumps({})
        try:
            self.objects.get(pk=self['pk'])
        except DoesNotExist:
            SESSION.new(self['pk'], self)
        else:
            SESSION.update(self['pk'], self)

    def delete(self):
        """Delete this Session instance from the datastore.
        """
        try:
            self.objets.get(pk=self['pk'])
        except:
            pass
        else:
            SESSION.delete_item(self['pk'])
