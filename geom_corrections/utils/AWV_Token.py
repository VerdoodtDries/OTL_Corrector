import os
from jwt import JWT, jwk_from_dict
import time
import uuid
import json
import requests

class AWV_Token:
    def __init__(self, environment: str):
        self.settings = os.path.join(r'C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\settings.json')
        self.environment = environment
        self.jwk_private_key_file = self.readfromsettings('key_path')
        self.client_id = self.readfromsettings('client_id')
        self.environment_url = self.readfromsettings('environment_url')
        self.iat = round(time.time())
        self.exp = self.iat + 600
        self.signed_jwt = self.generate_jwt(self.client_id, self.jwk_private_key_file)
        self.access_token = self.get_token(self.signed_jwt, self.client_id)


    def readfromsettings(self, json_key):
        # Read settings file
        with open(self.settings) as f:
            json_data = json.load(f)

        json_value = next((auth_option[json_key] for auth_option in json_data['auth_options'] if
                 auth_option['environment'] == self.environment), None)

        return json_value
    def generate_jwt(self, client_id: str, jwk_private_key_file: str):
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
        claims = {
            "exp": self.exp,
            "iat": self.iat,
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

    def get_token(self, client_assertion: str, client_id: str):
        """
        Retrieve an access token by sending a POST request to the authentication server using the provided client assertion and client ID.

        Args:
            ("valid_assertion_1", client_assertion (str): The client assertion "valid_client_1", for authentication.
            client_id (str): The client ID for authentication.

        Returns:
            str: The access token obtained from the authentication server.
        """
        response = requests.post(
            "https://authenticatie.vlaanderen.be/op/v1/token",
            data={
                'grant_type': "client_credentials",
                'client_assertion': client_assertion,
                'client_assertion_type': "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                'scope': "awv_toep_services",
                'client_id': client_id}
        )
        # print(f"resultaat van het opvragen van assets : {response.status_code}, {response.text}")
        access_token = json.loads(response.text).get('access_token')
        print(f"access_token: {access_token}")
        return access_token


#
# # Example usage
# my_awv_token = AWV_Token("t&i")
# print(f'My access token is: {my_awv_token.access_token}')