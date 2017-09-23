#-------------------------------------------------------------------------------
# Name:        paypal.py
# Purpose:     Process paypal payments
#
# Author:      Douma
#
# Created:     11/03/2013
# Copyright:   (c) Douma 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

# Local imports
from base       import PartnerProcess
from config     import VIRWOX
from api.virwox import VirWoxAPI

VirWox = VirWoxAPI( VIRWOX['account'],
                    VIRWOX['password'],
                    VIRWOX['api_key']
                  )

class paypal( PartnerProcess ):
    payment_name  = ['paypal']
    exchange_name = ['paypal']
    process_name  = 'paypal'

    def transfer_funds( self, order ):
        """ Transfer funds to virwox account """

        amount  = order['AmountToCredit']
        account = order['DestAccount']
        try:
            response = VirWox.send_paypal( account, amount )
        except Exception, e:
            eventtype = 'PayPal API failure'
            params = {'Exception': str(e)}
            return self.transfer_error ( eventtype, order, requeue = 20, **response )
            
        if 'paymentID' in response:
            return self.order_complete( order, **response )
        else:
            eventtype = 'Virwox Transfer Failed'
            return self.transfer_error ( eventtype, order, requeue = False, **response )

