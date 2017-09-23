#-------------------------------------------------------------------------------
# Name:        bitstamp.py
# Purpose:
#
# Author:      Douma
#
# Created:     19/03/2012
# Copyright:   (c) Douma 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import urllib
import requests
import json

class BitStampAPI( object ):
    bitstamp_url = "https://www.bitstamp.net/api/"

    def api( self, method, argc, **kwargs ):
        url = self.bitstamp_url + argc + '/'
        if method == 'POST':
            response = requests.post( url, data = kwargs )
        elif method == 'GET':
            response = requests.get( url )
        return response


    def __init__( self, username, password ):
        """
        Initialize class
        """
        self.username = username
        self.password = password

    def getTicker( self ):
        response = self.api('GET', 'ticker')
        return json.loads( response.text )

    def getBalance( self ):
        """
        Returns current USD balance
        return example: {"balance":90.09769988}
        """
        response = self.api( 'POST',
                             'balance',
                             user = self.username,
                             password = self.password
                           )
        return json.loads( response.text )

    def getTransactions( self, timedelta):

        response = self.api( 'POST',
                             'user_transactions',
                             user = self.username,
                             password = self.password,
                             timedelta = timedelta
                           )
        return json.loads( response.text)

    def makeCoupon( self, USD = None, BTC = None ):
        """
        Withdrawing USD to BTCE-Coupon
        parameter: amount=123.04 (amount to withdraw in USD), min amount is 0.01
        on success returns coupon ID
        success return example: {"couponID":"BTCE-USD-RJYLZQ5G-7ML8MDNO-7VC7T10J-0I0DA3G6-PTKT5MPW"}
        error return example: {"error":"not enough funds"}
        """
        kwargs = dict( user = self.username,
                      password = self.password
                    )
        if USD:
            kwargs.update( usd = USD )
        elif BTC:
            kwargs.update( btc = BTC )

        response = self.api( 'POST',
                             'create_code',
                             **kwargs
                           )
        if not 'error' in response.text:
            decode = response.text.replace('"','')
            return {'couponID':decode}
        else:
            return json.loads( response.text )

    def checkCoupon ( self, couponID ):
        """
        Check the amount of coupon
        parameter: couponID= BTCE-USD-RJYLZQ5G-7ML8MDNO-7VC7T10J-0I0DA3G6-PTKT5MPW (coupon id)
        success return example: {"couponAmount":123.04 }
        """
        response = self.api( 'POST',
                             'check_code',
                             user = self.username,
                             password = self.password,
                             code = couponID
                           )
        return json.loads( response.text )



    def redeemCoupon( self, couponID ):
        """
        Redeeming BTCE-Coupon
        parameter: couponID= BTCE-USD-RJYLZQ5G-7ML8MDNO-7VC7T10J-0I0DA3G6-PTKT5MPW (coupon id)
        on success redeeming returns amount of redeemed USD
        success return example: {"couponAmount":123.04 }
        error return example: {"error":"bad coupon id"}
        """
        response = self.api( 'POST',
                             'redeem_code',
                             user = self.username,
                             password = self.password,
                             code = couponID
                           )
        return json.loads( response.text )


    def moveFunds( self, customerID, amount ):
        """
        move funds to a customer account
        parameters: customer_id, amount
        """
        response = self.api ( 'POST',
                              'bitinstant/transfer',
                              user = self.username,
                              password = self.password,
                              customer_id = customerID,
                              USD = float('%.2f' % amount), usd=float('%.2f' % amount), amount=float('%.2f' %amount))
        return response.text
    def withdrawBTC( self, btc_address, amount ):
        """
        withdraw bitcoins
        parameters: userLogin=support (user login at BTC-E);
                    amount=123.04 (amount to move in USD)
        on success moving funds returns result=success
        success return example: {"result":"success" }
        error return example: {"error":"user doesnt exist"}
        """
        response = self.api( 'POST',
                             'bitcoin_withdrawal',
                             user = self.username,
                             password = self.password,
                             address  = btc_address,
                             amount   = amount
                           )
        return response.text

if __name__ == '__main__':
    # Local import
    from config import BITSTAMP
    import sys
    import csv

    bitstamp = BitStampAPI( BITSTAMP['clientID'],
                            BITSTAMP['password']
                          )
    trans_data = bitstamp.getTransactions(9999999999999999999)

    d_w = csv.DictWriter(sys.stdout,trans_data[0].keys())
    print ','.join(trans_data[0].keys())
    d_w.writerows(trans_data)


    sys.exit(0)

    # Get the current ticker
    response = bitstamp.getTicker()
    print response

    # Get the account balance
    response = bitstamp.getBalance()
    print response

    # Force fail test.
    response = bitstamp.makeCoupon()
    print response

    # Error should occur, now do a real one
    if 'error' in response:

        # Make a coupon with a valid value
        response = bitstamp.makeCoupon( USD = 0.02 )
        print response

        # Error should not occur
        if 'error' in response:
            code = None
        elif 'couponID' in response:
            code = response['couponID']

    # Should not hit this
    elif 'couponID' in response:
        code = response['couponID']

    if code:
        # Check the coupon value
        response = bitstamp.checkCoupon( code )
        print response

        # Redeem it
        response = bitstamp.redeemCoupon( code )
        print response

    # Force an error on moving funds
    response = bitstamp.moveFunds( 'xxxxxxx', '0.02')
    print response

    # Move funds to a bitcoin address
    if 'error' in response:

        # Create a BTC This fails if
        response = bitstamp.makeCoupon( BTC = 0.02 )
        print response

        # Move funds to bitcoin address, fail because there are no BTC funds
        if not 'error' in response:
            response = bitstamp.moveFunds( '1Fy9GLWXWMAya8mFaaiYgqxbbgJQW67RUY',
                                           '0.02')
            print response
