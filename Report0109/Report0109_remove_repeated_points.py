## Import packages
from pathlib import Path
from otlmow_converter.OtlmowConverter import OtlmowConverter
from otlmow_model.OtlmowModel.BaseClasses.OTLObject import dynamic_create_instance_from_uri
from otlmow_model.OtlmowModel.BaseClasses.OTLObject import OTLObject
from otlmow_model.OtlmowModel.Helpers.OTLObjectHelper import print_overview_assets
from otlmow_converter.FileFormats.PandasConverter import PandasConverter
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
from collections import defaultdict
import os

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



# Read the Excel file in a dataframe
excel_path = r"C:\Users\DriesVerdoodtNordend\Downloads\[RSA] Geometrie is geldig_ geen opeenvolgende punten_20240813.xlsx"
df_report0109 = pd.read_excel(excel_path, sheet_name='Resultaat', header=2)
#print(df_report0109)

# Filter het dataframe, behoud alle records waar de wkt_string !~ 'MULTI'
# Create a boolean mask for rows that contain 'MULTI'
mask = df_report0109['wkt_string_prefix'].str.contains('MULTI')
# Negate the mask to get rows that do not contain 'MULTI'
df_report0109_filtered = df_report0109[~mask]
#print(df_report0109_filtered)

# Launch the API request to obtain data
typeURI = df_report0109_filtered['typeuri'].tolist()
uuid = df_report0109_filtered['assetuuid'].tolist()
#print(f'typeURI: {typeURI}')
#print(f'uuid: {uuid}')


object_generator = eminfra_importer.import_assets_from_webservice_by_uuids(asset_uuids=uuid)
#print(f'Type: {type(object_generator)}\nResponse: {object_generator}')

#asset_dicts_dict = AssetUpdater.get_dict_from_object_generator(object_generator)
asset_dicts_dict = AssetUpdater.get_dict_from_object_generator(object_generator)


# Convert the data to a dataframe
df = pd.DataFrame(data=asset_dicts_dict)
# Transpose rows and column
df = df.transpose()
#print(f'Type: {type(df)}')
#print(f'Dataframe: {df}')

# Create a GeoSeries
gs_geometry = gpd.GeoSeries.from_wkt(df['loc:Locatie.geometrie'])
#print(f'Type: {type(gs_geometry)}')
#print(f'Geoseries: {gs_geometry}')

# Convert the DataFrame to a GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry=gs_geometry, crs="EPSG:31370")

# Count the number of point before and after the geometry correction with function remove_repeated_points()
gdf['num_points1'] = gdf['geometry'].apply(count_coordinates)
gdf['num_points2'] = remove_repeated_points(gdf['geometry']).apply(count_coordinates)
print(f'Calling the shapely function "remove_repeated_points" to reduce duplicate consecutive points.')
print(f"This is the resulting number of points for the records in the Geodataframe:\n\n{gdf[['num_points1', 'num_points2']]}")

series1 = gdf['geometry']
series2 = remove_repeated_points(gdf['geometry'])

# update the geometry column
gdf['geometry'] = series2

# Convert to JSON
# Keep only some columns, rename the columns
columns_to_keep = ['@id', '@type', 'AIMDBStatus.isActief', 'geometry']
gdf_output = gdf.filter(items=columns_to_keep).copy()
#print(f'Geodataframe to export: {gdf_output}')

# Rename multiple columns
gdf_output = gdf_output.rename(columns={'@id': 'assetId.identificator', "@type": 'typeURI', 'AIMDBStatus.isActief': 'isActief'})
# Keeping only the part after the last forward slash and replacing the original column
gdf_output['assetId.identificator'] = gdf_output['assetId.identificator'].str.split('/').str[-1]
# gdf_output = gdf_output.reset_index()
#print(gdf_output)

# Convert geometries to WKT
gdf_output['geometry'] = gdf_output['geometry'].apply(lambda geom: geom.wkt)

## Convert gdf to list of dictionaries
list_of_dict = gdf_output.to_dict(orient='records')
# Edit the attribute assetId.identificator.
for i, list_element in enumerate(list_of_dict):
    list_element['assetId'] = {'identificator': list_element['assetId.identificator']}
    del list_element['assetId.identificator'] # verwijder dit dictionary element
#print(list_of_dict)

list_OTLAssets = []
# dict to otlmow model
for asset in list_of_dict:
    #print(f'Asset: {asset}')
    OTLAsset = OTLObject.from_dict(asset)
    #print(f'OTL-asset: {OTLAsset}')
    list_OTLAssets.append(OTLAsset)

# Example sorted list based on type name
list_OTLAssets = sorted(list_OTLAssets, key=lambda x: type(x).__name__)

# Group elements by their type
type_groups = defaultdict(list)  # create a dictionary of lists
for item in list_OTLAssets:
    type_name = type(item).__name__
    type_groups[type_name].append(item)

# Instantiate the converter
converter = OtlmowConverter()

os.makedirs('DA-2024-21600', exist_ok=True)
# Export each type group to a separate file
for type_name, items in type_groups.items():
    # Generate a unique file name for each type
    filepath = Path(f'DA-2024-21600/{type_name}.geojson')

    # Export to file
    converter.create_file_from_assets(filepath=filepath, list_of_objects=items)

    print(f"Created file for {type_name} with {len(items)} items: {filepath}")