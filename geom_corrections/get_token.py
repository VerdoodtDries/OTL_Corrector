import json
import os
import requests
#from generate_jwt import generate_jwt  # Roep deze functie aan!
from jwt import JWT, jwk_from_dict
import time
import uuid
from get_iat import get_iat

environment_name = 't&i'
settings_file = os.path.join('../settings.json')

# Read settings file and obtain the client_id
with open(settings_file) as f:
    json_data = json.load(f)

# Given a specific environment, retrieve the client_id, jwk_private_key_file, environment_url
client_id = next((auth_option['client_id'] for auth_option in json_data['auth_options'] if
                  auth_option['environment'] == environment_name), None)
jwk_private_key_file = next((auth_option['key_path'] for auth_option in json_data['auth_options'] if
                 auth_option['environment'] == environment_name), None)
#environment_url = next((auth_option['environment_url'] for auth_option in json_data['auth_options'] if auth_option['environment'] == environment_name), None)

##
##client_assertion = generate_jwt(client_id, jwk_private_key_file)
##print(f"The signed JSON Web Token (JWT), also named client_assertion is: {client_assertion}")

sub = client_id
iat = get_iat()
exp = iat + 599
jti = str(uuid.uuid4())
# environment_url = feature.getAttribute('environment_url')
instance = JWT()
aud = "https://authenticatie.vlaanderen.be/op"

with open(jwk_private_key_file) as pk:
    json_data = json.load(pk)

private_key = jwk_from_dict(json_data)

payload = {
    "exp": 1714748919,
    "iat": 1714748321,
    "jti": jti,
    "iss": sub,
    "sub": sub,
    "aud": aud,
}

header = {
    "alg": "RS256",
    "typ": "JWT"
}

client_assertion = instance.encode(payload, private_key, alg='RS256', optional_headers=header)

# Launch API Call POST
response = requests.post(
    "https://authenticatie.vlaanderen.be/op/v1/token",
    json={
        'grant_type': "client_credentials",
        'client_assertion': client_assertion,
        'client_assertion_type': "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        'scope': "awv_toep_services",
        'client_id': client_id},
    headers={
        "Content-Type": "application/x-www-form-urlencoded"
    }
)

# Compare FME and Python Post requests with a tool like Fiddler

print(f"resultaat van het opvragen van assets : {response.status_code}, {response.text}")
print("Ophalen token ")
print(response)