import json
import os
import requests
from generate_jwt import generate_jwt  # Roep deze functie aan!


# Define functions

# Roep een functie aan om de Token op te halen
# input: client_id, environment,
# output: token
environment_name = 't&i'

settings_file = os.path.join(r'C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\settings.json')

# Read settings file and obtain the client_id
with open(settings_file) as f:
    json_data = json.load(f)
#print('Settings file content: {0}'.format(json_data))

# Retrieve the client_id from the specified environment
client_id = next((auth_option['client_id'] for auth_option in json_data['auth_options'] if
                  auth_option['environment'] == environment_name), None)
jwk_private_key_file = next((auth_option['key_path'] for auth_option in json_data['auth_options'] if
                 auth_option['environment'] == environment_name), None)
environment_url = next((auth_option['environment_url'] for auth_option in json_data['auth_options'] if
                        auth_option['environment'] == environment_name), None)


client_assertion = generate_jwt(client_id, jwk_private_key_file)
print(f"The signed JSON Web Token (JWT), also named client_assertion is: {client_assertion}")

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

print(f"resultaat van het opvragen van assets : {response.status_code}, {response.text}")
print("Ophalen token ")
print(response)



def getToken(settings_file, environment, private_key):
    """

    :return: token
    """
    # Read settings file

    # Get the client_id based on the environment

    # Get the private keys
    return token
