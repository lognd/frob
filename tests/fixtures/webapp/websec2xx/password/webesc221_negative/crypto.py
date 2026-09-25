from Crypto.Cipher import AES

cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
