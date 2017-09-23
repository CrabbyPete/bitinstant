#-------------------------------------------------------------------------------
# Name:        virwox.py
# Purpose:     Process virwox actions
#
# Author:      Douma
#
# Created:     11/03/2013
# Copyright:   (c) Douma 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

# Local imports
from config     import VIRWOX
from base       import PartnerProcess
from api.virwox import VirWoxAPI

VirWox = VirWoxAPI( VIRWOX['account'],
                    VIRWOX['password'],
                    VIRWOX['api_key']
                  )

class virwox( PartnerProcess ):
    payment_name  = ['virwoxcoupon']
    exchange_name = ['virwox']
    process_name  = 'virwox'

    def transfer_funds( self, order ):
        """ Transfer funds to virwox account """

        amount = order['AmountToCredit']
        account = order['DestAccount']
        try:
            response = VirWox.moveFunds( account, amount )
        except Exception, e:
            eventtype = 'VirWox API failure'
            params = {'Exception':e}
            return  self.transfer_error ( eventtype, order, requeue = 20, **params )
        
        if 'paymentID' in response:
            return self.order_complete( order, **response )
        else:
            eventtype = 'Virwox Transfer Failed'
            return self.transfer_error ( eventtype, order, requeue = False, **response )

