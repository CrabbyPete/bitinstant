#-------------------------------------------------------------------------------
# Name:        models.py
# Purpose:     Define schema for database elements
#              Quote, Order, Executed Order
#
# Author:      Douma
# Notes:       Determines which DB to use. MongoDB or SimpleDB
# Created:     16/02/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
#!/usr/bin/env python

import uuid
import time
import collections

from datetime           import date, datetime, timedelta

# Local imports
import config

USE_MONGO = False

if USE_MONGO:
    from mongodb        import  MongoDatabase
    # This is here so I know what database I am using.
    MONGODB = {'db': 'mirror',
               'options': { 'host': '54.235.177.27',
                            'port': 27017,
                            'username': 'mirror',
                            'password': '1XPhx96V9hny3bDuTu43'
                          }
              }

    SDB = MongoDatabase(MONGODB['db'],**MONGODB['options'])
    STD       = SDB.domain(config.amazon_std_domain)
    TXLOG     = SDB.domain(config.amazon_tx_log_domain )
    USER      = SDB.domain( config.amazon_accounts )
    SESSION   = SDB.domain( config.amazon_sessions )
    BANK      = SDB.domain( config.amazon_bank_accounts )
    FUZE      = SDB.domain( config.amazon_fuze_accounts )


else:
    from database           import Database
    SDB = Database(config.sdb_amazon_access_key,
                   config.sdb_amazon_secret_key
                  )
    STD       = SDB.domain(config.amazon_std_domain)
    TXLOG     = SDB.domain( config.amazon_tx_log_domain )
    USER      = SDB.domain( config.amazon_accounts )
    SESSION   = SDB.domain( config.amazon_sessions )
    BANK      = SDB.domain( config.amazon_bank_accounts )
    FUZE      = SDB.domain( config.amazon_fuze_accounts )
    PAYF      = SDB.domain( config.amazon_std_payment  )
    PAYT      = SDB.domain( config.amazon_std_exchanges )
    IDENTITY  = SDB.domain( config.amazon_identity )


# Define exceptions
class DoesNotExist(Exception):
    """ Exeption for not finding any items """
    pass

class NotUnique(Exception):
    """ Exception for finding more than one item that should be unique """
    pass

class BadArgument(Exception):
    """ Exception for passing bad arguments to a search """
    pass

