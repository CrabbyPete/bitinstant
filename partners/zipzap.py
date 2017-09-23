#-------------------------------------------------------------------------------
# Name:        zipzap.py
# Purpose:     Process zipzap payments
#
# Author:      Douma
#
# Created:     11/03/2013
# Copyright:   (c) Douma 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

# Local imports
from base import PartnerProcess

class zipzap( PartnerProcess ):
    payment_name  = ['zipzap']
    exchange_name = ['zipzap']
    process_name  = 'zipzap'