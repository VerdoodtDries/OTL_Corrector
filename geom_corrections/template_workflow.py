from geom_corrections.utils import AWV_Token
from geom_corrections.utils import EMInfraCoreAPI as API
import pandas as pd
import sqlite3
import os
import time

# Set the environment variables
environment_name = 't&i'
#environment_name = 'prd'

sqlite_token = os.path.join(r'C:\Users\DriesVerdoodtNordend\OneDrive - '
                            r'Nordend\projects\AWV\python_repositories\OTL_Corrector\token.sqlite')
# Connect to the SQLite database
conn = sqlite3.connect(sqlite_token)
cursor = conn.cursor()

# Create a table if not exists
cursor.execute('''CREATE TABLE IF NOT EXISTS token (environment TEXT, environment_url TEXT, iat INTEGER, exp INTEGER, 
access_token TEXT)''')
# Select the expiry date (exp) of the token of a certain environment
cursor.execute(f'''SELECT exp, access_token, environment_url from token where environment = "{environment_name}"''')
row = cursor.fetchone()

if row is None or (round(time.time()) > row[0]-60):
    # The token is missing or is about to expire.
    # Generate a new token
    myAWV_Token = AWV_Token.AWV_Token(environment_name)
    access_token = myAWV_Token.access_token
    iat = myAWV_Token.iat
    exp = myAWV_Token.exp
    environment_url = myAWV_Token.environment_url
    base_url = myAWV_Token.environment_url

    print(f'My access token is: {access_token}')
    print(f'Base URL: {base_url}')

    # Remove the old token from the SQLite database table
    cursor.execute(f'''DELETE FROM token where environment = "{environment_name}"''')
    # Insert a token-record into the SQLite database table
    cursor.execute(f'''INSERT INTO token (environment, environment_url, iat, exp, access_token) VALUES ("{environment_name}","{environment_url}", {iat}, {exp}, "{access_token}")''')
else:
    exp_actual, access_token, environment_url = row[0], row[1], row[2]

# Commit and close the SQLite connection
conn.commit()
conn.close()

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
size = 100
filters = '"uuid" : ["702519c0-142d-43d6-8e2a-218693fd6f86", "9eca6525-ca46-43d9-b579-49038525361c"]' # 2 random assets

response = API.otlassetssearch(access_token, environment_url, filters, size)
print(response)


# Bewaar dit asset in het OTLMOW-model

# Verbeter de fout in de data

# Converteer het asset naar het JSON-bestandsformaat voor DAVIE aanlevering