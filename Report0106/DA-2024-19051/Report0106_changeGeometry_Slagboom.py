## Import packages
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
from shapely import wkt
import logging
from EMInfraImporter import EMInfraImporter
from RequestHandler import RequestHandler
from RequesterFactory import RequesterFactory
from SettingsManager import SettingsManager
from AssetUpdater import AssetUpdater
import geopandas as gpd

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


## Functions


# Read the Sqlite file in a pandas dataframe
sqlite_path = r"C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\Report0106\DA-2024-19051\DA-2024-19051.sqlite"

# Read the data from the SQLite database into a geopandas geodataframe
gdf_new_geometry = gpd.read_file(sqlite_path, layer='Slagboom')

# Display the DataFrame
print(gdf_new_geometry)

# Launch the API request to obtain data
asset_uuids = gdf_new_geometry['AIMID'].tolist()
asset_uuids = [i[:36] for i in asset_uuids] # Behoud enkel de eerste 36 karakters, hetgeen overeenkomt met de uuid, en niet de volledige AIM-ID
print(f'Asset UUID'f's: {asset_uuids}')

object_generator = eminfra_importer.import_assets_from_webservice_by_uuids(asset_uuids=asset_uuids)
print(f'Type: {type(object_generator)}\nResponse: {object_generator}')

asset_dicts_dict = AssetUpdater.get_dict_from_object_generator(object_generator)


# Convert the data to a dataframe
df = pd.DataFrame(data=asset_dicts_dict)
# Transpose rows and column
df = df.transpose()
print(f'Type: {type(df)}')
print(f'Dataframe: {df}')

# Create a GeoSeries
gs_geometry = gpd.GeoSeries.from_wkt(df['loc:Locatie.geometrie'])
print(f'Type: {type(gs_geometry)}')
print(f'Geoseries: {gs_geometry}')

# Convert the DataFrame to a GeoDataFrame
gdf_slagboom = gpd.GeoDataFrame(df, geometry=gs_geometry, crs="EPSG:31370")
# Set attribute uuid
gdf_slagboom['uuid'] = gdf_slagboom['@id'].str.split('/').str[-1]

# Replace the geometry column
# 0. Prefix one gdf to make a distinction between both
# 1. Merge the gdf dataframe
# 2. Replace the geometry column
gdf_new_geometry = gdf_new_geometry.add_prefix('new_geom_')

# Merge the GeoDataFrames based on the common key
gdf_slagboom = gdf_slagboom.merge(gdf_new_geometry, left_on='uuid', right_on='new_geom_AIMID')

# Keep only the columns: uuid, new_geom_geometry
columns_to_keep = ['uuid', 'new_geom_geometry', '@type', 'new_geom_notitie']
gdf_slagboom = gdf_slagboom.filter(items=columns_to_keep).copy()
# Rename columns
gdf_slagboom = gdf_slagboom.rename(columns={'@type': 'typeURI', 'new_geom_geometry': 'geometry', 'new_geom_notitie': 'notitie'})
##gdf_dwarse_markering['geometry'] = gdf_dwarse_markering['geometry'].apply(lambda geom: geom.wkt) # Convert geometries to WKT
gdf_slagboom['geometry'] = gdf_slagboom['geometry'].apply(lambda geom: wkt.dumps(geom)) # Convert geometries to WKT

# Convert to JSON
## Convert gdf to list of dictionaries
list_of_dict_slagboom = gdf_slagboom.to_dict(orient='records')

# Edit the attribute assetId.identificator.
for list_element in list_of_dict_slagboom:
    list_element['assetId'] = {'identificator': list_element.pop('uuid')}

list_OTLAssets_slagboom = []

# dict to otlmow model
for asset in list_of_dict_slagboom:
    OTLAsset = OTLObject.from_dict(asset)
    list_OTLAssets_slagboom.append(OTLAsset)

converter = OtlmowConverter()
converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_ASSETTYPE.geojson'), list_of_objects=list_OTLAssets_slagboom)
