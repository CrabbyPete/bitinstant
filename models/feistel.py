#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Douma
#
# Created:     12/02/2013
# Copyright:   (c) Douma 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python
""" ``feistel`` module.
"""


def make_feistel_number(f):
    """ Generate pseudo random consistent reversal number
        per Feistel cypher algorithm.

        see http://en.wikipedia.org/wiki/Feistel_cipher

        >>> feistel_number = make_feistel_number(sample_f)
        >>> feistel_number(1)
        573852158
        >>> feistel_number(2)
        1788827948
        >>> feistel_number(123456789)
        1466105040

        Reversable

        >>> feistel_number(1466105040)
        123456789
        >>> feistel_number(1788827948)
        2
        >>> feistel_number(573852158)
        1
    """
    def feistel_number(n):
        l = (n >> 16) & 65535
        r = n & 65535
        for i in (1, 2, 3):
            l, r = r, l ^ f(r)
        return ((r & 65535) << 16) + l
    return feistel_number


def sample_f(x):
    return int((((1366 * x + 150889) % 714025) * 32767) // 714025)



def luhn_checksum(n):
    """ Calculates checksum based on Luhn algorithm, also known as
        the "modulus 10" algorithm.

        see http://en.wikipedia.org/wiki/Luhn_algorithm

        >>> luhn_checksum(1788827948)
        0
        >>> luhn_checksum(573852158)
        1
        >>> luhn_checksum(123456789)
        7
    """
    digits = digits_of(n)
    checksum = (sum(digits[-2::-2]) +
                sum(sum2digits(d << 1) for d in digits[-1::-2])) % 10
    return checksum and 10 - checksum or 0


def luhn_sign(n):
    """ Signs given number by Luhn checksum.

        >>> luhn_sign(78482748)
        784827487
        >>> luhn_sign(47380210)
        473802106
        >>> luhn_sign(123456789)
        1234567897
    """
    return luhn_checksum(n) + (n << 3) + (n << 1)


def is_luhn_valid(n):
    """
        >>> is_luhn_valid(1234567897)
        True
        >>> is_luhn_valid(473802106)
        True
        >>> is_luhn_valid(34518893)
        False
    """
    digits = digits_of(n)
    checksum = sum(digits[-1::-2]) + sum(sum2digits(d << 1)
                                         for d in digits[-2::-2])
    return checksum % 10 == 0


def digits_of(n):
    """ Returns a list of all digits from given number.

        >>> digits_of(123456789)
        [1, 2, 3, 4, 5, 6, 7, 8, 9]
    """
    return [int(d) for d in str(n)]


def sum2digits(d):
    """ Sum digits of a number that is less or equal 18.

        >>> sum2digits(2)
        2
        >>> sum2digits(17)
        8
    """
    return (d // 10) + (d % 10)

def new_account_number( index ):
    feistel_number = make_feistel_number(sample_f)
    number = feistel_number(index)
    print number
    print feistel_number(number)
    sign = luhn_sign( number )
    print sign
    print is_luhn_valid(sign)
    number = sign/10
    print feistel_number(number)
    pass




def main():
    account = new_account_number(1)


if __name__ == '__main__':
    main()
