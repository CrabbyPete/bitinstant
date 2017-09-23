#-------------------------------------------------------------------------------
# Name:        std.py
# Purpose:     Model the STD library
#
# Author:      Douma
#
# Created:     26/02/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import collections

# Define the schema
PAYFROM = (
    'Enabled',
    'MethodName',
    'LimitPerTx',
    'FeePercentage',
    'LowerFeePercentage',
    'Display',
    'RateLevel',
    'action',
    'table'
)


PAYTO = (
    'Enabled',
    'Display',
    'ExchangeName',
    'FeePercentage',
    'LowerFeePercentage',
    'RateLevel',
    'action',
    'table'
)

from models     import STD, DoesNotExist


class Manager( object ):
    """ Class for doing searches and gets for database items
    """
    operators = {'eq' :  '=',
                 'gt' :  '>',
                 'gte':  '>=',
                 'lt' :  '<' ,
                 'lte':  '<='
                }

    def __init__(self, schema  ):
        """ Initialize to the type of item you are looking for
            Payment or Exchange
            Make sure the first line is the eventtype
        """
        self.schema = schema

    def all(self, **args ):
        query = STD.select('*').where(args)
        self.result = query.list()
        return self.result

    def get(self, **args ):
        """ Find one and only QuoteID
        """
       # Make sure its a valid argument
        for key in args.keys():
            if not key in self.schema:
                raise BadArgument("Key %s not a valid argument" % key )

        query = STD.select('*')
        query = query.where( args )
        item = query.list()

        # If a list return make sure there is only one item
        if isinstance(item, collections.Iterable):
            if len(item) > 1:
                raise NotUnique("More than one items found")
            if len(item) == 0:
                print "No items found"
                return None
            else:
                item = item[0]
        return item

    def filter(self, **args ):
        """ Find one and only QuoteID a list of items found
        """
        query = TXLOG.select('*')
        for key, value  in args.items():
            if '__' in key:
                key, op = key.split('__')
            else:
                op = 'eq'

            if not key in self.schema:
                raise BadArgument("Key %s not a valid argument" % key )

            if not isinstance(value, basestring ):
                value = str(value)

            query = query.where({key:value}, self.operators[op])

        items = query.list()
        return items

class PayFrom(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, *args, **kwargs):
        super(Paymethod,self).__init__(*args, **kwargs)
        self.__dict__ = self

    objects = Manager(PAYFROM)

    def save(self):
        """ Save the record make sure all parameters are set
        """
        for key, value in self.items():
            if not key in PAYFROM:
                raise  BadArguement("Key %s",key)

        return STD.update(self['MethodName'], self )

class PayTo(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, *args, **kwargs):
        super(Exchange,self).__init__(*args, **kwargs)
        self.__dict__ = self

    objects = Manager(PAYTO)

    def save(self):
        """ Save the record make sure all parameters are set
        """
        for key, value in self.items():
            if not key in PayTo:
                raise  BadArguement("Key %s",key)

        return STD.update(self['ExchangeName'], self )

def main():
    import pprint
    pp = pprint.PrettyPrinter(indent=4)

    # Look for a know QuoteID in -Dev
    items = PayFrom.objects.all(action = 'AddMethod')
    for item in items:
        pay = PayFrom.objects.get( MethodName = item['MethodName'])
        if not 'Display' in pay:
            pay['Display'] = pay['MethodName'].capitalize()
        if not 'RateLevel' in pay:
            pay['RateLevel'] = 100
        pp.pprint(pay)
        ans = raw_input('Send Notice? (y/n)')
        if ans == 'y':
            pay.save()


    items = PayTo.objects.all(action = 'AddExchange')
    for item in items:
        pp.pprint(item)

if __name__ == '__main__':
    main()
