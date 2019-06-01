#
#
#
import os
from hashlib import md5

from Crypto import Random
from Crypto.Cipher import ARC4
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA

#*******************************
# php openssl_(seal|open)
# http://php.net/manual/en/function.openssl-seal.php (User notes)
#
def openssl_seal(plain_data, pub_key):
    nonce = Random.new().read(16)
    rnd_key = SHA.new(nonce).digest()
    rc4 = ARC4.new(rnd_key)
    sealed_data = rc4.encrypt(plain_data)
    rsa = RSA.importKey(pub_key, None)
    pkcs = PKCS1_v1_5.new(rsa)
    env_key = pkcs.encrypt(rnd_key)
    return sealed_data, env_key

def openssl_open(sealed_data, env_key, priv_key):
    rsa = RSA.importKey(priv_key, None)
    size = SHA.digest_size
    sentinel = Random.new().read(15 + size)
    pkcs = PKCS1_v1_5.new(rsa)
    d_env_key = pkcs.decrypt(env_key, sentinel)
    rc4 = ARC4.new(d_env_key)
    return rc4.decrypt(sealed_data)

#*******************************
#
#
def md5sum_match(file_path, md5sum):
    if  not os.path.isfile(file_path):
        return False
    f = None
    content = None
    try:
        f = open(file_path, 'rb')
    finally:
        if  f:
            content = f.read()
        f.close()
    if  not content:
        return False
    return md5(content).hexdigest() == md5sum

#
#
#
