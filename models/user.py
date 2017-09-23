#-------------------------------------------------------------------------------
# Name:        user.py
# Purpose:     Quote class for bitinstant models
#
# Author:      Douma
# Notes:       http://mindref.blogspot.com/2012/11/generate-account-number.html
# Created:     16/02/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import hashlib
import collections

from uuid               import uuid4
from itertools          import izip

# Local imports
from feistel            import (make_feistel_number,
                                 sample_f,
                                 luhn_sign,
                                 is_luhn_valid
                               )

from models     import USER, DoesNotExist, NotUnique
from mixins.user import UserGoogleAuthenticatorMixin, UserTwoFactorMixin

# User Account schema
ACCOUNT = (
    'UserName',
    'Account',
    'Active',
    'Password',
    'LastName',
    'FirstName',
    'Status'
    'Email',
    'Phone',
    'DOB',
    'Address',
    'City',
    'State',
    'Country',
    'LexID',
    'LexStatus',
    'OTPProvider',
    'OTPSecret',
    'OTPPassPhrase',
    'OTPProvider',
    'Quotes'     # An array of quotes for this user
    'Orders'     # An array of orders for this user
)


def constant_time_compare(val1, val2):
    """Returns True if the two strings are equal, False otherwise.

    The time taken is independent of the number of characters that match.  Do
    not use this function for anything else than comparison with known
    length targets.

    This is should be implemented in C in order to get it completely right.

    Taken from: https://github.com/mitsuhiko/itsdangerous/blob/master/itsdangerous.py
    License: https://github.com/mitsuhiko/itsdangerous/blob/master/LICENSE
    """
    len_eq = len(val1) == len(val2)
    if len_eq:
        result = 0
        left = val1
    else:
        result = 1
        left = val2
    for x, y in izip(left, val2):
        result |= ord(x) ^ ord(y)
    return result == 0


class UserManager(object):
    """ Query User database
    """
    def get(self, **args):
        """ Get a user record
        """
        item = None

        # If you have a pk just get the record
        if 'pk' in args:
            item = USER.get(args['pk'])

        # If you have the account you can derive the pk from it
        elif 'account' in args:
            if is_luhn_valid(args['account']):
                number = int(args['account']) / 10
                feistel = make_feistel_number(sample_f)
                number = feistel(number)
                item = USER.get(number)

        # If you are searching for a user by email or phone
        else:
            query = USER.select('*')
            query = query.where(args)

            item = query.list()
            if isinstance(item, collections.Iterable):
                if len(item) > 1:
                    raise NotUnique("Error multiple users found")
                elif len(item) < 1:
                    raise DoesNotExist("Error no such user")
                else:
                    item = item[0]

        # Check that you got an item
        if not item:
            raise DoesNotExist("Error no such user")

        # Query list alway returns a list, there should be one in it

        return User(item)


