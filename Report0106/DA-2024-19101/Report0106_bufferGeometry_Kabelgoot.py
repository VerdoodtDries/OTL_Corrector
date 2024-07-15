## Import packages
from HelperFunctions.utils import plot_gdf, split_list
import os.path
from pathlib import Path
from otlmow_converter.OtlmowConverter import OtlmowConverter
from otlmow_model.OtlmowModel.BaseClasses.MetaInfo import meta_info
from otlmow_model.OtlmowModel.BaseClasses.OTLObject import dynamic_create_instance_from_uri
from otlmow_model.OtlmowModel.BaseClasses.OTLObject import OTLObject
from otlmow_model.OtlmowModel.Helpers.OTLObjectHelper import print_overview_assets
from otlmow_converter.FileFormats.PandasConverter import PandasConverter
import uuid
import pandas as pd
import sqlite3
from shapely.geometry import Point, Polygon, LineString
from shapely import wkt, force_3d
import logging
from EMInfraImporter import EMInfraImporter
from RequestHandler import RequestHandler
from RequesterFactory import RequesterFactory
from SettingsManager import SettingsManager
from AssetUpdater import AssetUpdater
import geopandas as gpd

## Variables
filename = r"C:\Users\DriesVerdoodtNordend\Downloads\[RSA] Geometrie is consistent met GeometrieArtefact_20240715.xlsx"
feature_type = 'Resultaat' # This is the layer name or the Excel sheet name

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


# Read the Sqlite file in a pandas dataframe
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
except FileNotFoundError as e:
    raise FileNotFoundError(f"The file {filepath} does not exist.") from e


# Launch the API request to obtain data
asset_uuids = df_input['uuid'].tolist()
asset_uuids = [i[:36] for i in asset_uuids] # Behoud enkel de eerste 36 karakters, hetgeen overeenkomt met de uuid, en niet de volledige AIM-ID
print(f'Asset UUID'f's: {asset_uuids}')


# Process the assets in groups (bins) of maximum 100.
# Split the list asset_uuids in groups of maximum 100 assets (list containing sublists of maximum 100 records).
asset_uuids_bin100 = split_list(asset_uuids)
asset_dicts_dict = {}  # Instantiate an empty dictionary to fill later on
for bin_asset_uuids in asset_uuids_bin100:
    object_generator = eminfra_importer.import_assets_from_webservice_by_uuids(asset_uuids=bin_asset_uuids)
    print(f'Type: {type(object_generator)}\nResponse: {object_generator}')
    asset_dicts_dict |= AssetUpdater.get_dict_from_object_generator(object_generator)  ## |= is the update operator for dictionaries.


# Convert the data to a dataframe
df_eminfra = pd.DataFrame(data=asset_dicts_dict)
# Transpose rows and column
df_eminfra = df_eminfra.transpose()
print(f'Type: {type(df_eminfra)}')
print(f'Dataframe: {df_eminfra}')

# Create a GeoSeries
gs_geometry = gpd.GeoSeries.from_wkt(df_eminfra['loc:Locatie.geometrie'])
print(f'Type: {type(gs_geometry)}')
print(f'Geoseries: {gs_geometry}')


# Convert the DataFrame to a GeoDataFrame
gdf_asset = gpd.GeoDataFrame(df_eminfra, geometry=gs_geometry, crs="EPSG:31370")
# Set attribute uuid
gdf_asset['uuid'] = gdf_asset['@id'].str.split('/').str[-1]

##gdf_sample = gdf_asset.iloc[[0]].copy()
##plot_gdf(gdf_sample, filename='1 line', fanout=False)

# Buffer the geometry column
gdf_asset['geometry'] = gdf_asset.geometry.buffer(distance=0.25, cap_style='flat', join_style='bevel')
##gdf_sample_buffer = gdf_asset.iloc[[0]].copy()
##plot_gdf(gdf_sample_buffer, filename='1 line buffered', fanout=False)

# plot the geodataframe
# Plot 1 record (originele kabelgoot)
# Plot dezelfde record (gebufferde kabelgoot)
##plot_gdf(gdf_asset, filename=' ', fanout=False)

# Set z-values to zero for all geometries
gdf_asset.geometry = force_3d(geometry=gdf_asset.geometry, z=0)

# Keep only the columns: uuid, @type, geometry
columns_to_keep = ['uuid', '@type', 'geometry']
gdf_asset = gdf_asset.filter(items=columns_to_keep).copy()
# Rename columns
gdf_asset = gdf_asset.rename(columns={'@type': 'typeURI'})
gdf_asset['notitie'] = 'Oorspronkelijke lijnen gebufferd met 25cm in overeenstemming met het GeometrieArtefact'


##gdf_asset['geometry'] = gdf_asset['geometry'].apply(lambda geom: geom.wkt) # Convert geometries to WKT
gdf_asset['geometry'] = gdf_asset['geometry'].apply(lambda geom: wkt.dumps(geom))  # Convert geometries to WKT
# Convert to JSON
## Convert gdf to list of dictionaries
list_of_dict_asset = gdf_asset.to_dict(orient='records')

# Edit the attribute assetId.identificator.
for list_element in list_of_dict_asset:
    list_element['assetId'] = {'identificator': list_element.pop('uuid')}

list_OTLAssets_asset = []

# dict to otlmow model
for asset in list_of_dict_asset:
    OTLAsset = OTLObject.from_dict(asset)
    list_OTLAssets_asset.append(OTLAsset)

converter = OtlmowConverter()
converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_ASSETTYPE.geojson'), list_of_objects=list_OTLAssets_asset)
