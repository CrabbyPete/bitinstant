#-------------------------------------------------------------------------------
# Name:        acs.py
# Purpose:     Process transactions to and from btc addresses
#
# Author:      Douma
#
# Created:     11/03/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import      pdb
import      pprint
import      config
import      uuid
import json

from base       import PartnerProcess
from api.acs    import ACSAPI
from log import logger

ACS = ACSAPI( config.ACS['PartnerID'],
              config.ACS['Username'],
              config.ACS['Password'],
              **config.ACS
            )

# Do this to test the connection.
#partner = ACS.get_partner()


class acs( PartnerProcess ):
    payment_name  = 'acs'
    exchange_name = ['acsbank','acsdebit']
    process_name  = 'acs'

    def transfer_funds( self, order ):
        """ Transfer funds to the client.
            OVERWRITE this routine in the specific instance
        """
        logger.info("INFO :: Transfering from {} funds...".format(self.exchange_name))
        logger.info("INFO :: Order details : %s" % json.dumps(order))

        # Make sure you have the AccountID, the get the account id from the db
        if 'ACSUserReference' in order:
            ok, user = ACS.get_user(referenceID = order['ACSUserReference'])


        if 'ACSAccountID' in order:
            ok, account = ACS.get_account( user,
                                           referenceID = order['ACSAccountID']
                                         )


        # Create a new transaction ID and translate amount into cents
        transactionReference = uuid.uuid4().hex
        amount = int( float( order['AmountToCredit'] ) * 100.00 )

        transaction = dict( referenceID = transactionReference,
                            sourceAccountID = config.ACS['account'],
                            destinationAccountID = account,
                            amount = amount,
                            executeTransfer = True # Sandbox only
                          )

        try:
            ok, transaction_id = ACS.create_transaction( transaction )
        except Exception,e:
            logger.error('ERROR :: ACS connection failure: {}'.format(e))
            eventtype = 'ACS connection failure'
            return self.transfer_error( eventtype, order, requeue = False )

        if ok:
            kwargs = { 'ACSTransactionReference':transactionReference }

            return self.order_complete( order, **kwargs )

        eventtype = 'ACS tranfer failure'
        return self.transfer_error( eventtype,
                                    order,
                                    requeue = False,
                                    **transaction_id
                                  )
