# Protective Source License v1.0 (PSL-1.0)
# Copyright (c) 2025 Kaif
# Unauthorized removal of credits or use for abusive/illegal purposes
# will terminate all rights granted under this license.

import binascii
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from ff_proto.send_like_pb2 import like as LikeProfileReq

# --- Garena API Encryption Constants ---
MAIN_KEY = b'Yg&tc%DEuh6%Zc^8'
MAIN_IV = b'6oyZDr22E3ychjM%'


def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    """
    Encrypt data using AES-CBC.
    """
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plaintext, AES.block_size)
    return cipher.encrypt(padded)

def create_like_payload(uid: int, region: str) -> bytes:
    """
    Build and encrypt the protobuf payload for /LikeProfile request.
    Returns raw bytes ready to send.
    """
    # --- Step 1: Create protobuf message ---
    message = LikeProfileReq()
    message.uid = int(uid)
    message.region = region
    protobuf_bytes = message.SerializeToString()

    # --- Step 2: Encrypt using AES-CBC ---
    encrypted_bytes = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, protobuf_bytes)

    # --- Return raw bytes (ready for requests.post(data=...)) ---
    return encrypted_bytes

# --- Example usage / hardcoded test ---
if __name__ == "__main__":
    uid_to_like = 111119900  # Hardcoded UID as a Placeholder
    region = "IND"             # Hardcoded region

    payload = create_like_payload(uid_to_like, region)
    print("--- /LikeProfile Payload ---")
    print("Raw bytes:", payload)
    print("Hex string:", binascii.hexlify(payload).upper().decode())
