# Protective Source License v1.0 (PSL-1.0)
# Copyright (c) 2025 Kaif
# Unauthorized removal of credits or use for abusive/illegal purposes
# will terminate all rights granted under this license.

# Original author: 0xMe
# GitHub: https://github.com/0xMe/FreeFire-Api
# Modifications by kaifcodec (c) 2025


from ff_proto import freefire_pb2, core_pb2, account_show_pb2
import httpx
import asyncio
import json
from google.protobuf import json_format, message
from google.protobuf.message import Message
from Crypto.Cipher import AES
import base64
from typing import Tuple
import sys

MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
RELEASEVERSION = "OB48"
USERAGENT = "Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)"
SUPPORTED_REGIONS = ["IND", "BR", "SG", "RU", "ID", "TW", "US", "VN", "TH", "ME", "PK", "CIS"]
ACCOUNTS = {
    'IND': "uid=4104125669&password=E5655A0D14EF812A908726152BDD38021BEF528801AA42B16CFA4ED67141C4CA",
    'SG': "uid=3158350464&password=70EA041FCF79190E3D0A8F3CA95CAAE1F39782696CE9D85C2CCD525E28D223FC",
    'RU': "uid=3301239795&password=DD40EE772FCBD61409BB15033E3DE1B1C54EDA83B75DF0CDD24C34C7C8798475",
    'ID': "uid=3301269321&password=D11732AC9BBED0DED65D0FED7728CA8DFF408E174202ECF1939E328EA3E94356",
    'TW': "uid=3301329477&password=359FB179CD92C9C1A2A917293666B96972EF8A5FC43B5D9D61A2434DD3D7D0BC",
    'US': "uid=3301387397&password=BAC03CCF677F8772473A09870B6228ADFBC1F503BF59C8D05746DE451AD67128",
    'VN': "uid=3301447047&password=044714F5B9284F3661FB09E4E9833327488B45255EC9E0CCD953050E3DEF1F54",
    'TH': "uid=3301470613&password=39EFD9979BD6E9CCF6CBFF09F224C4B663E88B7093657CB3D4A6F3615DDE057A",
    'ME': "uid=3301535568&password=BEC9F99733AC7B1FB139DB3803F90A7E78757B0BE395E0A6FE3A520AF77E0517",
    'PK': "uid=3301828218&password=3A0E972E57E9EDC39DC4830E3D486DBFB5DA7C52A4E8B0B8F3F9DC4450899571",
    'CIS': "uid=3309128798&password=412F68B618A8FAEDCCE289121AC4695C0046D2E45DB07EE512B4B3516DDA8B0F",
    'BR': "uid=3158668455&password=44296D19343151B25DE68286BDC565904A0DA5A5CC5E96B7A7ADBE7C11E07933"
}


async def json_to_proto(json_data: str, proto_message: Message) -> bytes:
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


async def getAccess_Token(account):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = account + "&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
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


async def create_jwt(region: str) -> Tuple[str, str, str]:
    account = ACCOUNTS.get(region)
    access_token, open_id = await getAccess_Token(account)
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
        return f"Bearer {token}", region, serverUrl


async def GetAccountInformation(ID, UNKNOWN_ID, regionMain, endpoint):
    json_data = json.dumps({
        "a": ID,
        "b": UNKNOWN_ID
    })
    encoded_result = await json_to_proto(json_data, core_pb2.GetPlayerPersonalShow())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, encoded_result)
    regionMain = regionMain.upper()
    if regionMain not in SUPPORTED_REGIONS:
        return {
            "error": "Invalid request",
            "message": f"Unsupported 'region' parameter. Supported regions are: {', '.join(SUPPORTED_REGIONS)}."
        }
    token, region, serverUrl = await create_jwt(regionMain)
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 13; A063 Build/TKQ1.221220.001)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Expect': "100-continue",
        'Authorization': token,
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASEVERSION
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(serverUrl + endpoint, data=payload, headers=headers)
        response_content = response.content
        message = json.loads(json_format.MessageToJson(decode_protobuf(response_content, account_show_pb2.AccountPersonalShowInfo)))
        return message

# --- Interactive Main Program ---
async def main():
    while True:
        print("\n--- Free Fire API Tool ---")
        print("1. Create JWT")
        print("2. Get Account Information")
        print("3. Exit")

        choice = input("Enter your choice (1-3): ")

        if choice == '1':
            print(f"\nSupported regions: {', '.join(SUPPORTED_REGIONS)}")
            region = input("Enter the region (e.g., IND, SG): ").upper()
            if region not in SUPPORTED_REGIONS:
                print("Error: Invalid region provided.")
                continue

            try:
                print(f"Creating JWT for region: {region}...")
                token, lock_region, server_url = await create_jwt(region)
                print("\n--- JWT Created Successfully ---")
                print(f"Token: {token}")
                print(f"Locked Region: {lock_region}")
                print(f"Server URL: {server_url}")
            except Exception as e:
                print(f"An error occurred while creating JWT: {e}")

        elif choice == '2':
            print(f"\nSupported regions: {', '.join(SUPPORTED_REGIONS)}")
            region = input("Enter the region (e.g., IND, SG): ").upper()
            if region not in SUPPORTED_REGIONS:
                print("Error: Invalid region provided.")
                continue

            try:
                player_id = input("Enter the player ID: ")
                unknown_id = input("Enter the UNKNOWN_ID (placeholder, usually 0): ")
                endpoint = "/GetPlayerPersonalShow"
                print(f"Fetching account information for ID {player_id}...")
                info = await GetAccountInformation(player_id, unknown_id, region, endpoint)
                if info.get("error"):
                    print(f"Error: {info['message']}")
                else:
                    print("\n--- Account Information ---")
                    print(json.dumps(info, indent=4))
            except Exception as e:
                print(f"An error occurred while getting account information: {e}")

        elif choice == '3':
            print("Exiting...")
            sys.exit(0)

        else:
            print("Invalid choice. Please enter a number between 1 and 3.")

if __name__ == "__main__":
    asyncio.run(main())
