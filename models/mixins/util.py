import os
import time
import re
import calendar
import pytz
from decimal import Decimal
from BeautifulSoup import BeautifulSoup
import requests
import random
from datetime import datetime, timedelta
from email.utils import parsedate_tz
import qrcode


def serialize_object(obj):
    def _dict(d_obj):
        ret = dict()
        d_obj_clean = {k: v for (k, v) in d_obj.items() if not k.startswith('_')}
        for (k, v) in d_obj_clean.items():
            ret[k] = serialize_object(v)
        return ret

    def _list(l_obj):
        ret = list()
        for i in l_obj:
            ret.append(serialize_object(i))
        return ret

    if isinstance(obj, dict):
        ret = _dict(obj)
    elif isinstance(obj, (list, tuple, set)):
        ret = _list(obj)
    elif isinstance(obj, Decimal):
        ret = float(obj)
    elif isinstance(obj, datetime):
        if obj.tzinfo is None:
            dt = pytz.UTC.localize(obj)
        elif obj.tzinfo != pytz.UTC:
            dt = obj.astimezone(pytz.UTC)
        ret = int(calendar.timegm(dt.timetuple())) * 1000
    else:
        ret = obj
    return ret


def camel_to_underscore(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def underscore_to_camelcase(value):
    def camelcase():
        yield str.lower
        while True:
            yield str.capitalize

    c = camelcase()
    return "".join(c.next()(x) if x else '_' for x in value.split("_"))


def lastmod_iso(file_path):
    fs = os.lstat(file_path)
    modtime = time.gmtime(fs.st_mtime)
    subs = dict(year=modtime.tm_year,
                month=modtime.tm_mon,
                day=modtime.tm_mday,
                hour=modtime.tm_hour,
                min=modtime.tm_min)
    return '%(year)s-%(month)02d-%(day)sT%(hour)02d:%(min)02dZ' % subs


def quantize_currency(dec):
    return dec.quantize(Decimal('0.01'))


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


def generate_random_passphrase(length=6):
    choice = random.SystemRandom().choice
    wordlist = get_common_word_list()
    return ' '.join([choice(wordlist) for w in range(length)])


def get_common_word_list():
    import config
    fpath = getattr(config, 'WORDLIST_FILE', 'wordlist.dat')

    def get_list_for_page(strt_hundred, end_hundred):
        ret = list()
        url = 'http://www.paulnoll.com/Books/Clear-English/words-%02d-%02d-hundred.html'
        url %= (strt_hundred, end_hundred)

        r = requests.get(url)
        soup = BeautifulSoup(r.text)
        for l in soup.findAll('ol'):
            for item in l.findAll('li'):
                ret.append(item.text)
        return ret
    if os.path.isfile(fpath):
        with open(fpath, 'r') as fs:
            words = fs.read()
            words = words.split('\n')
    else:
        with open(fpath, 'w') as fs:
            words = list()
            for i in range(1, 30, 2):
                new = get_list_for_page(i, i + 1)
                fs.write('\n'.join(new))
                words.extend(new)

    return words


def to_bool(inp):
    try:
        inp = int(inp)
    except ValueError:
        if isinstance(inp, basestring):
            inp = inp.lower() == 'true'
        else:
            inp = False
    else:
        inp = bool(inp)
    return inp


def to_datetime(datestring):
    time_tuple = parsedate_tz(datestring.strip())
    dt = datetime(*time_tuple[:6])
    return dt - timedelta(seconds=time_tuple[-1])


def generate_btc_address_qrcode(address, amount=None):
    uri = 'bitcoin:%s' % address
    if amount is not None:
        uri = '%s:?amount=%s' % (uri, amount)
    qr = qrcode.QRCode()
    qr.add_data(uri)
    img = qr.make_image()
    return img
