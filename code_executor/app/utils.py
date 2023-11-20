import boto3
import base64

class EncryptorClass:
    def __init__(self, key_id):
        self.kms_client = boto3.client("kms")
        self.key_id = key_id
    def encrypt(self, text):
        ret = self.kms_client.encrypt(
            KeyId=self.key_id,
            Plaintext=text
        )
        return base64.b64encode(ret["CiphertextBlob"]).decode()
    def decrypt(self, cipher_text_blob):
        ret = self.kms_client.decrypt(
            KeyId=self.key_id,
            CiphertextBlob=base64.b64decode(cipher_text_blob)
        )
        return ret["Plaintext"].decode()