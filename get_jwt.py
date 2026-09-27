# Protective Source License v1.0 (PSL-1.0)
# Copyright (c) 2025 Kaif
# Unauthorized removal of credits or use for abusive/illegal purposes
# will terminate all rights granted under this license.



import httpx
import asyncio
import json
import base64
import sys
from typing import Tuple
from google.protobuf import json_format, message
from Crypto.Cipher import AES

# IMPORTANT: This script requires 'freefire_pb2.py' to be in the same directory.
from ff_proto import freefire_pb2

# --- Global Constant
MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
RELEASEVERSION = "OB50"
USERAGENT = "Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)"
SUPPORTED_REGIONS = ["IND", "BR", "SG", "RU", "ID", "TW", "US", "VN", "TH", "ME", "PK", "CIS"]

# --- Helper Functions
async def json_to_proto(json_data: str, proto_message: message.Message) -> bytes:
    json_format.ParseDict(json.loads(json_data), proto_message)
    serialized_data = proto_message.SerializeToString()
    return serialized_data

def pad(text: bytes) -> bytes:
    padding_length = AES.block_size - (len(text) % AES.block_size)
    padding = bytes([padding_length] * padding_length)
    return text + padding

def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    aes = AES.new(key, AES.MODE_CBC, iv)
    padded_plaintext = pad(plaintext)
    ciphertext = aes.encrypt(padded_plaintext)
    return ciphertext

def decode_protobuf(encoded_data: bytes, message_type: message.Message) -> message.Message:
    message_instance = message_type()
    message_instance.ParseFromString(encoded_data)
    return message_instance

# --- Core Authentication
async def getAccess_Token(uid: str, password: str):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = f"uid={uid}&password={password}&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=payload, headers=headers)
        data = response.json()
        return data.get("access_token", "0"), data.get("open_id", "0")
        

async def create_jwt(uid: int, password: str) -> Tuple[str, str, str]:
    access_token, open_id = await getAccess_Token(uid, password)
    
    if access_token == "0":
        raise ValueError("Failed to obtain access token.")
    
    json_data = json.dumps({
      "open_id": open_id,
      "open_id_type": "4",
      "login_token": access_token,
      "orign_platform_type": "4"
    })
    
    encoded_result = await json_to_proto(json_data, freefire_pb2.LoginReq())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, encoded_result)
    
    url = "https://loginbp.ggblueshark.com/MajorLogin"
    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Expect': "100-continue",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASEVERSION
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=payload, headers=headers)
        response_content = response.content
        message = json.loads(json_format.MessageToJson(decode_protobuf(response_content, freefire_pb2.LoginRes)))
        
        token = message.get("token", "0")
        region = message.get("lockRegion", "0")
        serverUrl = message.get("serverUrl", "0")
        
        if token == "0":
            raise ValueError("Failed to obtain JWT.")
            
        return token, region, serverUrl

# --- Main Program to Run
async def main():
    print("\n--- Free Fire JWT Generator ---")
    
    uid = input("Enter your UID: ")
    password = input("Enter your password: ")
    
    if not uid or not password:
        print("UID and password cannot be empty.")
        sys.exit(1)
        
    try:
        print("\nGenerating JWT...")
        token, lock_region, server_url = await create_jwt(uid, password)
        # return token
        print("\n--- JWT Created Successfully ---")
        print(f"Token: {token}")
        print(f"Locked Region: {lock_region}")
        print(f"Server URL: {server_url}")
        
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