class MissingAttribute(Exception):
    """ Exception for missing required attribute to a search """
    pass


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
            QUOTE, ORDER,EXECUTED
            Make sure the first line is the eventtype
        """
        self.schema = schema
        #self.klass  = klass

    def all(self, **args ):
        query = TXLOG.select('*').where({'eventtype':self.schema[0]})
        self.result = query.list()
        return self.result

    def get(self, **args ):
        """ Find one and only QuoteID
        """
        # Try doing a get, if you don't get it search
        if 'pk' in args:
            return TXLOG.get(args['pk'])

        query = TXLOG.select('*').where({'eventtype':self.schema[0]})
        query = query.where( args )
        item = query.list()

        # If a list return make sure there is only one item
        if isinstance(item, collections.Iterable):
            if len(item) > 1:
                raise NotUnique("More than one items found")

            if len(item) == 0:
                raise DoesNotExist("Item not found")

            else:
                item = item[0]
        return item

    def filter(self, **args ):
        """ Find one and only QuoteID a list of items found
        """
        # Try doing a get, if you don't get it search
        if 'pk' in args:
            return [TXLOG.get(args['pk'])]

        query = TXLOG.select('*').where({'eventtype':self.schema[0]})
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

        return query
        # The issue with how this is done is that you're not returning the
        # instances of the model class, but instad 'Item' instances from boto.
        """ Return the generator instead of the list
        items = query.list()
        return items
        """

    def related(self, **attr):
        """ Find all records with a similar attribute, and return a list of them
            attrib (dict): attrib and value to look for eq. OrderID = xxxxxxxx
        """
        if 'return_query' in attr:
            return_query = attr['return_query']
            del attr['return_query']
        else:
            return_query = False
        query = TXLOG.select('*')
        if len(attr):
            for key, value in attr.items():
                query = query.where( {key:value} )

            if return_query:
                return query
            return query.list()
        else:
            return None


# Standard Quote schema, first is name of eventtype
QUOTE = (
     "Quote for new transaction",
     "User",                       # NEW: points to a User who started this
     "EventID",
     "DestAccount",
     "OurRate",
     "QuoteID",
     "AmountCreditedToClientAccountUSD",
     "DestExchange",
     "PayMethod",
     "AmountPaidByClientUSD",
     "ExpectedMaxDeliveryTime",
     "expires",
     "ExchangeName",
     "eventtype",
     "EventSentAt",
     "GuaranteedDeliveryTime",
     "SneakPreviewUser",
     "NotifyEmail",
     "AmountToCredit",
     "TransactionID",
     "PaymentAccount",
     "PaymentAccountExpiration",
     "AmountToPayBTC",
     "AmountExpectedUSD",
     "pk"
)

class Quote( dict ):
    """ Define a Quote class
    """

    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, *args, **kwargs ):
        super(Quote,self).__init__(*args, **kwargs)
        self.__dict__ = self
        self["eventtype"] = QUOTE[0]

    objects = Manager( QUOTE )

    def save(self):
        """ Save the current Quote to the database
        """
        if not 'QuoteID' in self:
            self['QuoteID'] = str( uuid.uuid4() )

        self['pk'] = self['QuoteID']
        data = {k: v for (k, v) in self.items() if not k.startswith('_')}
        if TXLOG.new(self['QuoteID'], data):
            return Quote(self)
        return None

    def status(self):
        records = self.objects.related(QuoteID=self.QuoteID)
        status = None
        for record in records:
            if record['eventtype'] == 'Order executed':
                status = 'executed'

            if 'FAILED' in record['eventtype'] or 'failed' in record['eventtype']:
                status = 'failed'

        if not status:
            status = 'pending'
        return status

    def events(self, filter_for_user=True):
        """Return all events associated with a given event.

        KWArgs:
            filter_for_user (bool): Filter out any events that shouldn't be shown to the
                                    end user (default: True).
        """
        records = self.objects.related(QuoteID=self.QuoteID, return_query=True)\
                              .is_not_null('EventID')\
                              .list()
        events = list()
        for record in records:
            e = {'timestamp': float(record['EventSentAt']),
                 'id': record['EventID'],
                 'type': record['eventtype']}
            events.append(e)

        events = sorted(events, key=lambda x: x['timestamp'])
        return events


# Base schema for an New Order, Fist is the eventtype
ORDER = (
     "New Order",
     "EventID",
     "DestAccount",
     "OurRate",
     "QuoteID",
     "DestExchange",
     "PayMethod",
     "eventtype",
     "EventSentAt",
     "AmountToCredit",
     "AmountCredited",
     "PaymentFrom",
     "AmountToCredit",
     "OrderDeadline",
     "AmountDue",
     "OrderID",
     "AmountPaidByClientUSD",
     "User",
     "pk"
 )

class Order( dict ):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, *args, **kwargs ):
        super(Order,self).__init__(*args, **kwargs)
        self.__dict__ = self
        self["eventtype"] = ORDER[0]

    # Define direct objects
    objects = Manager( ORDER )

    def save(self):
        """ Save the current Quote to the database
        """
        if not 'OrderID' in self:
            self['OrderID'] = str( uuid.uuid4() )

        self['pk'] = self['OrderID']
        data = {k: v for (k, v) in self.items() if not k.startswith('_')}
        if TXLOG.new(self['OrderID'], data):
            return Order(self)
        return None

    def status(self):
        """ Return status by finding all records with the OrderId
        """
        records = self.objects.related(OrderID=self.OrderID)
        status = dict(date=self['EventSentAt'],
                      id=self['OrderID'],
                      AmountToCredit=self['AmountToCredit'],
                      Paymethod=self['PayMethod'],
                      DestExchange=self['DestExchange'])

        if 'EventSentAt' in self:
            status['timestamp'] = int(self['EventSentAt'])
        else:
            status['timestamp'] = int(self['expires']) - 3600

        for record in records:
            if record['eventtype'] == 'Order executed':
                status['status'] = 'executed'

            if 'FAILED' in record['eventtype'] or 'failed' in record['eventtype']:
                status['status'] = 'failed'

        if 'status' not in status:
            status['status'] = 'pending'
        return status


# Base schema for Order executed
EXECUTED = (
     "Order executed",
     "EventID",
     "OrderID",
     "DestAccount",
     "QuoteID",
     "DestExchange",
     "eventtype",
     "EventSentAt",
     "FundsSent",
     "SneakPreviewUser",
     "APIResponse",
     "User",
     "pk"
)


class OrderExecuted( dict ):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, *args, **kwargs ):
        super(OrderExecuted,self).__init__(*args, **kwargs)
        self.__dict__ = self
        self["eventtype"] = EXECUTED[0]

    objects = Manager( EXECUTED )

    def save(self):
        """ Save a Quote to the database
        """
        if not 'EventID' in self:
            self['EventID'] = str( uuid.uuid4() )

        self['pk'] = self['EventID']
        data = {k: v for (k, v) in self.items() if not k.startswith('_')}
        if TXLOG.new(self['EventID'], data):
            return OrderExecuted(self)
        return None

    def copy_from_order(self, order, **kwargs ):
        self.OrderID        = order.get('OrderID',None)
        self.DestAccount    = order.get("DestAccount",None)
        self.QuoteID        = order.get("QuoteID",None)
        self.DestExchange   = order.get("DestExchange",None)
        self.FundsSent      = order.get("AmountCredited",None)
        self.SneakPreview   = order.get("SneakPreviewUser",None)

        if 'User' in order:
            self.User = order['User']

        if kwargs:
            self.APIResponse = kwargs
        return self



class GenericManager( object ):
    """ Class for doing searches and gets for database items
    """
    operators = {'eq' :  '=',
                 'gt' :  '>',
                 'gte':  '>=',
                 'lt' :  '<' ,
                 'lte':  '<='
                }

    def all(self, **args ):
        query = TXLOG.select('*').where( args )
        self.result = query.list()
        return self.result

    def get(self, **args ):
        """ Find one and only QuoteID
        """
        # Try doing a get, if you don't get it search
        if 'pk' in args:
            return TXLOG.get(args['pk'])

        query = TXLOG.select('*')
        query = query.where( args )
        item = query.list()

        # If a list return make sure there is only one item
        if isinstance(item, collections.Iterable):
            if len(item) > 1:
                raise NotUnique("More than one items found")

            if len(item) == 0:
                raise DoesNotExist("Item not found")

            else:
                item = item[0]
        return item

    def filter(self, **args ):
        """ Find one and only QuoteID a list of items found
        """
        # Try doing a get, if you don't get it search
        if 'pk' in args:
            return [TXLOG.get(args['pk'])]

        query = TXLOG.select('*')
        for key, value  in args.items():
            if '__' in key:
                key, op = key.split('__')
            else:
                op = 'eq'

            if not isinstance(value, basestring ):
                value = str(value)

            query = query.where({key:value}, self.operators[op])

        return query


class Generic( dict ):
    """ A generic class for creating new records
    """
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, eventtype, *args, **kwargs ):
        super(Generic,self).__init__(*args, **kwargs)
        self["eventtype"] = eventtype

    objects = GenericManager()

    def save(self):
        """ Save a Quote to the database
        """
        if not 'EventID' in self:
            self['EventID'] = str( uuid.uuid4() )

        self['pk'] = self['EventID']
        data = {k: v for (k, v) in self.items() if not k.startswith('_')}
        if TXLOG.new(self['EventID'], data ):
            return Generic(self)
        return None
