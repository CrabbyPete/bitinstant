#-------------------------------------------------------------------------------
# Name:        payment router.py
# Purpose:     Route messages off the queue to individual payment processes
#
# Author:      Douma
#
# Created:     30/03/2013
# Copyright:   (c) Douma 2013
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import json
import zmq
import boto
import inspect
import signal

from time  import sleep
from log   import logger

# Local imports
import config
import partners
from log import logger
from util import serialize_object


#-------------------------------------------------------------------------------
# Define a ZeroMQ routing table for each task based on the exchange where
# funds are being transfered to
# Note: partners __init__ must have the partner api interface
#-------------------------------------------------------------------------------
RoutingTable = {
    'bitstamp': { 'ip':"tcp://127.0.0.1:5001", 'sockt': None, 'task': None },
    'fuze'    : { 'ip':"tcp://127.0.0.1:5002", 'sockt': None, 'task': None },
    'zipzap'  : { 'ip':"tcp://127.0.0.1:5003", 'sockt': None, 'task': None },
    'mtgox'   : { 'ip':"tcp://127.0.0.1:5004", 'sockt': None, 'task': None },
    'btce'    : { 'ip':"tcp://127.0.0.1:5005", 'sockt': None, 'task': None },
    'vouchx'  : { 'ip':"tcp://127.0.0.1:5006", 'sockt': None, 'task': None },
    'paypal'  : { 'ip':"tcp://127.0.0.1:5007", 'sockt': None, 'task': None },
    'dwolla'  : { 'ip':"tcp://127.0.0.1:5008", 'sockt': None, 'task': None },
    'bitcoin' : { 'ip':"tcp://127.0.0.1:5009", 'sockt': None, 'task': None },
    'acs'     : { 'ip':"tcp://127.0.0.1:5010", 'sockt': None, 'task': None },
    'virwox'  : { 'ip':"tcp://127.0.0.1:5011", 'sockt': None, 'task': None }
}

def check_table( method ):
    """ Check routing table for a method, look for conjuntions such as
        mtgoxcoupon as well
    """
    # If a method is the table return it
    if method in RoutingTable:
        logger.info('INFO :: Sending {}'.format(method))
        return RoutingTable[method]


    # If not directly in the table it may be a conjunctions like mtgoxcoupon
    for exchange in RoutingTable.keys():
        if method.startswith( exchange ):

            logger.info('Sending {} -> {}'.format( method, exchange ))
            return RoutingTable[exchange]

    logger.error("ERROR :: Unknown method {}".format( method ))
    return None


def new_order( order ):
    """ Process messages where the eventtype = 'New Order'
    """
    method = order['PayMethod']
    exchange = check_table( method )
    if exchange:
        exchange['sockt'].send_json( order )


def process_transfer( order ):
    """ Tranfer funds after payment received
    """
    method = order['DestExchange']
    exchange = check_table( method )

    if exchange:
        exchange['sockt'].send_json( order )


def manual_order( order ):
    """ Just do the transfer on a Manual Order eventtype """
    return process_transfer( order )


def coinapult_payment( order ):
    """ Just send a coinapult payment request to mtgox """
    RoutingTable['mtgox']['sockt'].send_json( order )

def subscription( message ):
    pass


def force_order( order ):
    process_transfer ( order )

def lr_status( message ):
    pass

def virwox_payment( message ):
    pass

def dumpit( message ):
    """
    Ignore these messages
    """
    pass


# Define the Eventtype we can get off the Amazon Queue
EVENTTYPE = {
    'New Order'                         : new_order,
    'Coinapult payment'                 : coinapult_payment,
    'Subscription added'                : dumpit,
    'Order retry requested'             : new_order,
    'Forcing order repeat'              : force_order,
    'Manual Order'                      : manual_order,
    'LR Status update'                  : dumpit,
    'Received payment data from VirWox' : virwox_payment,
    'Quote for new transaction'         : dumpit,
    'Manual transfer created'           : dumpit,
    'Command'                           : dumpit
}

