import requests

def otlassetssearch(token: str, base_url: str, filters: str, size: int = 1000):
    """
    https://apps.mow.vlaanderen.be/eminfra/core/swagger-ui/#/otl/otlAssetsSearch

    Args:
        token (str): The token used for authorization (Bearer).
        base_url (str): The base URL for the search request.
        size (int): The number of assets to retrieve. Integer value between 100 and 1000.
        filters (str): The filters to apply for the search.

    Returns:
        str: The JSON response containing the search results.
    """
    response = requests.post(
        f"https://{base_url}/eminfra/core/api/otl/assets/search",
        params={"size": size, "filters": filters},
        headers={"Authorization": f"Bearer {token}"},
#        data=bytes,
        timeout=15,
    )

    print(f'response url: {response.url}')
    print(f'response headers: {response.headers}')
    print(f'response request: {response.request}')
    print(f'response status_code: {response.status_code}')

    return str(response.json())

# On hold (work in progress)
# def lgcassetssearch(token: str, base_url: str, filters: str, size: int = 1000):
#     response = requests.post(
#         f"https://{base_url}/assets/search",
#         params={"size": size, "filters": filters},
#         headers={"Authorization": f"Bearer {token}"},
#         data=bytes,
#         timeout=15,
#     )
#     return str(response.json())
