import json
import requests

def get_token(client_assertion: str, client_id: str):
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

