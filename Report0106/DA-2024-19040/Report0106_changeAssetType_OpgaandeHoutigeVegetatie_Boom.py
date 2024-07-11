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
from shapely import wkt
from shapely.geometry import Point, Polygon, LineString
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


# Read the CSV file in a dataframe
csv_path = r"C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\Report0106\DA-2024-19040\OpgaandeHoutigeVegetatie.csv"
df_OpgaandeHoutigeVegetatie = pd.read_csv(csv_path, delimiter=';')
print(df_OpgaandeHoutigeVegetatie)

# Launch the API request to obtain data
asset_uuids = df_OpgaandeHoutigeVegetatie['uuid'].tolist()
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
gdf = gpd.GeoDataFrame(df, geometry=gs_geometry, crs="EPSG:31370")

# Convert to JSON
# Keep only some columns, rename the columns
columns_to_keep = ['@id', '@type', 'geometry']
gdf_output = gdf.filter(items=columns_to_keep).copy()

# Rename multiple columns
gdf_output = gdf_output.rename(columns={'@id': 'assetId.identificator', "@type": 'typeURI'})
# Keeping only the part after the last forward slash and replacing the original column
gdf_output['assetId.identificator'] = gdf_output['assetId.identificator'].str.split('/').str[-1]
# gdf_output = gdf_output.reset_index()
print(gdf_output)

gdf_output['geometry'] = gdf_output['geometry'].apply(lambda geom: geom.wkt)  # Convert geometries to WKT

# Copy the geodataframe
gdf_output_opgaandehoutigevegetatie = gdf_output.copy()
gdf_output_boom = gdf_output.copy()

# Postprocessing Opgaande Houtige Vegetatie
gdf_output_opgaandehoutigevegetatie['isActief'] = False
gdf_output_opgaandehoutigevegetatie['notitie'] = 'gedeactiveerd en nieuwe nieuwe asset aangemaakt met assettype Boom'
del gdf_output_opgaandehoutigevegetatie['geometry']

# Postprocessing Boom
gdf_output_boom['typeURI'] = 'https://wegenenverkeer.data.vlaanderen.be/ns/onderdeel#Boom'
# Genereer een nieuwe willekeurige uuid
gdf_output_boom['assetId.identificator'] = gdf_output_boom['assetId.identificator'].apply(lambda _: str(uuid.uuid4()))

## Convert gdf to list of dictionaries
list_of_dict_opgaandehoutigevegetatie = gdf_output_opgaandehoutigevegetatie.to_dict(orient='records')
list_of_dict_boom = gdf_output_boom.to_dict(orient='records')

# Edit the attribute assetId.identificator.
for list_element in list_of_dict_opgaandehoutigevegetatie:
    list_element['assetId'] = {'identificator': list_element.pop('assetId.identificator')}

for list_element in list_of_dict_boom:
    list_element['assetId'] = {'identificator': list_element.pop('assetId.identificator')}

list_OTLAssets_opgaandehoutigevegetatie = []
list_OTLAssets_boom = []

# dict to otlmow model
for asset in list_of_dict_opgaandehoutigevegetatie:
    OTLAsset = OTLObject.from_dict(asset)
    list_OTLAssets_opgaandehoutigevegetatie.append(OTLAsset)

# dict to otlmow model
for asset in list_of_dict_boom:
    OTLAsset = OTLObject.from_dict(asset)
    list_OTLAssets_boom.append(OTLAsset)

converter = OtlmowConverter()
converter.create_file_from_assets(filepath=Path('DA-2024-19040_OpgaandeHoutigeVegetatie.csv'), list_of_objects=list_OTLAssets_opgaandehoutigevegetatie)
converter.create_file_from_assets(filepath=Path('DA-2024-19040_Boom.csv'), list_of_objects=list_OTLAssets_boom)
converter.create_file_from_assets(filepath=Path('DA-2024-19040_Boom.geojson'), list_of_objects=list_OTLAssets_boom)