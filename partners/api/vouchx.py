#-------------------------------------------------------------------------------
# Name:        vouchx.py
# Purpose:
#
# Author:      Douma
#
# Created:     19/03/2012
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import requests
import urllib
import json

import hashlib

from config     import VOUCHX

class VOUCHXAPI(object):
    vouchx_url = 'https://www.vouchx.com/api/'

    def __init__(self, merchantId, APIKey ):
        """ Intialize VouchX
        """
        self.merchantId = merchantId
        hash = hashlib.sha1()
        hash.update( merchantId + APIKey )
        self.sha1 = hash.hexdigest()
        pass

    def api( self, method, argc, **kwargs ):
        """ Api interface
            method POST or GET
            argc the function to call
            **kwargs parameters for a POST
        """
        # Append the process to the URL
        url = self.vouchx_url + argc + '/'

        # Concatenate parameters to calculate REST-SIG
        parameters = ""
        for value in kwargs.keys():
            parameters += kwargs[value]

        # Calculate REST-SIG
        hash = hashlib.sha1()
        hash.update( self.sha1 + parameters )
        sha1 = hash.hexdigest()
        headers = { 'REST-ID':self.merchantId, 'REST-SIG':sha1 }

        # Encode parameters
        data = urllib.urlencode(kwargs)

        if method == 'POST':
            response = requests.post( url,
                                      data = data,
                                      headers = headers,
                                    )
        elif method == 'GET':
            response = requests.get( url,
                                     headers = headers,
                                   )
        return response.text

    def create( self, _currency, _amount ):
        """ Create a voucher
        """
        response = self.api( 'POST', 'create', currency = _currency, amount = str(_amount) )
        return json.loads(response)

    def valid( self, voucher ):
        response = self.api( 'POST', 'validate', voucher = voucher )
        return json.loads(response)

    def redeem( self, voucher ):
        response = self.api( 'POST', 'redeem', voucher = voucher )
        return json.loads(response)

    def balance(self):
        response = self.api( 'GET', 'get_balances' )
        return json.loads(response)

    def history(self, currency, start = None, to = None, limit = None, page = None ):
        kwargs = dict( currency = currency )
        if start: kwargs['from']  = start
        if to:    kwargs['to']    = to
        if limit: kwargs['limit'] = limit
        if page:  kwargs['page']  = page

        response = self.api( 'POST', 'get_history', **kwargs )
        return json.loads(response)

if __name__ == '__main__':
    # This is the test in API to show how to calculate SHA1
    #vouchx = VOUCHXAPI('1234','Ksih29u9g92fj')

    vouchx = VOUCHXAPI(VOUCHX['MerchantID'],VOUCHX['APIKey'])
    print vouchx.redeem('VXUSD-7029046398-86820380')

    """
    voucher = vouchx.create('TST', '22.10')

{u'balance': 977.9,
 u'code': 0,
 u'message': u'OK',
 u'transaction_id': 367,
 u'voucher': {u'amount': 22.1,
              u'currency': u'TST',
              u'id': 8139834152L,
              u'string': u'VXTST-8139834152-84891910'}}
    """
    #ok = vouchx.valid('VXTST-8139834152-84891910')
    #print ok

    #ok = vouchx.redeem('VXTST-8139834152-84891910')
    """
    {u'message': u'OK', u'code': 0, u'voucher': {u'currency': u'TST', u'amount': u'22.10', u'id': u'8139834152', u'string': u'VXTST-8139834152-84891910'}}
    {u'balance': u'1000.00', u'message': u'OK', u'code': 0, u'voucher': {u'currency': u'TST', u'amount': u'22.10', u'id': u'8139834152', u'string': u'VXTST-8139834152-84891910'}, u'transaction_id': 368}
    """
    print ok

    balance = vouchx.balance()
    print balance
    history = vouchx.history('TST')
    print history
    pass

