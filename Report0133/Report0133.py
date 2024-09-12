######################################################################
### Import packages
######################################################################
from pathlib import Path
from otlmow_converter.OtlmowConverter import OtlmowConverter
from otlmow_model.OtlmowModel.BaseClasses.MetaInfo import meta_info
from otlmow_model.OtlmowModel.BaseClasses.OTLObject import dynamic_create_instance_from_uri
from otlmow_model.OtlmowModel.BaseClasses.OTLObject import OTLObject
from otlmow_model.OtlmowModel.Helpers.OTLObjectHelper import print_overview_assets
from otlmow_converter.FileFormats.PandasConverter import PandasConverter
from fuzzywuzzy import fuzz
from HelperFunctions.utils import split_list, plot_gdf, gdf_to_OTLAssets
import json
import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.geometry import Point, Polygon
from shapely import count_coordinates, remove_repeated_points
import logging
from EMInfraImporter import EMInfraImporter
from RequestHandler import RequestHandler
from RequesterFactory import RequesterFactory
from SettingsManager import SettingsManager
from AssetUpdater import AssetUpdater
import geopandas as gpd
import matplotlib
from openpyxl import load_workbook
import matplotlib.pyplot as plt
matplotlib.use('TkAgg')
import contextily as ctx
from matplotlib.ticker import ScalarFormatter
import os

boom_type_uri = 'https://wegenenverkeer.data.vlaanderen.be/ns/onderdeel#Boom'
boom = dynamic_create_instance_from_uri(boom_type_uri)

######################################################################
### Define variables
######################################################################
provincie = 'Oost-Vlaanderen'

script_dir = os.path.dirname(os.path.abspath(__file__))
filename = f'[RSA] Dubbele bomen ({provincie}).xlsx'
filepath = os.path.join(script_dir, 'input', filename)
feature_type = 'Resultaat'  # This is the layer name or the Excel sheet name


######################################################################
### Connect to API
######################################################################
if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    settings_manager = SettingsManager(
        settings_path=r'C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\settings.json')

    requester = RequesterFactory.create_requester(settings=settings_manager.settings, auth_type='JWT', env='prd')

    request_handler = RequestHandler(requester)

    eminfra_importer = EMInfraImporter(request_handler)


######################################################################
### Read input data in a pandas dataframe
######################################################################
try:
    # Split the extension
    filename_abs, extension = os.path.splitext(filename)
    # Read the data from the SQLite database into a geopandas geodataframe
    if extension == '.sqlite':
        gdf_input = gpd.read_file(filepath, layer=feature_type)
    # Read the data from an Excel file into a pandas dataframe
    elif extension == '.xlsx':
        df_input = pd.read_excel(filepath, sheet_name=feature_type, skiprows=2)
    elif extension == '.csv':
        df_input = pd.read_csv(filepath_or_buffer=filepath, delimiter=';')
except FileNotFoundError as e:
    raise FileNotFoundError(f"The file {filepath} does not exist.") from e

# Launch the API request to obtain data
asset_uuids = df_input['boom1_uuid'].tolist()
asset_uuids = [i[:36] for i in
               asset_uuids]  # Behoud enkel de eerste 36 karakters, hetgeen overeenkomt met de uuid, en niet de volledige AIM-ID

# Verwijder de dubbels uit de lijst. Python trucje: converteer naar een set en meteen terug naar een lijst
# print(f'Lengte van de initiële lijst: {len(asset_uuids)}')
asset_uuids = list(set(asset_uuids))
# print(f'Lengte van de unieke lijst: {len(asset_uuids)}')


######################################################################
### Launch the API request to obtain data
######################################################################
asset_uuids_bin100 = split_list(asset_uuids)
asset_dicts_dict = {}  # Instantiate an empty dictionary to fill later on
for bin_asset_uuids in asset_uuids_bin100:
    # Bewaar de resultaten per match
    object_generator = eminfra_importer.import_assets_from_webservice_by_uuids(asset_uuids=bin_asset_uuids)
    ## print(f'Type: {type(object_generator)}\nResponse: {object_generator}')
    asset_dicts_dict |= AssetUpdater.get_dict_from_object_generator(
        object_generator)  ## |= is the update operator for dictionaries.

df = pd.DataFrame(data=asset_dicts_dict).transpose()  # Transpose rows and column

# Create a GeoSeries
gs_geometry = gpd.GeoSeries.from_wkt(df['loc:Locatie.geometrie'])

# Convert the DataFrame to a GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry=gs_geometry, crs="EPSG:31370")

