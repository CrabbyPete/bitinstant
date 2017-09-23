#-------------------------------------------------------------------------------
# Name:        btc.py
# Purpose:     Process transactions to and from btc addresses
#
# Author:      Douma
#
# Created:     11/03/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
#!/usr/bin/env python
from base           import PartnerProcess
from send_event     import requeue_event


class bitcoin( PartnerProcess ):
    payment_name  = ['bitcoin']
    exchange_name = ['bitcoin', 'bitcoinemail']
    process_name  = 'bitcoin'

    def transfer_funds( self, order ):
        """ Process a coinapult transfer for bitcoins """
        # Requeue this for mtgox
        order['eventtype']    = 'Coinapult payment'

        # Put this message on the queue so router sends it to mtgox
        requeue_event( order )

