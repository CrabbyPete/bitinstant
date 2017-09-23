#-------------------------------------------------------------------------------
# Name:        vouchx.py
# Purpose:     Process vouchx transactions
#
# Author:      Douma
#
# Created:     11/03/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
#!/usr/bin/env python

# Local imports
from config     import VOUCHX
from base       import PartnerProcess

from api.vouchx import VOUCHXAPI

VouchX = VOUCHXAPI( VOUCHX['MerchantID'],
                    VOUCHX['APIKey']
                  )

class vouchx( PartnerProcess ):
    payment_name  = ['vouchxcoupon']
    exchange_name = ['vouchx']
    process_name  = 'vouchx'


    def process_payment( self, order ):
        if not 'USD' in order['VouchXCoupon']:
            eventtype = 'VouchX coupon failed'
            return self.payment_error ( eventtype ,
                                        order,
                                        requeue = False
                                      )
        try:
            vouchx_resp = VouchX.redeem(order['VouchXCoupon'])
        except Exception,e:
            params = {'Exception':str(e)}
            eventtype = 'VouchX API failure'
            return self.payment_error ( eventtype,
                                        order,
                                        requeue = False,
                                        **params
                                      )


        if vouchx_resp['voucher'].has_key('amount') and \
           vouchx_resp['message'] == 'OK':

            usd_amount = float(vouchx_resp['voucher']['amount'])
            order['AmountPaid'] = usd_amount
            params = { 'CouponValue':vouchx_resp['voucher']['amount']}
            return self.payment_complete( order, **params )

        params = {'VouchXResp':vouchx_resp,
                  'Coupon':order['VouchXCoupon']
                 }

        eventtype = 'VouchX coupon deposit failed'
        return self.payment_error( eventtype,
                                   order,
                                   requeue = False,
                                   **params
                                 )

    def transfer_funds( self, order):
        amount = order['AmountToCredit']
        return VOUCHX.create('USD', str(amount))