######################################################################
### Process dataframe
######################################################################
# Voeg opnieuw de info toe uit het input dataframe (df_input): ident8, ident2(, gemeente, provincie). Merge o.b.v. uuid.
# Add a column "id_duplicate_asset". This is the column to detect the duplicate assets (identical trees).
# Step 1: Merge the input dataframe (df_input) and add the column "boom2_uuid".
# preprocess df_input: set index, keep attributes uuid, ident8(, gemeente, provincie)
# Keep a minimalistic version of df_input
df_input_minimal = df_input[["boom1_uuid", "boom2_uuid", "boom1_ident8", "boom2_ident8"]].copy()
df_input_minimal.set_index("boom1_uuid", drop=False, inplace=True)
df_input_minimal = df_input_minimal.drop_duplicates('boom1_uuid')
gdf = pd.merge(gdf, df_input_minimal, left_index=True, right_index=True, how='inner')
# Step 2: Create a sorted tuple for each combination of 'uuid1' and 'uuid2'
#         Add a column that indicates the match between two assets: id_duplicate_asset
gdf['id_duplicate_asset'] = gdf.apply(lambda row: tuple(sorted([row['boom1_uuid'], row['boom2_uuid']])), axis=1)
# Sort the dataframe for visual inspection
gdf.sort_values(by="id_duplicate_asset", inplace=True)

######################################################################
### Groepeer dataframe per weg (ident8)
### Plot een kaart met alle dubbele bomen
### Schrijf een samenvatting weg naar Excel
######################################################################
# Group by the 'ident8' column and perform operations on each group
grouped = gdf.groupby('boom1_ident8')

group_counts = gdf.groupby('boom1_ident8').size().reset_index(name='count')
group_counts = group_counts.rename(columns={'boom1_ident8': 'ident8'})

# Directories and file paths
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, 'output')
filename = 'Overzicht dubbele bomen.xlsx'
output_file = os.path.join(output_dir, filename)

