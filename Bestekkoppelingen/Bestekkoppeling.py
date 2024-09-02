######################################################################
### Import packages
######################################################################
import os
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


######################################################################
### Define variables
######################################################################


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


# Willekeurige asset
# Geleideconstructie
# New-Jerseyblocks langs E411 in Overijse, zonder en mét een bestek. Bestekkoppeling geeft een empty string terug.

# dev
asset_uuids = ['1e793570-1a08-40e6-95d8-96240ed88f34']  # Geen bestek gekoppeld
#asset_uuids = ['3171d773-166a-426f-8b0f-707c9a694a16']  # bestek gekoppeld
# tei
#asset_uuids = ['1a611542-8a8b-42d4-92d8-7a8652e65316'] # Bestek zonder koppeling tei
#prd
asset_uuids = ['1f622605-aa54-47eb-ab06-2d77e12f1d2a']
asset_uuids = ['63cf7fa1-1310-4931-8f30-903581849c7d']  # Dwarse Markering N275 Hoeilaart

######################################################################
### API Call: ophalen bestekkoppeling
######################################################################
object_generator = eminfra_importer.get_all_bestekkoppelingen_from_webservice_by_asset_uuids_installaties(asset_uuids=asset_uuids)
bestekkoppelingen_dict = {}

bestekkoppelingen_dict |= AssetUpdater.get_dict_from_object_generator(object_generator)

######################################################################
### API Call: Ophalen aanleveringen door Dries Verdoodt
######################################################################


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
# Transpose rows and column
df = df.transpose()
## print(f'Type: {type(df)}')
## print(f'Dataframe: {df}')

# Create a GeoSeries
gs_geometry = gpd.GeoSeries.from_wkt(df['loc:Locatie.geometrie'])
## print(f'Type: {type(gs_geometry)}')
## print(f'Geoseries: {gs_geometry}')

# Convert the DataFrame to a GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry=gs_geometry, crs="EPSG:31370")

######################################################################
### Process dataframe
######################################################################
# Toevoegen van de naam van de provincie
filepath_provincie = 'Refprv.sqlite'
gdf_provincie = gpd.read_file(filepath_provincie, layer='Refprv')
# When you perform an overlay operation using gpd.overlay(),
# the resulting GeoDataFrame does not retain the original indices of the input GeoDataFrames.
# However, you can keep the original indices by temporarily storing them as a new column in the input GeoDataFrames
# before performing the overlay.
# After the overlay, you can set the original indices back.
# Add a temporary column to store the original index
gdf['original_index'] = gdf.index
gdf = gpd.overlay(gdf, gdf_provincie, how='intersection')
# Restore the original index and drop the temporary column
gdf.set_index('original_index', inplace=True)

# Add a column "id_duplicate_asset". This is the column to detect the duplicate assets (identical trees).
# Step 1: Merge the input dataframe (df_input) and add the column "boom2_uuid".
# preprocess df_input: set index, keep only boom1_uuid and boom2_uuid
# Keep a minimalistic version of df_input
df_input_minimal = df_input[["boom1_uuid", "boom2_uuid"]].copy()
df_input_minimal.set_index("boom1_uuid", drop=False, inplace=True)
gdf = pd.merge(gdf, df_input_minimal, left_index=True, right_index=True, how='left')
# Step 2: Create a sorted tuple for each combination of 'uuid1' and 'uuid2'
#         Add a column that indicates the match between two assets: id_duplicate_asset
gdf['id_duplicate_asset'] = gdf.apply(lambda row: tuple(sorted([row['boom1_uuid'], row['boom2_uuid']])), axis=1)

# Sort the dataframe for visual inspection
gdf.sort_values(by="id_duplicate_asset", inplace=True)


######################################################################
### Preprocessing gdf alvorens wegschrijven
######################################################################
# Behoud sommige attributen
columns_to_keep = ['@id', '@type', 'AIMDBStatus.isActief', 'geometry', 'PROVINCIE']
gdf_output = gdf_output.filter(items=columns_to_keep)
## print(f'Geodataframe to export: {gdf_output}')
# Set isActief = False
gdf_output['AIMDBStatus.isActief'] = False

# Rename columns
gdf_output = gdf_output.rename(columns={'@id': 'assetId.identificator', "@type": 'typeURI', 'AIMDBStatus.isActief': 'isActief'})
# Keeping only the part after the last forward slash and replacing the original column
gdf_output['assetId.identificator'] = gdf_output['assetId.identificator'].str.split('/').str[-1]
# Convert geometries to WKT. Na dit punt wordt de geodataframe een normaal dataframe.
gdf_output['geometry'] = gdf_output['geometry'].apply(lambda geom: geom.wkt)


######################################################################
### Converteer gdf naar dictionary
######################################################################
## Convert gdf to list of OTLAssets
list_OTLAssets = gdf_to_OTLAssets(gdf_output)

######################################################################
### Schrijf weg naar DAVIE-file
######################################################################
# Volledige export van alle bomen verwerken en wegschrijven naar JSON/Excel files.
# GEOJSON formaat is ongeldig DAVIE formaat. Zie: https://github.com/davidvlaminck/OTLMOW-Converter/issues/21
converter = OtlmowConverter()
converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx.geojson'), list_of_objects=list_OTLAssets)
converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx.xlsx'), list_of_objects=list_OTLAssets)