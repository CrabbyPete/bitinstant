import calendar
import pytz
from decimal import Decimal
from datetime import datetime


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