# Write to Excel without overwriting the whole file
with pd.ExcelWriter(output_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    group_counts.to_excel(writer, sheet_name=provincie, index=False)
    print(f"Results written to {output_file}")

# Loop over each group
for group_name, group_data in grouped:
    print(f"Group: {group_name}")
    print(group_data)

    # Perform your custom operations here
    # For example, counting the records for each group
    count = group_data['boom1_uuid'].count()
    print(f"Count for {group_name}: {count}\n")


    # Plot the data
    # title = f'{group_name} - aantal bomen: {count}'
    # plot_gdf(group_data, output_dir, group_name, fanout=False, color='green', title=title, figsize=(10, 10), dpi=100)



######################################################################
### Bereken het aantal unieke waarden per groep. Anders gezegd: zijn alle attributes identiek?
### Tel het aantal niet-NULL waarden voor een gegeven lijst van attributen
######################################################################
# Convert VegetatieElement.soortnaam JSON-dictionary naar tekst (json.dumps())
gdf['VegetatieElement.soortnaam.json'] = gdf['VegetatieElement.soortnaam'].apply(json.dumps)
# Convert Boom.boomspiegel lijst naar tekst (concatenate lijst elementen)
gdf['Boom.boomspiegel.list'] = gdf['Boom.boomspiegel'].apply(lambda x: str(x))

# Lijst met attribuutnamen
attributes = [
      'AIMNaamObject.naam'
    , 'AIMToestand.toestand'
    , 'AIMObject.notitie'
    , 'AIMObject.datumOprichtingObject'
    , 'AIMDBStatus.isActief'
    , 'VegetatieElement.soortnaam.json'
    , 'VegetatieElement.hoogte'
    , 'Boom.boomspiegel.list'
    , 'Boom.eindbeeld'
    , 'Boom.geschatteKlassePlantjaar'
    , 'Boom.groeifase'
    , 'Boom.heeftLuchtleiding'
    , 'Boom.takvrijeStamlengte'
]



# outer loop in iedere groep van identieke bomen. Meestal zijn dit groepen van 2, maar dit kan ook 3 of meer dubbels zijn.
grouped = gdf.groupby('id_duplicate_asset')
grouped_counts = gdf.groupby('id_duplicate_asset').size().reset_index(name='count')
print(f'Aantal dubbele elementen: {grouped_counts}')

# Append 2 columns to main geodataframe
gdf['non_null_count'] = None
gdf['identical_values'] = None

for group_name, group_data in grouped:
    # Step 1: Check if all the elements in the selected attributes are identical
    identical_values = group_data.loc[:,attributes].nunique() == 1
    all_identical = identical_values.all()  # True if all attributes have identical values, False otherwise
    print(f"Are all values identical across attributes? {all_identical}")

    # Step 2: Count the number of non-null (non-NaN) values for each row in the selected attributes
    non_null_count = group_data[attributes].notna().sum(axis=1)
    group_data['non_null_count'] = non_null_count  # Add this as a new column
    print(group_data)

    # Step 3: Add a boolean column to indicate if all values in these attributes are identical
    group_data['identical_values'] = identical_values.all()

    # Step 4: Update main geodataframe before looping to the next group
    gdf.update(group_data)


# Controleer of er een volledig exacte kopie is. Dat betekent: alle attribuutwaarden hetzelfde (identical_values=True) en evenveel attributen ingevuld (non_null_count)
# Deze is overbodig. Als assets 100% identief zijn, dan maakt het niet uit welke geactiveerd of gedeactiveerd wordt.
# gdf_identiek = gdf[gdf['identical_values'] == True]

# Indien geen keuze kan gemaakt worden welke asset te deactiveren, sorteer volgens volgende criteria
print('Sorteer volgens volgende criteria:\n'
      'id_duplicate_asset:\n\t\t\tper groep van dubbele assets\n'
      'non_null_count:\n\t\t\taantal kolommen met een waarde\n'
      'AIMNaamObject.naam:\n\t\t\tnaam van de boom (niet te verwarren met soortnaam)\n'
      'AIMObject.datumOprichtingObject:\n\t\t\taflopende datum (meest recente eerst)\n'
      'notitie:\n\t\t\tnotitie. Waardes eerst')

gdf_output = gdf.sort_values(by=['id_duplicate_asset', 'non_null_count', 'AIMNaamObject.naam', 'AIMObject.datumOprichtingObject', 'AIMObject.notitie'], ascending=[True, False, False, False, False])

# Na het sorteren, activeer de eerste asset van de groep en deactiveer de overige assets van dezelfde groep.
# Create a boolean column that assigns True to the first element of each group
gdf_output['isActief'] = gdf_output.groupby('id_duplicate_asset').cumcount() == 0


# ######################################################################
# ### Preprocessing gdf alvorens wegschrijven
# ######################################################################
# Schrijf deze info opnieuw weg, meteen naar DAVIE-conforme Excel
# Behoud attributen om de situatie juist te kunnen evalueren
columns_to_keep = ['@id', '@type', 'isActief', 'geometry', 'AIMObject.notitie', 'AIMToestand.toestand', 'AIMNaamObject.naam'
    , 'Boom.boomspiegel', 'Boom.eindbeeld', 'Boom.geschatteKlassePlantjaar', 'Boom.groeifase', 'Boom.heeftLuchtleiding'
    , 'Boom.takvrijeStamlengte', 'VegetatieElement.hoogte', 'VegetatieElement.soortnaam']
gdf_output = gdf_output.filter(items=columns_to_keep)

# Rename columns
gdf_output = gdf_output.rename(
    columns=
    {
        '@id': 'assetId.identificator'
        , "@type": 'typeURI'
        , 'AIMNaamObject.naam': 'naam'
        , 'AIMObject.notitie': 'notitie'
        , 'AIMToestand.toestand': 'toestand'
        , 'Boom.boomspiegel': 'boomspiegel'
        , 'Boom.eindbeeld': 'eindbeeld'
        , 'Boom.geschatteKlassePlantjaar': 'geschatteKlassePlantjaar'
        , 'Boom.groeifase': 'groeifase'
        , 'Boom.heeftLuchtleiding': 'heeftLuchtleiding'
        , 'Boom.takvrijeStamlengte': 'takvrijeStamlengte'
        , 'VegetatieElement.hoogte': 'hoogte'
        , 'VegetatieElement.soortnaam': 'soortnaam'
    }
)

# Keeping only the part after the last forward slash and replacing the original column
gdf_output['assetId.identificator'] = gdf_output['assetId.identificator'].str.split('/').str[-1]
# Convert geometries to WKT. Na dit punt wordt de geodataframe een normaal dataframe.
gdf_output['geometry'] = gdf_output['geometry'].apply(lambda geom: geom.wkt)


######################################################################
### Converteer gdf naar dictionary
######################################################################
# Om alle attributen weg te schrijven naar een DAVIE-conform bestand, dient nog wat post-processing te gebeuren aan de attributen.
list_columns = ['boomspiegel']  # columns to replace NaN with an empty list
dict_key_mapping = \
    {
        'DtcVegetatieSoortnaam.soortnaamWetenschappelijk': 'soortnaamWetenschappelijk'
        , 'DtcVegetatieSoortnaam.soortnaamNederlands': 'soortnaamNederlands'
        , 'DtcVegetatieSoortnaam.wetenschappelijkeSoortnaam': 'wetenschappelijkeSoortnaam'
    }  # Mapping of old keys to new keys

# Vervang alle nan-waardes door None
gdf_output = gdf_output.where(pd.notna(gdf_output), None)
gdf_output[list_columns] = gdf_output[list_columns].map(lambda x: [None] if pd.isna(x) else x)
gdf_output['soortnaam'] = [{dict_key_mapping.get(k, k): v for k, v in my_dict.items()} for my_dict in gdf_output['soortnaam']]  # Rename keys using dictionary comprehension

## Convert gdf to list of OTLAssets
list_OTLAssets = gdf_to_OTLAssets(gdf_output)

######################################################################
### Schrijf weg naar DAVIE-file
######################################################################
# Volledige export van alle bomen verwerken en wegschrijven naar JSON/Excel files.
# GEOJSON formaat is ongeldig DAVIE formaat. Zie: https://github.com/davidvlaminck/OTLMOW-Converter/issues/21
converter = OtlmowConverter()
converter.create_file_from_assets(filepath=Path('./output/DA-2024-xxxxx.geojson'), list_of_objects=list_OTLAssets)
converter.create_file_from_assets(filepath=Path('./output/DA-2024-xxxxx.xlsx'), list_of_objects=list_OTLAssets)