# Define the IP address for tasks to send completed payments
EXCHANGE_ROUTER_IP  = "tcp://127.0.0.1:5222"


def start_tasks( name = None):
    """ Start tasks in the RoutingTable.
        if name = None, start them all otherwise start a specific one
    """
    if not name:
        for module in inspect.getmembers( partners, inspect.isclass):
            if module[0] in RoutingTable:

                # process( listen_ip, writeto_ip )
                process = module[1]( RoutingTable[module[0]]['ip'],
                                     EXCHANGE_ROUTER_IP
                                   )

                process.daemon = True
                process.start()
                RoutingTable[module[0]]['task'] = process
                sleep(.01)

    elif name in RoutingTable:
        try:
            module = getattr( partners, name)
        except AttributeError:
            logger.error("ERROR :: Unknown task %s" % name)
            return

        process = module( RoutingTable[name]['ip'], EXCHANGE_ROUTER_IP )
        process.daemon = True
        process.start()
        RoutingTable[name]['task'] = process
        return process.pid

def shut_down(signal, func = None ):
    """ Shut down gracefully, make sure all processing is complete before
        before killing
    """
    for key,value in RoutingTable.items():
        try:
            if value['task'].is_alive():
                value['task'].terminate()
        except Exception, e:
            logger.error("ERROR :: Error exiting {}:{}".format(key, e))
            pass

    while True:
        null = {}
        for key in RoutingTable.keys():
            RoutingTable[key]['sockt'].send_json( null )
            if RoutingTable[key]['task'].is_alive():
                sleep(.1)
                break
        else:
            exit(0)


    print "Goodbye"
    exit()


def main():
    """ Start to process orders
    """

    # Start reading off the Amazon Queue
    conn = boto.connect_sqs( config.sqs_amazon_access_key,
                             config.sqs_amazon_secret_key
                           )

    queue = conn.get_queue(config.amazon_sqs_queue)

    # Start a ZeroMQ context
    context = zmq.Context()

    # Initialize all the task routes
    for process in RoutingTable.keys():
        sock = context.socket(zmq.PUSH)
        sock.connect(RoutingTable[process]['ip'])
        RoutingTable[process]['sockt'] = sock

    # Start the Exchange Router IP
    sock = context.socket(zmq.PULL)
    sock    = context.socket( zmq.PULL )
    sock.bind( EXCHANGE_ROUTER_IP )

    # Start up all the clients & set up the exit handler
    start_tasks()

    # Catch an interupt signal and shutdown nice
    signal.signal(signal.SIGINT, shut_down  )
    signal.signal(signal.SIGTERM, shut_down )

    # Read off the Amazon Queue and send it to the right processor for payment
    # Timeout after 1 sec to check for incoming messages
    while True:
        try:
            msg = queue.read( wait_time_seconds = 1 )
        except Exception, e:
            logger.error('ERROR :: Error reading queue:{}'.format(e))

        # See what message you got and send to the processor
        else:
            if msg:
                message  = json.loads( msg.get_body())
                logger.info('INFO :: Got message {}'.format(message['eventtype']))
                try:
                    EVENTTYPE[ message['eventtype'] ](message)
                except KeyError:
                    logger.error('Unknown eventtype: %s'%(message['eventtype']))

                msg.delete()

        # Check the incoming socket for order processed for payment
        # Don't block, read them at the timeout rate set for the Amazon queue
        try:
            order = sock.recv_json( flags = zmq.NOBLOCK )

        # No message causes an ZMQError
        except zmq.ZMQError:
            pass

        # Someone is done processing payment, now transfer funds
        else:
            process_transfer( order )

        # Check all tasks and make sure they are still alive
        for key,value in RoutingTable.items():
            try:
                # if a process died, restart it
                if not value['task'].is_alive():
                    logger.warn('WARN :: %s DIED, ATTEMPTING RESTART'%( value['task'].name ))
                    start_tasks( key )

            except Exception, e:
                logger.error("ERROR :: Error trying to start {}: {}".format(key, e))


if __name__ == '__main__':
    main()
