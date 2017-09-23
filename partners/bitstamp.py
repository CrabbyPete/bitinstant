#-------------------------------------------------------------------------------
# Name:        bitstamp.py
# Purpose:     Process bitstamp actions
#
# Author:      Douma
#
# Created:     11/03/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
#!/usr/bin/env python
#import zerorpc
import pprint

# Local imports
from config import BITSTAMP
from log    import logger
from base   import PartnerProcess
from api    import bitstamp

"""
API = zerorpc.Client()
API.connect("tcp://127.0.0.1:4242")
"""

BitStamp = bitstamp.BitStampAPI( BITSTAMP['clientID'],
                                  BITSTAMP['password']
                                )

class bitstamp( PartnerProcess ):
    exchange_name = ['bitstamp']
    payment_name =  ['bitstampcoupon']
    process_name =  'bitstamp'

    def process_payment( self, order ):
        """ Process bitstamp coupon """
        #coupon_balance = API.bitstamp_coupon( order['BitstampCoupon'])
        try:
            coupon_balance = BitStamp.checkCoupon(order['BitstampCoupon'])
        except Exception, e:
            eventtype = 'Bitstamp API failure'
            params = {'Exception':e}
            return self.payment_error ( eventtype,
                                        order,
                                        requeue = 20,
                                        **params
                                      )
            
        if 'error' in coupon_balance:
            eventtype = 'Bitstamp coupon failed'
            params = {'CouponValue':str(coupon_balance)}
            return self.payment_error ( eventtype,
                                        order,
                                        requeue = False,
                                        **params
                                      )

        try:
            # bitstamp_resp = API.bitstamp_redeem__coupon(order['BitstampCoupon'])
            bitstamp_resp = BitStamp.redeemCoupon(order['BitstampCoupon'])
        except Exception, e:
            eventtype = 'Bitstamp API failure'
            params = {'Exception':str(e)}
            return self.payment_error( eventtype,
                                       order,
                                       requeue = 20,
                                       **params
                                     )

        if 'usd' in bitstamp_resp:
            usd_amount = float(bitstamp_resp['usd'])
            order['AmountPaid'] = usd_amount
            eventtype = 'Bitstamp coupon deposited at BitInstant account'
            return self.payment_complete( eventtype, order )


        eventtype = 'Bitstamp coupon deposit failed'
        params = {'BitstampResp':bitstamp_resp }
        return self.payment_error( eventtype,
                                   order,
                                   requeue = False,
                                   **params
                                 )


    def transfer_funds( self, order ):
        """ Transfer funds to the bitstamp account """
        #balance = API.bitstamp_balance()
        
        # Check the balance
        try:
            balance = BitStamp.getBalance()
        except Exception, e:
            eventtype = 'Bitstamp API failure'
            params = {'Exception':str(e)}
            return self.payment_error( eventtype,
                                       order,
                                       requeue = 100,
                                       **params
                                     )
        
        if 'usd_balance' in balance:
            if float(balance['usd_balance']) < float( order['AmountToCredit']):
                eventtype = "BitStamp funds low"
                params = {'USDBalance':balance['usd_balance'] }
                return self.transfer_error( eventtype,
                                            order,
                                            requeue = 100
                                            **params
                                          )
        
        # Move funds
        try:
            response = BitStamp.moveFunds( order['DestAccount'],
                                          float( order['AmountToCredit'] )
                                         )
        except Exception, e:
            eventtype = 'Bitstamp API failure'
            params = {'Exception':str(e)}
            return self.transfer_error( eventtype,
                                        order,
                                        requeue = 20,
                                        **params
                                       )
            
        # Check for an error: note they sometimes return html, so trunc it.
        if 'error' in response:
            eventtype = 'Bitstamp transfer failed'
            if not isinstance( response, dict ):
                response = str(response)
                if len( response ) > 200:
                    response = response[0:200]
                response = {'BitstampResponse': str(response) }
            
            return self.transfer_error( eventtype,
                                        order,
                                        requeue = False,
                                        **response
                                       )

        return self.order_complete( order )
