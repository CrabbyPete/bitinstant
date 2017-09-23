#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Douma
#
# Created:     06/05/2013
# Copyright:   (c) Douma 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import pdb
import uuid
import requests
import json

class VirWoxAPI( object ):
    url = 'https://www.virwox.com/api/payment.php'

    def __init__( self, account, password, api_key ):
        self.account  = account
        self.password = password
        self.api_key = api_key,

    def moveFunds( self, account, amount, token = None ):
        if not token:
            query = { 'method'       :'requestPayment',
                      'key'          : self.api_key,
                      'recipientName': account,
                      'amount'       : amount,
                      'currency'     : 'USD',
                      'description'  : 'Bitinstant transfer',
                      'paymentType'  : 'OTHER',
                      'id'           : str(uuid.uuid4())
                    }

            response = requests.post( self.url, data = query )
            if response.status_code == 200:
                reply = json.loads( response.text )
                if 'result' in reply:
                    result = reply['result']
                    if 'errorCode' in result and result['errorCode'] == 'OK':
                        token = result['token']

        if token:
            query = { 'method'  :'authorizePayment',
                      'key'     : self.api_key,
                      'username': self.account,
                      'password': self.password,
                      'token'   : token,
                      'id'      : str(uuid.uuid4())
                    }
            response = requests.post( self.url, data = query )
            if response.status_code == 200:
                reply = json.loads( response.text )
                if 'result' in reply:
                    result = reply['result']
                    if  'errorCode' in result and result['errorCode'] == 'OK':
                        return { 'paymentID' :result.get('paymentID', None),
                                 'id': query['id']
                               }
        try:
            return json.loads( response.text )
        except:
            return None

    def send_paypal(self,account, amount, comment = None ):
        """ Send to paypal via VirWox """
        
        query = {  'method'         : 'requestPayment',
                   'key'            : self.api_key,
                   'recipientName'  : 'bitinstant',
                   'amount'         : amount,
                   'currency'       :'USD',
                   'description'    : comment,
                   'paymentType'    :'OTHER',
                   'targetType'     :'PAYPAL',
                   'withdrawTo'     : account,
                   'id'             : str(uuid.uuid4())
                }
        
        response = requests.post( self.url, data = query )
        token = None
        
        if response.status_code == 200:
            reply = json.loads( response.text )
            if 'result' in reply:
                result = reply['result']
                if 'errorCode' in result and result['errorCode'] == 'OK':
                        token = result['token']

        if token:
            query = { 'method'   :'authorizePayment',
                      'key'      : self.api_key,
                      'username' : self.account,
                      'password' : self.password,
                      'token'    : token,
                      'id'       : str(uuid.uuid4())
                    }

            response = requests.post( self.url, data = query )
            if response.status_code == 200:
                reply = json.loads( response.text )
                if 'result' in reply:
                    result = reply['result']
                    return result
        
        try:
            return json.loads( response.text )
        except:
            return None       

def main():
    pass

if __name__ == '__main__':
    virwox = VirWoxAPI( VIRWOX['account'],
                        VIRWOX['password'],
                        VIRWOX['api_key']
                      )
    response = virwox.moveFunds( 'CrabbyPete',
                                 1
                               )
    print response
    #u'{"result":{"errorCode":"OK","token":"c65e182a-b8a6-11e2-9089-6c626dd90a95"},"error":null,"id":"65b850b4-29ec-49c1-af63-74f8699259c6"}'