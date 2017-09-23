#-------------------------------------------------------------------------------
# Name:        retry.py
# Purpose:     Retry to submit orders that failed to pay customer, due to
#              due to communication problems with an api
#
# Author:      Douma
# Created:     10/07/2013
#-------------------------------------------------------------------------------
import zmq
import time
"""
from models import Database

SDB = Database( config.sdb_amazon_access_key,
                config.sdb_amazon_secret_key
              )

QUEUE = SDB.domain(config.amazon_queue)

"""
def main():

    # Initialize all the task routes
    context = zmq.Context()

    # Set up the listen socket
    lsock = context.socket( zmq.PULL )
    lsock.bind( "tcp://0.0.0.0:5233" )

    poller = zmq.Poller()
    poller.register( lsock, zmq.POLLIN)

    while True:
        socks = dict(poller.poll(10000))
        if socks:
            if socks.get(lsock) == zmq.POLLIN:
                order = lsock.recv_json(zmq.NOBLOCK)
        """
        if queued( order ):
            requeue( order )
        else:
            queue( order )
        """

if __name__ == '__main__':
    main()
