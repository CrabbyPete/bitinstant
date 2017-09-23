#-------------------------------------------------------------------------------
# Name:        btce.py
# Purpose:
#
# Author:      Douma
#
# Created:     19/03/2012
#-------------------------------------------------------------------------------
#!/usr/bin/env python

# Local imports
import config
from base   import PartnerProcess
from api    import btce

BtcE = btce.BTCEAPI( config.BTC_E['uid'],
                      config.BTC_E['key'],
                      config.BTC_E['trade_key'],
                      config.BTC_E['trade_secret']
                   )


class btce( PartnerProcess ):
    payment_name  = 'btcecoupon'
    exchange_name = 'btce'
    process_name  = 'btce'

    def process_payment( self, order ):
        if not 'USD' in order['BTCECoupon']:
            eventtype = 'BTC-E coupon failed'
            return self.payment_error ( eventtype,
                                        order,
                                        requeue = False
                                      )

        try:
            btce_resp = BtcE.redeemCoupon(order['BTCECoupon'])
        except Exception,e:
            eventtype = 'BTC-E API failure'
            params = {'Exception':str(e)}
            return self.payment_error ( eventtype,
                                        order,
                                        requeue = False,
                                        **params
                                      )

        if btce_resp.has_key('couponAmount'):
            usd_amount = float(btce_resp['couponAmount'])
            order['AmountPaid'] = usd_amount
            eventtype = 'BTC-E coupon deposited at BitInstant account'
            return self.payment_complete( eventtype, order )


        eventtype = 'BTC-E coupon deposit failed',
        params = { 'BTCEResp':btce_resp }
        return self.payment_error ( eventtype,
                                    order,
                                    requeue = False,
                                    **params
                                  )

    def transfer_funds(self, order):
        account = order['DestAccount'],
        amount  = order['AmountToCredit']
        return BtcE.moveFunds( account, amount )


if __name__ == '__main__':
    pass
