#-------------------------------------------------------------------------------
# Name:        mtgox.py
# Purpose:     Process mtgox actions
#
# Author:      Douma
#
# Created:     11/03/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import pprint

# Local imports
from config     import MTGOX, COINAPULT
from base       import PartnerProcess
from api.mtgox  import GoxAPI

from api.coinapult  import CoinapultClient, CoinapultError

BitCoin = CoinapultClient({'key'   :COINAPULT['key'] ,
                           'secret':COINAPULT['secret']
                         })

MtGox = GoxAPI( MTGOX['api_key'], MTGOX['secret'] )

PP = pprint.PrettyPrinter()

class mtgox( PartnerProcess ):
    payment_name  = ['mtgoxticket']
    exchange_name = ['mtgox','bitcoinemail','bitcoin']
    process_name  = 'mtgox'


    def check_ticket(self, order ):
        """ Check the Mtgox ticket
            Catch exceptions in process_payment
        """
        ticket_valid = MtGox.check_ticket( order['MtgoxParams'] )
        if not 'error' in ticket_valid:
            if 'result' in ticket_valid and ticket_valid['result'] == 'success':
                if ticket_valid['return']['amount']['currency'] == 'USD':
                        return True, ticket_valid

        return False, ticket_valid


    def process_payment( self, order ):
        """ Process MtGox Tickets """

        # Check if the ticket is good
        try:
            ok, ticket = check_ticket( order['MtgoxParams'] )
        except Exception, e:
            ok = False
            ticket = { 'Exception':e }

        # Catch error and exceptions
        if not ok:
            eventtype = "MtGox ticket failed"
            return self.payment_error( eventtype, order, **ticket )

        # The ticket is good, process it
        try:
            ticket = MtGox.settle_ticket(ticket)
        except Exception, e:
            eventtype = 'MtGox settle failed'
            return self.payment_error( eventtype, order, **ticket )

        return self.order_complete( order, **ticket )

    def transfer_funds( self, order ):
        """ Directly transfer fund into an account """

        # If this came for coinapult, just use coinapults account number
        if order['eventtype'] == 'Coinapult payment':

            # If you requeue and mtgox is already paid don't do it again
            if 'Status' in order and 'mtgox_paid' in order['Status']:
                return self.send_to_coinapult( order )

            # Set the user_id so you don't have to do a get_user_id
            user_id = COINAPULT['account']

        # Otherwise get the real account number
        elif order['DestAccount'][0]  == 'M' and order['DestAccount'][-1] == 'X':
            dest_account = order['DestAccount'][3:-1]
                
            # Get the user id
            try:
                retval = MtGox.get_user_id(dest_account)
            except Exception, e:
                retval = str(e)
                user_id = None
            
            else:
                try:
                    user_id = retval['return']['user_id']
                except:
                    user_id = None

        # If you did not get a user id, there's a problem
        if not user_id:
            eventtype = "MtGox account error"
            params =  {'retval':retval}
            return self.transfer_error( eventtype,
                                        order,
                                        requeue = 300,
                                        **params
                                       )

        amount = float( order['AmountToCredit'] )
        try:
            retval = MtGox.direct_transfer( user_id,
                                            amount,
                                            'Bitinstant transfer: ' + str( order['OrderID'] ),
                                            order['OrderID']
                                          )
        except Exception, e:
            retval = {'error':'MTGox Exception ' + str(e)}

        
        params = {'retval':retval}
        if 'error' in retval:
                eventtype = 'MtGox tranfer error  '
                return self.transfer_error( eventtype,
                                            order,
                                            requeue = 300,
                                            **params
                                          )

        #PP.pprint( retval )
        
        # If its not coinapult order you are done
        if not order['eventtype'] == 'Coinapult payment':
            return self.order_complete( order, **params )

        # Otherwise tell coinaplult about the MtGox transaction
        if 'return' in retval and 'xfer' in retval['return']:
            order['GoxTransactionID'] = retval['return']['xfer']
        else:
            eventtype = "Coinapult MtGox error"
            return self.tranfer_error( eventtype, order, requeue = False, **retval )

        # Save the payment status
        if 'Status' in order:
            order['Status'].update( mtgox_paid = True )
        else:
            order.update( Status = dict(mtgox_paid = True)  )

        # Send to mtgox
        return self.send_to_coinapult( order )

    def send_to_coinapult(self, order ):
        """ Handle coinapult transactions here
            Funds are first transfer via MtGox from BI to Coinapult once complete
            a transaction ticket is sent to coinapult showing the transaction
        """

        # Get the PIN if any and mtgox transaction ID
        if 'PIN' in order:
            pin = order["PIN"]
        else:
            pin = None

        try:
            reply = BitCoin.send( amount     = order['AmountToCredit'],
                                  address    = order['DestAccount'],
                                  currency   ='BTC',
                                  typ        ='bitcoin',
                                  method     ='MtGoxTransId',
                                  instrument = order['GoxTransactionID'],
                                  extOID     = order['OrderID'],
                                  pin        = pin
                               )

        except Exception, e:
             eventtype = 'Coinapult error'
             params = {'Exception': e}
             return self.transfer_error(  eventtype,
                                          order,
                                          requeue = False,
                                          **params
                                       )

        trans_id = {'TransactionID':reply}
        #PP.pprint ( trans_id )
        
        return self.order_complete( order, **trans_id )