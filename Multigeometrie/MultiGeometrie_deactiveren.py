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
import xlsxwriter
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


######################################################################
### Define variables
######################################################################
filename = 'multigeometrie_uuids.csv'
filepath = Path(r'C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\OTL_Aanpassingen\MultiGeometrie_Deactiveren\multigeometrie_uuids.csv')
feature_type = None

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

print(f'input dataframe: {df_input}')

# Launch the API request to obtain data
asset_uuids = df_input['assetId.identificator'].tolist()
asset_uuids = [i[:36] for i in asset_uuids]


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

df = pd.DataFrame(data=asset_dicts_dict)
df = df.transpose()

# Create a GeoSeries
gs_geometry = gpd.GeoSeries.from_wkt(df['loc:Locatie.geometrie'])

# Convert the DataFrame to a GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry=gs_geometry, crs="EPSG:31370")


######################################################################
### Preprocessing gdf alvorens wegschrijven
######################################################################
# Behoud sommige attributen
# Omit geometry
columns_to_keep = ['@id', '@type', 'AIMDBStatus.isActief']
gdf_output = gdf.filter(items=columns_to_keep)

# Rename columns
gdf_output = gdf_output.rename(columns={'@id': 'assetId.identificator', "@type": 'typeURI', 'AIMDBStatus.isActief': 'isActief'})
# Keeping only the part after the last forward slash and replacing the original column
gdf_output['assetId.identificator'] = gdf_output['assetId.identificator'].str.split('/').str[-1]

gdf_output['geometry'] = '88888888'

list_OTLAssets = gdf_to_OTLAssets(gdf_output)
######################################################################
### Schrijf weg naar DAVIE-file
######################################################################
converter = OtlmowConverter()
if list_OTLAssets:
    # converter.from_objects_to_file(file_path=Path('DA-2024-24432.xlsx'), sequence_of_objects=list_OTLAssets)
    # converter.from_objects_to_file(file_path=Path('DA-2024-24432.geojson'), sequence_of_objects=list_OTLAssets)
    converter.from_objects_to_file(file_path=Path('DA-2024-24432.json'), sequence_of_objects=list_OTLAssets)
