#-------------------------------------------------------------------------------
# Name:        bank.py
# Purpose:     Bank Account class for bitinstant models
#
# Author:      Douma
# Notes:       http://mindref.blogspot.com/2012/11/generate-account-number.html
# Created:     16/02/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import collections
import time

from models     import(BANK, DoesNotExist, MissingAttribute, BadArgument, NotUnique  )

# Bank Account schema
BANKACCOUNT = (
    'User',         # The owner of this account, should be a pk to User
    'Name',         # Let the user name the account
    'Account',      # Only store the last 4 digits, the rest should be x'ed out
    'ACSAccountID', # ACS Stored account token
    'Type',         # 'acsbank' or 'acsdebit'
    'Status',       # Status of account
    'Created',      # Date created
    'pk'            # Primary key
)


class BankAccountManager(object):
    """ Query User database
    """
    operators = {'eq' :  '=',
                 'gt' :  '>',
                 'gte':  '>=',
                 'lt' :  '<' ,
                 'lte':  '<='
                }

    def __init__(self, schema  ):
        """ Initialize with schema
        """
        self.schema = schema


    def get(self, **args):
        """ Get a bank account (ascdebit or acsbank) record
        """
        item = None

        # If you have a pk just get the record
        if 'pk' in args:
            item = BANK.get(args['pk'])

        # If you are searching for a user by email or phone
        else:
            query = BANK.select('*')
            query = query.where(args)

            item = query.list()
            if isinstance(item, collections.Iterable):
                if len(item) > 1:
                    raise NotUnique("Error multiple bank accounts found")
                elif len(item) < 1:
                    raise DoesNotExist("Error no such bank account")
                else:
                    item = item[0]

        # Check that you got an item
        if not item:
            raise DoesNotExist("Error no such bank account")

        # Query list alway returns a list, there should be one in it
        return BankAccount(item)

    def filter(self, **args ):
        """ Find items with attributes in args
        """
        # Try doing a get, if you don't get it search
        if 'pk' in args:
            return [BANK.get(args['pk'])]

        query = BANK.select('*')
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


class BankAccount(dict):
    """ Define attributes for a User
    """
    __getattr__ = dict.__getitem__

    def __setattr__ (self, attr, value ):
        if attr in BANKACCOUNT:
            self[attr] = value
        else:
            raise BadArgument("Key %s not a valid argument" % attr)

    def __init__(self, *args, **kwargs):
        super(BankAccount, self).__init__(*args, **kwargs)

    # Object manage for searching items
    objects = BankAccountManager(BANKACCOUNT)

    def save(self):
        """ Save the current account, increment the user number
        """
        # Is this a new account with no pk
        if not 'pk' in self:
            try:
                query = BANK.select('pk')\
                            .is_not_null('pk')\
                            .order_by('pk')\
                            .reverse()

                last = query.list()[0]
            except Exception:
                self['pk'] = 1

            # This is a new user increment the user number
            else:
                self['pk'] = int(last['pk']) + 1

            # Make sure the required fields are set
            self['Created'] = time.time()
            self['Status'] = 'active'
            for item in BANKACCOUNT:
                if not item in self:
                    raise MissingAttribute("Missing {}".format(item))

            ok = BANK.new(self['pk'], self)
        else:
            ok = BANK.update(self['pk'], self)

        # If it save return what you saved
        if ok:
            return BankAccount(self)

        return None

    def is_active(self):
        return self['Status'] == 'active'

