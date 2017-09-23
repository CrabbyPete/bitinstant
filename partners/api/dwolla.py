import os
import getpass
import config
import time
import pexpect
email    = config.dwolla_email
password = config.dwolla_password

os.system('curl -c cookies.txt -d "EmailAddress=%s&Password=%s" https://www.dwolla.com/login.aspx' % (email,password))
os.system('curl -O -J -b cookies.txt "https://www.dwolla.com/statements?year=2013&month=`date +%m`&format=csv"')
print 'Updating current Dwolla SVN...'
os.system('svn update %s' % (config.dwolla_csv_svn_co))
print 'Importing new statement...'
os.system('mv DwollaStatement*.csv %s' % config.dwolla_csv_svn_co)
os.system('svn add %s/*.csv' % config.dwolla_csv_svn_co)
os.system('svn commit %s -m \'Dwolla import ran on %s\'' % (config.dwolla_csv_svn_co,time.ctime()))
os.system('svn update %s' % (config.dwolla_csv_svn_co))