class User(UserTwoFactorMixin, UserGoogleAuthenticatorMixin, dict):
    """ Define attributes for a User
    """
    __getattr__ = dict.__getitem__

    id_fields_map = {
                        'lex_id'      : 'LexID',
                        'lex_status'  : 'LexStatus',
                        'first_name'  : 'FirstName',
                        'last_name'   : 'LastName',
                        'address'     : 'Address',
                        'city'        : 'City',
                        'country'     : 'Country',
                        'postal_code' : 'PostalCode',
                        'state'       : 'State',
                        'dob'         : 'DOB',
                        'country'     : 'Country',
                        'phone_number': 'Phone',
                    }

    def __setattr__(self, attr, value):
        if attr == 'Password':
            self.set_password(value)
        else:
            self[attr] = value

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        if not 'Email' in self and not 'Phone' in self and not 'UserName' in self:
            raise AttributeError("Email,Phone or UserName is required")

        # If the password is passed in set it, else yell at the user
        if 'Password' in kwargs:
            self.set_password(kwargs['Password'])
        elif not 'Password' in self:
            raise AttributeError("Password is required")

        if not 'UserName' in self:
            self.UserName = None

        if not 'Email' in self:
            self['Email'] = None

        if not 'Phone' in self:
            self['Phone'] = None

        if not 'FirstName' in self:
            self['FirstName'] = None

        if not 'LastName' in self:
            self['LastName'] = None

        if not 'Address' in self:
            self['Address'] = None

        if not 'City' in self:
            self['City'] = None

        if not 'PostalCode' in self:
            self['PostalCode'] = None

        if not 'State' in self:
            self['State'] = None

        if not 'Country' in self:
            self['Country'] = 'USA'


        if not 'DOB' in self:
            self['DOB'] = None

        # LexisNexis specific fields
        if not 'LexID' in self:
            self['LexID'] = None

        if not 'LexStatus' in self:
            # LexStatus must be one of ('UNKNOWN', 'VERIFIED', 'AUTHENTICATED')
            # NOTE (brian) :: Wouldn't enumerations be nice in python? *sigh*
            self['LexStatus'] = 'UNKNOWN'

        if not 'OTPPassPhrase' in self:
            self['OTPPassPhrase'] = None
        if not 'OTPProvider' in self:
            self['OTPProvider'] = None
        if not 'OTPSecret' in self:
            self['OTPSecret'] = None


        self['Status'] = 'active'

    # Object manage for searching items
    objects = UserManager()

    def _account_number(self, number):
        """ Create an account number from the user number
            Give 10 modulus checksum to double check
        """
        feistel = make_feistel_number(sample_f)
        number = feistel(number)
        number = luhn_sign(number)
        return number

    @property
    def salt(self):
        salt, password = self['Password'].split('$')
        return salt

    def valid_account(self, number):
        """ Check if this is a valid account number
        """
        if not is_luhn_valid(number):
            return False

        # Take the checksum off, and return the user number
        number = number / 10
        return feistel_number(number)

    def save(self):
        """ Save the current user, increment the user number
        """
        # Is this a new user with no pk or Account get that user number
        if not 'pk' in self and not 'Account' in self:
            try:
                query = USER.select('pk')\
                            .is_not_null('pk')\
                            .order_by('pk')\
                            .reverse()

                last = query.list()[0]
            except Exception, e:
                self['pk'] = 1

            # This is a new user increment the user number
            else:
                self['pk'] = int(last['pk']) + 1

            self['Account'] = self._account_number(self['pk'])

        # Check if the email exist
        item = None
        if self['Email'] is not None:
            try:
                item = self.objects.get(Email=self['Email'])
            except DoesNotExist:
                pass

        # Check if the phone number exists
        if not item and self['Phone'] is not None:
            try:
                item = self.objects.get(Phone=self['Phone'])
            except DoesNotExist:
                pass

        if not item and self['UserName'] is not None:
            try:
                item = self.objects.get(UserName = self['UserName'])
            except DoesNotExist:
                pass

        # Check the Account number
        if not item:
            try:
                item = self.objects.get(Account=self['Account'])
            except DoesNotExist:
                pass

        # Does this already exist?
        data = {k: v for (k, v) in self.items() if self[k] is not None}
        if item:
            data['pk'] = item['pk']
            data['Account'] = item['Account']
            ok = USER.update(self['pk'], data)
        else:
            ok = USER.new(self['pk'], data)

        # If it save return what you saved
        if ok:
            return self
        return None

    def is_active(self):
        return self['Status'] == 'active'

    def is_anonymous(self):
        return False

    def _encrypt(self, salt, message):
        crypt_str = salt + message
        return hashlib.sha256(crypt_str).hexdigest()

    def set_password(self, raw_password):
        salt = uuid4().hex
        crypt_str = self._encrypt(salt, raw_password)
        self['Password'] = '%s$%s' % (salt, self._encrypt(salt, crypt_str))

    def check_password(self, raw_password):
        salt, password = self['Password'].split('$')

        crypt_pass = self._encrypt(salt, raw_password)
        crypt_pass = self._encrypt(salt, crypt_pass)
        return constant_time_compare(crypt_pass, password)

    def __unicode__(self):
        if self['Email']:
            return self['Email']
        elif self['Phone']:
            return self['Phone']
        else:
            return self['Account']

    def update_personal_info(self, lex_id, info):
        self['LexID'] = lex_id
        for (key, attr) in self.id_fields_map.items():
            if key in info:
                self[attr] = info[key].strip().upper()

    def verify_personal_info(self, info):
        changed_fields = list()
        for (key, attr) in self.id_fields_map.items():
            if key in info:
                val = info[key].strip().upper()
                if self[attr] != val:
                    changed_fields.append(attr)
        return bool(changed_fields)

    def add_order(self, orderID):
        if not 'Orders' in self:
            self['Orders'] = [orderID]
        else:
            self['Order'].append( orderID )
        return self

    def add_quote(self, quoteID):
        if not 'Quotes' in self:
            self['Quotes'] = [quoteID]
        else:
            self['Quotes'].append( quoteID )
        return self


class AnonymousUser(object):

    def is_anonymous(self):
        return True

    def is_active(self):
        return False
