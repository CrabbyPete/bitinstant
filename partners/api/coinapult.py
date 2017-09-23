"""
Author: Ira Miller
Copyright Coinapult 2013
"""

import urllib, urllib2, hashlib, hmac, json, time, string, random, requests

class CoinapultClient():
    def __init__(self, credentials, testmode=False):
        self.key = credentials['key']
        self.secret = credentials['secret']
        if not testmode:
            self.rootURL = 'https://merchant.coinapult.com'
        else:
            self.rootURL = 'http://127.0.0.1:8000'

    def sendToCoinapult(self, url, values, sign=False):
        """Send message to URL and return response contents
        Raises CoinapultError"""

        values['timestamp'] = int(time.time())
        values['nonce'] = createNonce(20)
        print self.rootURL + str(url) + "\t" + json.dumps(values)
        #headers = {'Content-type': 'application/x-www-form-urlencoded',
        #           'Accept': 'application/json'}
        headers = {}

        if sign:
            headers['cpt-key'] = self.key
            headers['cpt-hmac'] = generateHmac(values, self.secret)
        data = urllib.urlencode(values)
        req = urllib2.Request(self.rootURL + str(url), data, headers)
        try:
            rawResp = urllib2.urlopen(req)
            jsonResp = rawResp.read()
            return json.loads(jsonResp)
        except urllib2.URLError as e:
            raise CoinapultError("Unable to connect to Coinapult")
        except ValueError:
            raise CoinapultError("Invalid response")

    def receive(self, amount, currency='USD', method='mtgoxCode', instrument='', callback='', **kwargs):
        """Receive money immediately. Use invoice to receive bitcoin from third party."""

        if amount is None or amount <= 0:
            raise CoinapultError('invalid amount')

        url = '/api/t/receive/'
        values = dict(**kwargs)
        values['amount'] = float(amount)
        values['currency'] = currency
        values['method'] = method
        values['instrument'] = instrument
        values['callback'] = callback
        if 'typ' in values:
            values['type'] = values['typ']
            del values['typ']
        print str(url) + "\t" + json.dumps(values)
        resp = self.sendToCoinapult(url, values, sign=True)
        if 'transaction_id' in resp:
            return resp
        elif 'error' in resp:
            raise CoinapultError(resp['error'])
        else:
            raise CoinapultError("unknown response from Coinapult")

    def send(self, amount,
             address,
             currency='BTC',
             typ='bitcoin',
             method='mtgoxCode',
             instrument='',
             callback='',
             **kwargs):
        """Send money."""

        if amount is None or amount <= 0:
            raise CoinapultError('invalid amount')

        if address is None:
            raise CoinapultError('address required')

        url = '/api/t/send/'
        values = dict(**kwargs)
        values['amount'] = float(amount)
        values['currency'] = currency
        values['address'] = str(address)
        values['type'] = typ
        values['callback'] = callback
        values['method'] = method
        values['instrument'] = instrument
        resp = self.sendToCoinapult(url, values, sign=True)
        if 'transaction_id' in resp:
            return resp['transaction_id']
        elif 'error' in resp:
            raise CoinapultError(resp['error'])
        else:
            raise CoinapultError("unknown response from Coinapult")

    def convert(self, amount, inCurrency='USD', outCurrency='BTC', **kwargs):
        """Convert balance from one currency to another."""

        if amount is None or amount <= 0:
            raise CoinapultError('invalid amount')
        elif inCurrency == outCurrency:
            raise CoinapultError('cannot convert currency to itself')

        url = '/api/t/convert/'
        values = dict(**kwargs)
        values['amount'] = float(amount)
        values['inCurrency'] = inCurrency
        values['outCurrency'] = outCurrency
        values = {'amount':float(amount), 'inCurrency':inCurrency, 'outCurrency':outCurrency}
        resp = self.sendToCoinapult(url, values, sign=True)
        if 'transaction_id' in resp:
            return resp['transaction_id']
        elif 'error' in resp:
            raise CoinapultError(resp['error'])
        else:
            raise CoinapultError("unknown response from Coinapult")

    def search(self, transaction_id=None, typ=None, currency=None, to=None, fro=None, **kwargs):
        """Search for a transaction by common fields"""
        url = '/api/t/search/'

        values = {}
        if transaction_id is not None:
            values['transaction_id'] = transaction_id
        if typ is not None:
            values['type'] = typ
        if currency is not None:
            values['currency'] = currency
        if to is not None:
            values['to'] = to
        if fro is not None:
            values['from'] = fro

        if len(values) == 0:
            raise CoinapultError('no search parameters provided')

        resp = self.sendToCoinapult(url, values, sign=True)
        if 'error' in resp:
            raise CoinapultError(resp['error'])
        else:
            return resp

    def getExchangeRates(self):
        """Get exchange rates."""

        url = '/api/getRates/'
        return self.sendToCoinapult(url, {})

class CoinapultError(Exception):
    def __init__(self, message):
        self.error = message
    def __str__(self):
        return self.error

def generateHmac(message, secret):
    """Encodes message as compact JSON (no whitespace)
    Then generate an SHA512 hashed HMAC of the message, using supplied key
    Returns HMAC"""
    formattedMess = {}
    for k in message:
        formattedMess[k] = str(message[k])
    jMessage = json.dumps(formattedMess, sort_keys=True, separators=(',',':'))
    mac = ""
    return hmac.new(str(secret), jMessage, hashlib.sha512).hexdigest()

def createNonce(length = 20):
    soup = string.ascii_letters + string.digits
    rString = ""
    for i in range(0, length):
        rString = rString + random.choice(soup)
    return rString