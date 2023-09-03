from rsa import newkeys, PublicKey, PrivateKey

def generateKeyPair():
    (pubKey, secKey) = newkeys(2048)

    with open("keys/public.pem", "wb")as file:
        file.write(pubKey.save_pkcs1("PEM"))
    with open("keys/private.pem", "wb")as file:
        file.write(secKey.save_pkcs1("PEM"))

def loadKeyPair():
    with open("keys/public.pem", "rb") as file:
        pubKey = PublicKey.load_pkcs1(file.read())
    with open("keys/private.pem", "rb") as file:
        secKey = PrivateKey.load_pkcs1(file.read())

    return (pubKey, secKey)