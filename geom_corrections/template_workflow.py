import otlmow_model.OtlmowModel
from shapely import LineString, Polygon
import geopandas as gpd
import requests

# Roep een functie aan om de Token op te halen
# input: client_id, environment,
# output: token

# Test Geopandas function remove_repeated_points()
s = gpd.GeoSeries([
       LineString([(0, 0), (0, 0), (1, 0)]),
       Polygon([(0, 0), (0, 0.5), (0, 1), (0.5, 1), (0,0)]),
    ],)
print(s)

s = s.remove_repeated_points(tolerance=0.0)
print(s)

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


# Verbeter het asset. Vb. Verwijder dubbele opeenvolgende punten
# https://geopandas.org/en/latest/docs/reference/api/geopandas.GeoSeries.remove_repeated_points.html



# Bewaar dit asset in het OTLMOW-model
# Converteer het asset naar het JSON-bestandsformaat voor DAVIE aanlevering