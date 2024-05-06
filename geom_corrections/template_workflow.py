from geom_corrections.utils import AWV_Token
from geom_corrections.utils import EMInfraCoreAPI as API
import pandas as pd

# Set the environment variables
environment_name = 't&i'
environment_name = 'prd'

## To do: store the token, the expiration date in an SQLite DB.
## Refresh the token, only if the expiration is about to expire. Otherwise recover the generated token.
## Append the timestamps iat and exp to the Class properties.

AWV_Token = AWV_Token.AWV_Token(environment_name)
access_token = AWV_Token.access_token
print(f'My access token is: {access_token}')

# Lees een Excel
# Vertaal de eerste kolom met uuids naar een lijst
# Read the Excel file
df = pd.read_excel(r'C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\OTL\Report0109\[RSA] Geometrie is '
                   r'geldig_ geen opeenvolgende punten.xlsx'
                   , sheet_name='Resultaat'
                   , skiprows=3)

# Transform the first column into a list
first_column_list = df.iloc[:, 0].tolist()
print(first_column_list)
print(f'The number of assets is: {len(first_column_list)}')

# Haal een asset op m.b.v. de API
base_url = AWV_Token.environment_url
print(f'Base URL: {base_url}')


size = 100
filters = '{"uuid" : ["702519c0-142d-43d6-8e2a-218693fd6f86", "9eca6525-ca46-43d9-b579-49038525361c"]}' # 2 random assets

response = API.otlassetssearch(access_token, base_url, filters, size)
print(response)
print(response)



# Bewaar dit asset in het OTLMOW-model

# Verbeter de fout in de data

# Converteer het asset naar het JSON-bestandsformaat voor DAVIE aanlevering