import boto
import json
import uuid
import time
import re
import web
import base64


import config

# This the queue www sends events and the oms reads them
QUEUE = boto.connect_sqs(config.sqs_amazon_access_key,
                         config.sqs_amazon_secret_key)\
            .get_queue(config.amazon_sqs_queue)



def requeue_event( event ):
    body = json.dumps( event )

    message = QUEUE.new_message( body )
    QUEUE.write( message )


def send_event( event, sending_user = None):
    """ Sends and save events to the oms through the sqs queue

        Args:
            event(dict)       : event to be sent to the oms
            sending_user(str) : ip or user name who sent this order
        Returns:
            event_id
        Raises:
            Exception: if save fails
    """
    try:
        from main   import session
    except:
        pass

    event['EventID'] = str( uuid.uuid4() )
    event['EventSentAt'] = time.time()

    try:
        auth = web.ctx.env['HTTP_AUTHORIZATION']
        auth = re.sub('^Basic ', '', auth)
        username, password = base64.decodestring(auth).split(':')
        event['SneakPreviewUser'] = username
    except:
        if sending_user == None:
            sending_user = 'Testing'
        event['SneakPreviewUser'] = sending_user

    try:
        event['ReferID'] = session.get('referer', None)

    except Exception, e:
        print 'Get ReferID Failed: ' + str(e)

    # Save the event to the database and send it to the oms queue
    event.save()
    body = json.dumps( event )

    message = QUEUE.new_message( body )
    QUEUE.write( message )

    return event
