import time
import pyotp
import qrcode
import util

from models.user import USER


class UserTwoFactorMixin(object):

    otp_provider_map = {'googleAuthenticator': 'ga'}

    def validate_otp(self, otp):
        p = self.otp_provider_map.get(self.OTPProvider, None)
        if p is None:
            return False
        func = getattr(self, '%s_validate_otp' % p)
        return func(otp)

    def enable_otp(self, provider):
        if self.otp_enabled:
            return False
        p = self.otp_provider_map.get(provider, None)
        if p is None:
            raise ValueError('Unknown OTP provider: %s' % provider)
        func = getattr(self, '%s_enable_otp' % p)
        if func():
            self.OTPProvider = provider
            self.save()
            return True
        return False

    def disable_otp(self):
        if not self.otp_enabled:
            return False
        p = self.otp_provider_map.get(self.OTPProvider, None)
        if p is None:
            raise ValueError('Unable to dispable OTP, registered provider is unknown: %s' % self.OTPProvider)
        func = getattr(self, '%s_disable_otp' % p)
        return func()

    def provisioning_qrcode_otp(self):
        p = self.otp_provider_map.get(self.OTPProvider, None)
        if p is None:
            raise ValueError('Unable to generate OTP QR code, registered provider is unknown: %s' % self.OTPProvider)
        func = getattr(self, '%s_provisioning_qrcode_otp' % p)
        return func()

    @property
    def otp_enabled(self):
        return self.get('OTPProvider', None) is not None

    @property
    def otp_provider(self):
        return self.get('OTPProvider', None)


class UserGoogleAuthenticatorMixin(object):

    def ga_validate_otp(self, otp_val):
        otp = pyotp.TOTP(self.OTPSecret)
        # Give the user a little breathing room on the totp.
        # Clocks may be out of sync, etc
        try:
            otp_val = int(otp_val)
        except:
            return False
        for dt in (-30, 0, 30):
            if otp.verify(otp_val, for_time=time.time() + dt):
                return True
        return False

    def ga_provisioning_qrcode_otp(self, outfile=None):
        """Return a PIL.Image with the user's TOTP secret encoded in it.
        The QR code returned is suitable for Google Authenticator. Returns None
        if the user hasn't enabled TOPT.
        """
        img = None
        if self.OTPSecret is not None:
            otp = pyotp.TOTP(self.OTPSecret)
            uri = otp.provisioning_uri('%s@bitinstant.com' % self.UserName)
            qr = qrcode.QRCode()
            qr.add_data(uri)
            img = qr.make_image()
        return img

    def ga_enable_otp(self):
        if self.OTPSecret is None:
            self.OTPSecret = pyotp.random_base32()
            self.OTPPassPhrase = util.generate_random_passphrase(length=8)
            return True
        return False

    def ga_disable_otp(self):
        if self.OTPSecret is not None:
            USER.delete_attributes(self.pk, ['OTPSecret', 'OTPPassPhrase', 'OTPProvider'])
            self.OTPSecret = None
            self.OTPPassPhrase = None
            return True
        return False
