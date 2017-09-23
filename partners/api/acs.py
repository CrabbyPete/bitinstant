#-------------------------------------------------------------------------------
# Name:        Accelerate Commerce Solutions API
# Purpose:
#
# Author:      Douma
#
# Created:     11/12/2012
# Copyright:   (c) Douma 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import sys
import socket
import ssl
import httplib
import base64
import requests
import urllib
import json
import uuid
from ssl import SSLError

from config     import ACS

class ACSError(Exception):
	pass

class HTTPSClientAuthConnection(httplib.HTTPSConnection):

	def __init__( self, host, port, key_file, cert_file, ca_file, timeout=None, ciphers=None ):
		httplib.HTTPSConnection.__init__( self, host, port,
                                          key_file=key_file,
                                          cert_file=cert_file
                                        )
		self.key_file  = key_file
		self.cert_file = cert_file
		self.ca_file   = ca_file
		self.timeout   = timeout
		self.ciphers   = ciphers

	def connect( self ):
		sock = socket.create_connection( ( self.host, self.port ), self.timeout )
		if self._tunnel_host:
			self.sock = sock
			self._tunnel()

		self.sock = ssl.wrap_socket(
									sock,
									self.key_file,
									self.cert_file,
									ca_certs=self.ca_file,
									cert_reqs=ssl.CERT_REQUIRED,
									ciphers = self.ciphers
								   )


class ACSAPI( object ):
    host = 'services.accelerated-commerce.com'
    port = 8289
    url = 'https://%s/disbursements/v1/partner/' % (host,)

    def __init__(self, id, username, password, **files ):
        self.url = self.url + id +'/'
        self.username  = username
        self.password  = password
        self.partnerId = id

        # Change the location of cert & key files
        if 'key_file' in files:
            self.key_file = files['key_file']
        else:
            self.key_file = 'client_key.pem'

        if 'cert_file' in files:
            self.cert_file = files['cert_file']
        else:
            self.cert_file = 'client_cert.pem'

        if 'ca_file' in files:
            self.ca_file = files['ca_file']
        else:
            self.ca_file = 'ca_cert.pem'

        if 'ciphers' in files:
        	self.ciphers = files['ciphers']
        else:
        	self.ciphers = None

        if 'host' in files:
            self.host = files['host']

        if 'port' in files:
            self.port = files['port']

        self.auth = base64.encodestring( self.username + ':' + password )\
                          .replace('\n', '')


    def api( self, method, command, **data ):
        """ Main api to call ACS
            method = GET or POST
            command  = the rest of the url
            data = json data for a POST
        """
        conn = HTTPSClientAuthConnection( self.host,
                                          self.port,
                                          key_file  = self.key_file,
                                          cert_file = self.cert_file,
                                          ca_file   = self.ca_file,
                                          ciphers   = self.ciphers
                                        )

        url = '/disbursements/v1/partners/%s/' % self.partnerId
        if command:
            url += command

        if method == 'GET':
            conn.putrequest( 'GET', url )
            conn.putheader( "Authorization", "Basic %s" % self.auth )
            try:
             	conn.endheaders()
            except SSLError, e:
            	raise ACSError('Error connecting to ACS {}'.format(e))

        else:
            params = json.dumps(data)

            headers = { "Content-type": "application/json;charset=ISO-8859-1",
                        "Authorization":"Basic %s" % self.auth
                      }

            try:
             	conn.request("POST",url, params, headers)
            except SSLError, e:
            	raise ACSError('Error connecting to ACS {}'.format(e))


        response = conn.getresponse()
        reply = response.read()
        result = json.loads( reply )
        return result


    def get_partner( self ):
        """ Get Partner By Partner ID
            GET '/disbursements/v1/partners/<ID>'
        """
        result = self.api('GET',None)
        return result


    def create_user(self, referenceID,
                          user,
                          homeAddress,
                          mailingAddress):
        """ Create User
            POST '/disbursements/v1/partners/<ID>/users'
        """
        if not 'homeAddress' in user:
            user['homeAddress'] = homeAddress
        if not 'mailingAddress' in user:
            user['mailingAddress'] = mailingAddress


        new_user = {'referenceID':referenceID,
                    'user': user
                   }
        result = self.api( 'POST', 'users', **new_user )
        if 'statusCode' in result:
            if result['statusCode'] == 200 or\
               result['statusCode'] == 201   :
                return True, result['userID']
            return False, result
        else:
            return False, result


    def get_user(self, referenceID = None, userID = None):
        """ Get User By User ID or ReferenceID
            GET '/disbursements/v1/partners/<ID>/users/<ID>'
            GET '/disbursements/v1/partners/<ID>/users/?referenceID=<ID>
        """
        if referenceID:
            result = self.api( 'GET', 'users/?referenceID=%s' % referenceID )
        elif userID:
            result = self.api( 'GET', 'users/%s' % userID )
        else:
            return False, None

        if 'statusCode' in result:
            if result['statusCode'] == 200 or\
               result['statusCode'] == 210   :
               if 'userID' in result:
                    return True, result['userID']
               if 'referenceID' in result:
                    return True, result['referenceID']
               return False, None

        return False, result


    def create_account(self, userID,
                             referenceID,
                             accountType,
                             account,
                             statementAddress ):
        """ Create Account
            POST /disbursements/v1/partners/<ID>/users/<ID>/accounts
        """
        if not accountType in ('ach','directConnect','debitCard'):
            print "Error bad accountType {}".format(accountType)
            return False, None

        account = { accountType:account,'statementAddress':statementAddress }

        new_account = { 'referenceID': referenceID,
                        'account': account
                      }


        result = self.api('POST', 'users/%s/accounts'%userID, **new_account )
        if 'statusCode' in result:
            # The account already exists, the account returned, referenceID ingnored
            if result['statusCode'] ==  200:
                return True, result['accountID']

            # The new account is created
            elif result['statusCode'] ==  201:
                return True, result['accountID']

        return False, result

    def get_account(self, userID, accountID = None, referenceID = None ):
        """ Get Account By AccountID
            GET /disbursements/v1/partners/<ID>/users/<ID>/accounts/<ID>
        """
        if accountID:
            url = 'users/%s/accounts/%s/' %(userID, accountID)
        elif referenceID:
            url = 'users/%s/accounts/?referenceID=%s' %( userID, referenceID )

        result = self.api( 'GET', url )
        if 'statusCode' in result:
            if result['statusCode'] == 200:
                if u'referenceID' in result:
                    return True, result[u'referenceID']
                elif u'accountID' in result:
                    return True, result[u'accountID']

        return False, result

    def create_transaction( self, transaction ):
        """ Create Transaction
            POST /disbursements/v1/partners/<ID>/transactions
        """
        result = self.api('POST', 'transactions/', **transaction)
        if 'statusCode' in result:
            if result['statusCode'] == 202:
                if 'transactionID' in result:
                    return True, result['transactionID']

        return False, result

    def get_transaction( self, transactionID = None, referenceID = None):
        if transactionID:
            url = 'transactions/%s/' % transactionID
        elif referenceID:
            url = 'transactions/?referenceID=%s' % referenceID

        result = self.api( 'GET', url )
        if 'statusCode' in result:
            if result['statusCode'] == 200:
                if u'referenceID' in result:
                    return True, result[u'referenceID']
                elif u'transactionID' in result:
                    return True, result[u'accountID']

        return False, result
