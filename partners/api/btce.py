#-------------------------------------------------------------------------------
# Name:        btce.py
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
import time
import hmac
import hashlib
import pprint

class BTCEAPI(object):
    btce_url  = 'https://btc-e.com/couponAPI/'
    btce_trade_url = 'https://btc-e.com/tapi/'

    def __init__(self, username, password, trade_key, trade_secret):
        """
        Intialize BTCEAPI
        """
        self.uid          = username
        self.secret       = password
        self.trade_key    = trade_key
        self.trade_secret = trade_secret

    def hash_hmac( self, msg ):
        """
        Return the encoded msg, with the key using hmac sha512
        """
        result = hmac.new( self.secret, msg, hashlib.sha512 )
        return result.hexdigest()
    def hash_tapi(self,msg):
        result = hmac.new(self.trade_secret, msg, hashlib.sha512)
        return result.hexdigest()


    def tapi(self,method,argc,**kwargs):
        """
        BTC-E trade api interface
        method POST or GET
        argc the function to call
        **kwargs parameters for a POST
        """
        url = self.btce_trade_url + argc + '/'
        kwargs['nonce'] = str(int(time.time()))
        kwargs['method'] = argc
        body = urllib.urlencode(kwargs)
        sign = self.hash_tapi( body )
        headers = dict( Sign = sign, Key = self.trade_key )
        if method == 'POST':
            response = requests.post( url,
                                      data = body,
                                      headers = headers,
                                    )
        elif method == 'GET':
            response = requests.get( url,
                                     headers = headers,
                                   )
        return response.text

    def api( self, method, argc, **kwargs ):
        """
        BTC-E common api interface
        method POST or GET
        argc the function to call
        **kwargs parameters for a POST
        """
        url = self.btce_url + argc + '/'
        body = urllib.urlencode(kwargs)
        sign = self.hash_hmac( body )
        headers = dict( Sign = sign, Uid = self.uid )
        if method == 'POST':
            response = requests.post( url,
                                      data = body,
                                      headers = headers,
                                    )
        elif method == 'GET':
            response = requests.get( url,
                                     headers = headers,
                                   )
        return response.text

    def getBalance( self ):
        """
        Returns current USD balance return example: {"balance":90.09769988}
        """
        response = self.api( 'POST', 'getBalance')
        return json.loads(response)

    def transHistory(self):
        response = self.tapi('POST','TransHistory', count=999999999999999)
        return json.loads(response)

    def makeCoupon( self, amount ):
        """
        Withdrawing USD to BTCE-Coupon
        parameter: amount=123.04 (amount to withdraw in USD), min amount is 0.01
        on success returns coupon ID
        success return example: {"couponID":"BTCE-USD-RJYLZQ5G-7ML8MDNO-7VC7T10J-0I0DA3G6-PTKT5MPW"}
        error return example: {"error":"not enough funds"}
        """
        response = self.api( 'POST', 'makeCoupon', amount = amount )
        return json.loads(response)

    def redeemCoupon( self, couponID ):
        """
        Redeeming BTCE-Coupon
        parameter: couponID= BTCE-USD-RJYLZQ5G-7ML8MDNO-7VC7T10J-0I0DA3G6-PTKT5MPW (coupon id)
        on success redeeming returns amount of redeemed USD
        success return example: {"couponAmount":123.04 }
        error return example: {"error":"bad coupon id"}
        """
        response = self.api( 'POST', 'redeemCoupon', couponID = couponID )
        return json.loads(response)

    def moveFunds ( self, userLogin, amount ):
        """
        Move funds from BitInstant account to another user
        parameters: userLogin=support (user login at BTC-E);
                    amount=123.04 (amount to move in USD)
        On success moving funds returns result = success
        success return example: {"result":"success" }
        error return example: {"error":"user doesnt exist"}
        """
        response = self.api ( 'POST',
                              'moveFunds',
                               userLogin = userLogin,
                               amount    = amount
                            )
        return json.loads(response)

if __name__ == '__main__':
    import csv
    import sys
    import time
    from config import BTC_E

    btce = BTCEAPI( BTC_E['uid'],
                    BTC_E['key'],
                    BTC_E['trade_key'],
                    BTC_E['trade_secret']
                  )


    print btce.getBalance()

    """trans_data = btce.transHistory()
    d_w = csv.DictWriter(sys.stdout,['ID','amount','currency','desc','status','timestamp','type'])
    print 'ID,amount,currency,desc,status,timestamp,type'
    for k,v in trans_data['return'].items():
        row_data = {}
        row_data['ID'] = k
        for _k,_v in v.items():
            if _k=='timestamp':
               row_data[_k] = time.ctime(_v)
            else:
               row_data[_k] = str(unicode(_v).encode('ascii','ignore'))
        d_w.writerow(row_data)
        sys.stdout.flush()"""

    # Make a 2 cent coupon
#    result = btce.makeCoupon('0.02')
#    print result

    # Redeem it back
#    couponID = result['couponID']
    couponID = 'BTCE-USD-5ZVP90L3-ZQXZ22LK-MBIC9HS8-EYLKSYIX-O0RQL22D'
    result = btce.redeemCoupon(couponID)
    print result

    # Move 2 cents
   # result = btce.moveFunds( 'crabbypete', '0.02')
   # print result

    # Move it back
    #result = btce.moveFunds( 'bitinstant', '0.02')
    #print result
