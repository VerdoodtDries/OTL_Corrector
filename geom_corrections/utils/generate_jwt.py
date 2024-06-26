from jwt import JWT, jwk_from_dict
import time
import uuid
import json


def generate_jwt(client_id: str, jwk_private_key_file: str):
    """
    Generate a JWT token using the provided client ID and JWK private key file.

    Args:
        client_id (str): The client ID used for token generation.
        jwk_private_key_file (str): The file path to the JWK private key.

    Returns:
        str: The signed JWT token generated using the client ID and private key.
    """
    # print(f"gebruiken van JWK private key in bestand {jwk_private_key_file}")
    with open(jwk_private_key_file) as key_file:
        json_data = json.load(key_file)
        private_key = jwk_from_dict(json_data)
        # print(f"private key is aangemaakt: {private_key}")
    # print("Aanmaken van een jwt token")
    current_time_in_seconds = round(time.time())
    expiry_time_in_seconds = current_time_in_seconds + 599
    claims = {
        "exp": expiry_time_in_seconds,
        "iat": current_time_in_seconds,
        # dit is een random token om replay attacks te vermijden
        "jti": str(uuid.uuid4()),
        "iss": client_id,
        "sub": client_id,
        "aud": "https://authenticatie.vlaanderen.be/op"
    }
    # print(f"de claims zijn {claims}")
    header = {
        "alg": "RS256",
        "typ": "JWT"
    }
    signed_jwt = JWT().encode(claims, private_key, alg="RS256", optional_headers=header)
    print(f"signed JWT token : {signed_jwt}")
    return signed_jwt
