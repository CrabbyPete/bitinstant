from datetime import datetime
import pytz

from models import STD
import config


class NewsManager(object):

    def latest(self):
        """ Get all SystemStatus records
        """
        query = STD.select('*')

        item = query.where({'table': 'SystemStatus'}, '=')\
                    .like('itemName()', '%')\
                    .order_by('itemName()')\
                    .reverse()\
                    .first()
        # Check that you got an item
        if not item:
            item = {'StatusMsg': config.DEFAULT_STATUS_MESSAGE}
        return News(item)


class News(dict):

    objects = NewsManager()

    def __init__(self, *args, **kwargs):
        super(News, self).__init__(*args, **kwargs)
        if 'UpdatedAt' in self:
            dt = datetime.strptime(self['UpdatedAt'], '%a %b %d %H:%M:%S %Y')
            dt = pytz.UTC.localize(dt)
            self['UpdatedAt'] = dt
        else:
            self['UpdatedAt'] = None
