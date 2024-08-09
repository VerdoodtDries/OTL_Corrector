######################################################################
### Import packages
######################################################################
# sourcery skip: remove-redundant-fstring
from pathlib import Path
from otlmow_converter.OtlmowConverter import OtlmowConverter
from otlmow_model.OtlmowModel.BaseClasses.MetaInfo import meta_info
from otlmow_model.OtlmowModel.BaseClasses.OTLObject import dynamic_create_instance_from_uri
from otlmow_model.OtlmowModel.BaseClasses.OTLObject import OTLObject
from otlmow_model.OtlmowModel.Helpers.OTLObjectHelper import print_overview_assets
from otlmow_converter.FileFormats.PandasConverter import PandasConverter
from fuzzywuzzy import fuzz
from HelperFunctions.utils import split_list, gdf_to_OTLAssets
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
import matplotlib.pyplot as plt

matplotlib.use('TkAgg')
import contextily as ctx
from matplotlib.ticker import ScalarFormatter
import os

######################################################################
### Define variables
######################################################################
filename = r"C:\Users\DriesVerdoodtNordend\Downloads\[RSA] Geometrie is consistent met GeometrieArtefact_20240808.xlsx"
feature_type = 'Resultaat'  # This is the layer name or the Excel sheet name
asset_of_interest = 'Netwerkelement'


######################################################################
### Print meta_info as the Asset
######################################################################
type_uri = 'https://wegenenverkeer.data.vlaanderen.be/ns/onderdeel#Netwerkelement'
asset = dynamic_create_instance_from_uri(type_uri)
print(meta_info(asset))



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

    requester = RequesterFactory.create_requester(settings=settings_manager.settings, auth_type='JWT', env='prd',
                                                  multiprocessing_safe=True)
    request_handler = RequestHandler(requester)

    eminfra_importer = EMInfraImporter(request_handler)


######################################################################
### Read input data in a pandas dataframe
######################################################################
script_dir = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(script_dir, filename)

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

######################################################################
### Filter input dataframe voor een specifiek asset
######################################################################
df_input_asset_of_interest = df_input[df_input['naam'] == asset_of_interest]
## Temp sample the first record
df_input_asset_of_interest = df_input_asset_of_interest.iloc[1:,:]

# Launch the API request to obtain data
asset_uuids = df_input_asset_of_interest['uuid'].tolist()
asset_uuids = [i[:36] for i in
               asset_uuids]  # Behoud enkel de eerste 36 karakters, hetgeen overeenkomt met de uuid, en niet de volledige AIM-ID

######################################################################
### Launch the API request to obtain data
######################################################################
# Haal de relaties op via de uuid.
# Converteer naar een pandas dataframe
# Voeg een kolom toe met de uuid van de correcte bijhorende asset (waarvan we de geometrie gaan overnemen)
# Haal de bron-asset op via de uuid.
# Haal de doel-asset op via de uuid.
# Merge de dataframes opdat de geometrie aan de originele asset wordt toegewezen.

asset_uuids_bin100 = split_list(asset_uuids, max_elements=100)
relations_dict = {}
for bin_asset_uuids in asset_uuids_bin100:
    # Bewaar de resultaten per match
    object_generator = eminfra_importer.import_assetrelaties_from_webservice_by_assetuuids(asset_uuids=bin_asset_uuids)
    ## print(f'Type: {type(object_generator)}\nResponse: {object_generator}')
    relations_dict |= AssetUpdater.get_dict_from_object_generator(
        object_generator)  ## |= is the update operator for dictionaries.

df_relations = pd.DataFrame(data=relations_dict).transpose()

df_relations_filter = df_relations[
    (df_relations['AIMDBStatus.isActief'] == True)  # actieve relaties
    &
    (
        (df_relations['RelatieObject.typeURI'].str.endswith('HoortBij'))  # relatietype HoortBij
        |
        (df_relations['RelatieObject.typeURI'].str.endswith('Bevestiging'))  # relatietype HoortBij
    )
    #&
    #df_relations['RelatieObject.doel'].apply(lambda x: x['@type'].endswith('installatie#IP'))  # doel-asset is IP
]


# Normalize de json-kolom van het dataframe.
df_relaties_bron_normalized = pd.json_normalize(df_relations_filter['RelatieObject.bron']).set_index(df_relations_filter.index)
df_relaties_doel_normalized = pd.json_normalize(df_relations_filter['RelatieObject.doel']).set_index(df_relations_filter.index)
# Rename columns using a dictionary, append prefix "RelatieObject.bron." and "RelatieObject.doel."
df_relaties_bron_normalized = df_relaties_bron_normalized.rename(columns={'@type': 'RelatieObject.bron.@type', '@id': 'RelatieObject.bron.@id'})
df_relaties_doel_normalized = df_relaties_doel_normalized.rename(columns={'@type': 'RelatieObject.doel.@type', '@id': 'RelatieObject.doel.@id'})
# Rewrite the uuid, keep the first 36 characters
df_relaties_bron_normalized['RelatieObject.bron.uuid'] = df_relaties_bron_normalized['RelatieObject.bron.@id'].apply(lambda x: x.split('/')[-1][:36])
df_relaties_doel_normalized['RelatieObject.doel.uuid'] = df_relaties_doel_normalized['RelatieObject.doel.@id'].apply(lambda x: x.split('/')[-1][:36])

