import urllib2, time, base64, json, pprint, math
from urllib import urlencode
from hashlib import sha512
from hmac import HMAC

def get_nonce():
    return int(time.time()*100000)

def sign_data(secret, data):
    return base64.b64encode(str(HMAC(secret, data, sha512).digest()))
      
class requester:
    def __init__(self, auth_key, auth_secret):
        self.auth_key = auth_key
        self.auth_secret = base64.b64decode(auth_secret)
        
    def build_query(self, req={}, public=False):
        if not public: req["nonce"] = get_nonce()
        post_data = urlencode(req)
        headers = {}
        headers["User-Agent"] = "GoxApi"
        if not public:
            headers["Rest-Key"] = self.auth_key
            headers["Rest-Sign"] = sign_data(self.auth_secret, post_data)
        return (post_data, headers)
        
    def perform(self, url, args,public=False):
        try:
            data, headers = self.build_query(args, public)
            req = urllib2.Request(url, data, headers)
            #print '\n urllib.request url: ' + str(url) + ' data: ' + str(data) + ' headers: ' + str(headers)
            res = urllib2.urlopen(req, data)
            resp = json.load(res)
            if 'error' in resp:
                resp = {'error':'Mtgox 200 error' + str(resp)}
            return resp
        except urllib2.HTTPError as e:
            response_code = e.code
            contents = e.read()
            return {'error':'Mtgox http error: ' + str(contents) + ' Code: ' + str(response_code)}
        except urllib2.URLError as e:
            reason = e.reason
            return {'error':'Mtgox url error: ' + str(reason)}
        except Exception as e:
            return {'error':'Mtgox general error: ' + str(e)}

class GoxAPI:
    
    def __init__(self,auth_key,auth_secret):
        self.requester = requester(auth_key,auth_secret)
    
    def get_balance(self):
        retval = self.requester.perform('https://mtgox.com/api/0/info.php',{})
        if not retval.has_key('Wallets'): return None
        if not retval['Wallets'].has_key('USD'): return None
        return retval['Wallets']['USD']['Balance']['value']
    
    def get_coupon(self,amount,currency):
        if currency=='USD':
            retval = self.requester.perform('https://mtgox.com/code/withdraw.php',{'group1':'USD2CODE','amount':amount})
        elif currency=='BTC':
            retval = self.requester.perform('https://mtgox.com/code/withdraw.php',{'group1':'BTC2CODE','amount':amount})
        if not retval.has_key('code'):
            return retval
        return retval['code']
    
    def deposit_coupon(self,code):
        retval = self.requester.perform('https://mtgox.com/api/0/redeemCode.php',{'code':code})
        if not retval.has_key('amount'): return {'error':retval}
        return retval
    
    def get_user_id(self,user):
        retval = self.requester.perform('https://mtgox.com/api/1/generic/private/user/locate',{'index':user,'realm':9})
        #print '\n\nretval1: ' + str(retval)#debug
        if str(retval).count('error') > 0: 
            retval = self.requester.perform('https://mtgox.com/api/1/generic/private/user/locate',{'index':user,'realm':9})
        elif str(retval).count('error') > 0:
            retval = self.requester.perform('https://mtgox.com/api/1/generic/private/user/locate',{'login':user,'realm':9})
        elif str(retval).count('error') > 0:
            retval = self.requester.perform('https://mtgox.com/api/1/generic/private/user/locate',{'login':user,'realm':9})
            #print '\n\nretval2: ' + str(retval)#debug
        return retval
    
    def direct_transfer(self,user_id,amount,description,OrderID=None):
        if not OrderID:
            OrderID = description
        currency_info = self.requester.perform('https://mtgox.com/api/1/generic/public/currency',{'currency':'USD'},public=True)['return']
        #print '\n\n currency_info: ' + str(currency_info)
        retval = self.requester.perform('https://mtgox.com/api/1/generic/private/token/process',{'user':user_id,
                                                                                                 'amount':amount*float(math.pow(10,float(currency_info['decimals']))),
                                                                                                 'currency':'USD',
                                                                                                 'description':description,
                                                                                                 'user_key':OrderID})
        #print '\n\n retval: ' + str(retval)        
        return retval
    
    def check_ticket(self,ticket):
        try:
            retval = self.requester.perform('https://mtgox.com/api/1/generic/ticket/get',ticket)
            return retval
        except Exception as e:
            print 'MTGox check_ticket Error: ' + str(e)
    
    def settle_ticket(self,ticket):
        try:
            ticket['description']='Payment to Bitinstant. BI QuoteID: ' + str(ticket['data'])
            retval = self.requester.perform('https://mtgox.com/api/1/generic/ticket/settle',ticket)
            return retval
        except Exception as e:
            print 'MTGox settle_ticket Error: ' + str(e)
            
    def check_settled(self,ticket):
        try:
            history = self.requester.perform('https://data.mtgox.com/api/1/generic/private/wallet/history',{'currency':'USD', 'type':'in', 'page':'1'})['return']['result']
            retval = {'status':'Not found','ticket':'Not found','message':'','quoteid':'Not Found'}
            for item in history:
                item_ticket = item['Info'].split('ticket ')[1].split('\n')[0]
                item_message = item['Info'].split('\n')[1]
                item_quoteid = item['Info'].split(' ')[-1]
                item_amount = item['Value']['value']
                
                print 'item_ticket: ' + str(item_ticket)
                print 'item_message: ' + str(item_message)
                print 'history item: ' + str(item)
                print 'item_amount: ' + str(item_amount)
                print 'item_quoteid: ' + str(item_quoteid) + '\n'
                
                if item_ticket == str(ticket['ticket']):
                    retval['status'] = 'settled'
                    retval['ticket'] = str(item_ticket)
                    retval['message'] = item_message
                    retval['amount'] = item_amount 
                    
                    if item_quoteid == str(ticket['data']):
                        retval['quoteid'] = item_quoteid
                    break
                
            return retval
        
        except Exception as e:
            print 'MTGox check_settled Error: ' + str(e)
    
    #===========================================================================
    # def token_transfer(self,token,amount,description):
    #    currency_info = gox_requester.perform('https://mtgox.com/api/1/generic/public/currency',{'currency':'USD'},public=True)
    #    retval = gox_requester.perform('https://mtgox.com/api/1/generic/private/token/process',{'token':token,
    #                                                                                            'amount':amount*math.pow(10,currency_info['decimals']),
    #                                                                                            'currency':'USD',
    #                                                                                            'description':description})
    #    return retval
    #===========================================================================

if __name__=='__main__':
 
    api_url='https://mtgox.com/api/1/generic/private/token/process'
    query = {'token':raw_input('Gox Token: ').strip('\n'),
             'amount':float(raw_input('Amount to transfer: ').strip('\n')),
             'currency':'USD',
             'description':raw_input('Comment: ').strip('\n')}

    #===========================================================================
    # print run_gox_transfer(query['token'],query['amount'],query['description'])
    #===========================================================================
    
