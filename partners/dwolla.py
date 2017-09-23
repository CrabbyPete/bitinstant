#-------------------------------------------------------------------------------
# Name:        dwolla.py
# Purpose:     Process bitstamp actions
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

class dwolla( PartnerProcess ):
    payment_name  = ['dwollacoupon']
    exchange_name = ['dwolla']
    process_name  = 'dwolla'