# Combine with the original DataFrame (append)
df_relations_filter = pd.concat([df_relations_filter, df_relaties_bron_normalized], axis=1)
df_relations_filter = pd.concat([df_relations_filter, df_relaties_doel_normalized], axis=1)


# Lanceer de API-request om de geometrie op te halen van bron-assets en doel-assets van de relaties
# Bron-asset
bron_asset_uuids = df_relations_filter['RelatieObject.bron.uuid']
bron_asset_uuids_bin100 = split_list(bron_asset_uuids, max_elements=100)
asset_dicts_dict = {}  # Instantiate an empty dictionary to fill later on
for bin_bron_asset_uuids in bron_asset_uuids_bin100:
    # Bewaar de resultaten per match
    object_generator = eminfra_importer.import_assets_from_webservice_by_uuids(asset_uuids=bin_bron_asset_uuids)
    ## print(f'Type: {type(object_generator)}\nResponse: {object_generator}')
    asset_dicts_dict |= AssetUpdater.get_dict_from_object_generator(
        object_generator)  ## |= is the update operator for dictionaries.
df_bron_asset = pd.DataFrame(data=asset_dicts_dict).transpose()
columns_to_keep = ['@id', '@type']
df_bron_asset = df_bron_asset.loc[:, columns_to_keep].add_prefix('bron.')

# Doel-asset
doel_asset_uuids = df_relations_filter['RelatieObject.doel.uuid']
doel_asset_uuids_bin100 = split_list(doel_asset_uuids, max_elements=100)
asset_dicts_dict = {}  # Instantiate an empty dictionary to fill later on
for bin_doel_asset_uuids in doel_asset_uuids_bin100:
    # Bewaar de resultaten per match
    object_generator = eminfra_importer.import_assets_from_webservice_by_uuids(asset_uuids=bin_doel_asset_uuids)
    ## print(f'Type: {type(object_generator)}\nResponse: {object_generator}')
    asset_dicts_dict |= AssetUpdater.get_dict_from_object_generator(
        object_generator)  ## |= is the update operator for dictionaries.
df_doel_asset = pd.DataFrame(data=asset_dicts_dict).transpose()
columns_to_keep = ['@id', '@type', 'loc:Locatie.geometrie']
try:
    # Attempt to select and prefix columns
    df_doel_asset = df_doel_asset.loc[:, columns_to_keep].add_prefix('doel.')
except KeyError as e:
    # Handle the error if one or more columns do not exist
    print(f"Error: One or more columns do not exist in the DataFrame: {e}")

# Merge de dataframes en link zo de wkt-geometrie aan de originele asset: df_bron_asset; df_doel_asset; df_relations_filter
df_output = pd.merge(left=df_bron_asset, right=df_relations_filter, how='left', left_on='bron.@id', right_on='RelatieObject.bron.@id')
df_output = pd.merge(left=df_output, right=df_doel_asset, how='left', left_on='RelatieObject.doel.@id', right_on='doel.@id')

# Extra filter voor de assets zonder goemetrie
df_output['doel.loc:Locatie.geometrie'] = df_output['doel.loc:Locatie.geometrie'].fillna('') # Fill nan with empty string
df_output_na_geom = df_output[
    (df_output['doel.loc:Locatie.geometrie'] == '')
]

df_output_geom = df_output[
    df_output['doel.loc:Locatie.geometrie'].str.startswith('POINT Z')
]

# Create a GeoSeries
gs_geometry = gpd.GeoSeries.from_wkt(df_output_geom['doel.loc:Locatie.geometrie'])
# Convert the DataFrame to a GeoDataFrame
gdf_output = gpd.GeoDataFrame(df_output_geom, geometry=gs_geometry, crs="EPSG:31370")

######################################################################
### Process gdf alvorens wegschrijven
######################################################################
# Behoud sommige attributen
columns_to_keep = ['bron.@id', 'bron.@type', 'doel.loc:Locatie.geometrie']
gdf_output = gdf_output.filter(items=columns_to_keep)
# Rename columns
gdf_output = gdf_output.rename(columns={'bron.@id': 'assetId.identificator', "bron.@type": 'typeURI', 'doel.loc:Locatie.geometrie': 'geometry'})
# Keeping only the part after the last forward slash and replacing the original column
gdf_output['assetId.identificator'] = gdf_output['assetId.identificator'].str.split('/').str[-1]
##gdf_output['assetId.toegekendDoor'] = 'AWV'
# Shapely functie .wkt is overbodig
# Convert geometries to WKT. Na dit punt wordt de geodataframe een normaal dataframe.
#gdf_output['geometry'] = gdf_output['geometry'].apply(lambda geom: geom.wkt)

######################################################################
### Converteer gdf naar dictionary
######################################################################
## Convert gdf to list of OTLAssets
list_OTLAssets = gdf_to_OTLAssets(gdf_output)


######################################################################
### Schrijf weg naar DAVIE-file
######################################################################
# Wegschrijven naar JSON/Excel files.
# GEOJSON formaat is ongeldig DAVIE formaat. Zie: https://github.com/davidvlaminck/OTLMOW-Converter/issues/21
converter = OtlmowConverter()
converter.create_file_from_assets(filepath=Path(f'{asset_of_interest}_XXXXX.geojson'), list_of_objects=list_OTLAssets)
converter.create_file_from_assets(filepath=Path(f'{asset_of_interest}_XXXXX.xlsx'), list_of_objects=list_OTLAssets)

# Objecten zonder geometrie
df_output_na_geom.to_csv(f'{asset_of_interest}_na_geometrie.csv', sep=';')