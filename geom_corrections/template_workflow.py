import otlmow_model.OtlmowModel
import requests

# Get the token


# Haal een asset op m.b.v. de API
# Kopieer dezelfde methode (API Call) als in FME, maar dan in Python.


# base_url = 'services.apps.mow.vlaanderen.be/eminfra/core/api'
base_url = 'services.apps-tei.mow.vlaanderen.be/eminfra/core/api'
size = 100
filters = {"uuid" : ["702519c0-142d-43d6-8e2a-218693fd6f86", "9eca6525-ca46-43d9-b579-49038525361c"]}  # 2 random assets

def otlassetssearch(token: str, base_url: str, size: int, filters: str):
    response = requests.post(
        f"https://{base_url}/otl/assets/search",
        params={
            "size": size,
            "filters": str(filters)
        },
        headers={"Authorization": f"Bearer {token}"},
        data=bytes,
        timeout=15
    )
    print(f"resultaat van het opvragen van assets : {response.status_code}, {response.text}")

    print("Ophalen assets ")
    print(response)
    return str(response.json())

# Function call
otlassetssearch(token=K_fOOntM61KUd7X8GVGqqvZ8GVuXcTKLZ8LTiGBnDQ4, base_url, size, filters)

# Bewaar dit asset in het OTLMOW-model
# Converteer het asset naar het JSON-bestandsformaat voor DAVIE aanlevering