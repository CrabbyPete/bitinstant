#-------------------------------------------------------------------------------
# Name:        mail.py
# Purpose:     Support Amazon SES and STMP mail interfaces
#
# Author:      Douma
#
# Created:     14/08/2011
# Copyright:   (c) Douma 2011
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

# Standard smpt interfaces such as gmai
import smtplib
from email.mime.text    import MIMEText


class Mailer(object):

    def __init__( self, user, password, server, port ):
        self.user     = user
        self.password = password
        self.server   = server
        self.port     = port

    def email_connect( self ):

        em = smtplib.SMTP(self.server, self.port)

        em.set_debuglevel(False)
        em.ehlo()
        em.starttls()
        em.ehlo()
        em.login(self.user, self.password)
        return em

    # Mail the message.
    def email_to( self, text, to_addresses, from_address, subject ):

        msg = MIMEText( text )
        msg['Subject'] = subject
        msg['From']    = from_address

        # To is a list of To addresses
        COMMASPACE = ', '
        msg['To'] = COMMASPACE.join(to_addresses)

        self.mail = self.email_connect()
        result = self.mail.sendmail(from_address, to_addresses, msg.as_string())
        self.mail.quit()


