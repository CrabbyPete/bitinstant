#-------------------------------------------------------------------------------
# Name:        base.py
# Purpose:     Define the base class for all task. Some processes need to
#              over written when they are instanciated. payment name, exchange
#              name, and process name MUST be over written
# Author:      Douma
#
# Created:     11/03/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
# System imports

import os
import re
import sys
import zmq
import multiprocessing
import pprint
import json
import time

from log        import logger
from jinja2     import Environment, PackageLoader

# Local imports
from send_event import requeue_event
from models     import Order, OrderExecuted, Generic, User, DoesNotExist
from mail       import Mailer
from util       import serialize_object
import config

MAX_RETRY  = 2
VALIDEMAIL =  "^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"

class PartnerProcess( multiprocessing.Process ):
    """ Task for each exchange running as a separate task
        Overwrite payment name eg. 'mtgoxcoupon' and exchange_name eg. 'mtgox'
        Overwrite payment_process, transfer_funds, and error processing
        Overwrite process_name, only works with Linux using ps -a
    """

    # List of possible payment name methods
    payment_name  = ['payment']

    # List of possible exchange name methods
    exchange_name = ['exchange']

    # The name of this task ( only in linux does it appear if you ps -a )
    process_name  = 'process'

    # These are the email templates for each case, they can be overridden in
    #    each instantiation
    templates = { 'payment_complete': 'payment_complete.tmpl',
                  'payment_error'   : 'payment_error.tmpl',
                  'order_complete'  : 'order_complete.tmpl',
                  'transfer_error'  : 'transfer_error.tmpl'

                }

    def __init__(self, listen_ip, write_ip ):
        """ PartnerProcess
               ip       = ZeroMQ address to listen on
               payment  = Name of payment type ( eg 'mtgoxcoupon' )
               exchange = Exchange or where to pay ( eg 'mtgox' )
        """
        args = (listen_ip,write_ip)
        super( PartnerProcess, self).__init__( args = args )
        self.exit = multiprocessing.Event()

    def run(self):
        """ This gets called when start() is called
        """
        me = multiprocessing.current_process()
        logger.info('INFO :: Starting {} = {}'.format( me.name, me.pid ))
        logger.info('INFO :: Listening on: {} Writing on {}'.format( self._args[0], self._args[1]))
        # Set up Jinja2 template folders
        self.loader = PackageLoader('partners', 'templates')
        self.env = Environment( loader = self.loader )

        # Set up the mailer
        smtp_server       = config.SMTP['server']
        smtp_port         = config.SMTP['port']
        smtp_user         = config.SMTP['user']
        smtp_password     = config.SMTP['password']
        self.from_address = config.SMTP['from_address']

        self.mail = Mailer( user     = smtp_user,
                            password = smtp_password,
                            server   = smtp_server,
                            port     = smtp_port
                          )

        # If this is Linux, change the name of the process to the class name
        if os.name == 'posix':
            import ctypes
            try:
                libc = ctypes.CDLL('libc.so.6')
                libc.prctl(15, self.process_name, 0, 0, 0)
            except OSError:
                pass


        # Initialize all the task routes
        self.context = zmq.Context()

        # Set up the listen socket
        self.lsock = self.context.socket( zmq.PULL )
        self.lsock.bind( self._args[0] )


        # Set up the write socket
        self.wsock = self.context.socket( zmq.PUSH )
        self.wsock.connect( self._args[1] )

        while not self.exit.is_set():
            try:
                order = self.lsock.recv_json()
            except zmq.ZMQError as error:
                print "ZMQ error in {}: {}".format(self.process_name, error)
                continue

            # Check if admin canceled this order
            try:
                db_order = Order.objects.get( OrderID = order['OrderID'] )
            except DoesNotExist:
                logger.info("ERROR :: Order {} not in database".format(order['OrderID']) )
            else:
                if 'OrderCanceled' in db_order:
                    continue
            
            # Check if this is my PayMethod, If a manual only process the destination
            if 'PayMethod' in order and not order['eventtype'] == 'Manual Order': 
                if order['PayMethod'] in self.payment_name:

                    # Check if the was already paid
                    try:
                        status = order['Status']['paid']
                    except:
                        status = False

                    # If not get payment
                    if not status:

                        # If payment fails your done
                        if self.process_payment( order ):
                            self.wsock.send_json( order )

                    # Else send it back to transfer funds ( possible requeue )
                    else:
                        self.wsock.send_json( order )

            # Check the exchange name, or names if its a list
            if 'DestExchange' in order:
                 if order['DestExchange'] in self.exchange_name:
                    self.transfer_funds( order )

        # Signal set to end this process
        return 0

    def terminate(self):
        """ Set an event to tell the process to shut down
        """
        logger.info("INFO :: Exiting {}".format(self.process_name))
        self.exit.set()


    def transfer_funds( self, order ):
        """ Transfer funds to the client.
            OVERWRITE this routine in the specific instance
        """
        sorder = serialize_object(order)
        logger.info("INFO :: Transfering from {} funds...".format(self.exchange_name))
        logger.info("INFO :: Order Details : %s" % json.dumps(sorder))
        return True

    def process_payment( self, order ):
        """ Process a payment from a client
            OVERWRITE this routine in the specific instance
        """
        sorder = serialize_object(order)
        logger.info("Processing payment to {} ...".format(self.payment_name))
        logger.info("INFO :: Order Details : %s" % json.dumps(sorder))
        return True

    def low_funds(self):
        pass

    def printable_time(self, epoch):
        gtime = time.gmtime( float( epoch ))
        return time.strftime("%b %d %Y %H:%M:%S", gtime)

    def email(self, template, subject, order ):
        """ Email user and support
        """

        context = {}
        if 'User' in order:
            try:
                user = User.objects.get( pk = order['User'] )
            except:
                user = None
            
            context.update( user = user )

        if 'EventSentAt':
            epoch = self.printable_time( order['EventSentAt'] )
            context.update( eventat = epoch )

        if 'NotifyEmail' in order and re.match(VALIDEMAIL, order['NotifyEmail'] ):
            template = self.env.get_template( template )
            context.update( order = order )

            mail = template.render( context )
            try:
                return self.mail.email_to( mail,
                                           [ order['NotifyEmail'], 'error@bitinstant.com' ],
                                           self.from_address,
                                           subject)
            except Exception, e:
                logger.error("ERROR :: Mail error in {} {}".format(e, subject))

        return False

    def print_order( self, order ):
        pp = pprint.PrettyPrinter( indent = 4 )
        pp.pprint( order )
        sorder = serialize_object(order)
        logger.info("INFO :: Order Details : %s" % json.dumps(sorder))

    def copy_order( self, record, order, **kwargs ):
        """ Create a new record from the order and extra kwargs
        """
        for key, value in order.items():
            if key == 'eventtype':
                continue

            if key == 'EventID':
                continue

            record[key] = value

        for key, value in kwargs.items():
            record[key] = str( value )

        return record

    def order_complete(self, order, **kwargs):
        """ An order has been completed, create an order executed record and
            inform everyone
        """
        eventtype = 'Order executed'
        logger.info("INFO :: Order executed {}".format(eventtype))
        self.print_order(order)

        executed = OrderExecuted()
        executed = executed.copy_from_order( order, **kwargs )
        executed['EventSentAt'] = time.time()
        executed.save()

        self.print_order( executed )
        self.email(self.templates['order_complete'], 'BitInstant Transaction Successful', order)
        return True

    def payment_complete( self, eventtype, order, **kwargs ):
        """ A payment has completed properly, create a record and send it to
            order processor
            This can be overwritten in the individual instance
        """
        logger.info("INFO :: Payment Complete {}".format(eventtype))
        if not 'Status' in order:
            order['Status'] = { 'paid':True }
        else:
            order['Status'].update( paid = True )

        self.print_order(order)

        record = Generic(eventtype)
        record = self.copy_order( record, order, **kwargs )
        record['EventSentAt'] = time.time()
        record.save()
  
        self.print_order( record )

        self.email( self.templates['payment_complete'], 'BitInstant Payment Confirmed', order )

        return True

    def payment_error(self, eventtype, order, requeue = False, **kwargs ):
        """ An error occured during the payment process, create a record, and
            determine whether to try again
            This can be OVERWRITTEN in the individual instance
        """
        logger.error("ERROR :: Payment Error {}".format( eventtype ))

        record = Generic(eventtype)
        record = self.copy_order( record, order, **kwargs )
        record['EventSentAt'] = time.time()
        record.save()
 
        self.print_order(record)

       # This forces an order to go through even if it failed
        if 'Force' in order:
            return True


        # If we should try again count the number of retries
        if requeue:
            if 'Status' in order:
                if 'payment_retry' in order['Status']:
                    retry = order['Status']['payment_retry'] - 1
                    order['Status'].update( payment_retry = retry )
                else:
                    order['Status'].update( payment_retry = requeue )
            else:
                order.update( Status = dict(payment_retry = requeue) )

            if order['Status']['payment_retry'] > 0:
                requeue_event( order )
                return False


        # This is done, let the user know
        self.email( self.templates['payment_error'], 'BitInstant Payment Error', order )
        return False


    def transfer_error( self, eventtype, order, requeue = False, **kwargs ):
        """ An error occured during the funds tranfer process, create a record,
            and determine whether to try again
            This can be OVERWRITTEN in the individual instance
        """
        logger.error("ERROR :: Transfer Error {}".format( eventtype ))

        record = Generic(eventtype)
        record = self.copy_order( record, order, **kwargs )
        record['eventtype'] = eventtype
        record['EventSentAt'] = time.time()
        record.save()

        self.print_order(record)

        if requeue:
            if 'Status' in order:
                if 'transfer_retry' in order['Status']:
                    retry = order['Status']['transfer_retry'] - 1
                    order['Status'].update( transfer_retry = retry )
                else:
                    order['Status'].update( transfer_retry = requeue )
            else:
                order.update( Status = dict(transfer_retry = requeue) )


            if order['Status']['transfer_retry'] > 0:
                requeue_event( order )
                return False

        self.email( self.templates['transfer_error'], 'BitInstant Transaction Failed', order )

        return False
