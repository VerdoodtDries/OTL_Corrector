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
from HelperFunctions.utils import split_list, gdf_to_OTLAssets, get_wkt_length
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
import re

matplotlib.use('TkAgg')
import contextily as ctx
from matplotlib.ticker import ScalarFormatter
import os


######################################################################
### Print meta_info as the Asset
######################################################################
##straatkolk_type_uri = 'https://wegenenverkeer.data.vlaanderen.be/ns/onderdeel#Straatkolk'
##straatkolk = dynamic_create_instance_from_uri(straatkolk_type_uri)
##print(meta_info(straatkolk))


######################################################################
### Define variables
######################################################################
filename = r"C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\Simplify_WKT_string\Assets_wkt_string_32767_karakters.csv"
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

# Launch the API request to obtain data
asset_uuids = df_input['uuid'].tolist()
asset_uuids = [i[:36] for i in
               asset_uuids]  # Behoud enkel de eerste 36 karakters, hetgeen overeenkomt met de uuid, en niet de volledige AIM-ID

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

# Filter de geodataframe. Behoud records waarbij de typeURI start met "https://www.wegenenverkeer.be"
df = df[df['@type'].str.contains('^(https://wegenenverkeer.data.vlaanderen.be).*', flags=re.IGNORECASE, regex=True)]

# Create a GeoSeries
gs_geometry = gpd.GeoSeries.from_wkt(df['loc:Locatie.geometrie'])
## print(f'Type: {type(gs_geometry)}')
## print(f'Geoseries: {gs_geometry}')

# Convert the DataFrame to a GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry=gs_geometry, crs="EPSG:31370")

######################################################################
### Process dataframe
######################################################################
# Behoud de relevante attributen: typeUri, id, geometry
columns_to_keep = ['@id', '@type', 'AIMDBStatus.isActief', 'geometry']
gdf_output = gdf.filter(items=columns_to_keep)

# Tel het aantal coordinaten / tekstkarakters van de geometrie vóór generalisatie.
gdf_output["nbr_coordinates"] = gdf_output['geometry'].apply(count_coordinates)
gdf_output["nbr_characters"] = gdf_output['geometry'].apply(get_wkt_length)

## Installeer hier een loop. Verhoog de tolerantie totdat het aantal karakters van de WKT string kleiner is dan 32767
tolerances = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5]
for tolerance in tolerances:
    mask = gdf_output['nbr_characters'] > 32767

    if mask.sum() > 0:
        print(f'Simplifying the geometry of {mask.sum()} records using tolerance of {tolerance} meters.')
        # Apply the function to the filtered records
        gdf_output.loc[mask, 'geometry'] = gdf_output.loc[mask, 'geometry'].apply(lambda geom: geom.simplify(tolerance=tolerance, preserve_topology=True))
        # Tel het aantal coordinaten / tekstkarakters van de geometrie ná generalisatie
        gdf_output["nbr_coordinates"] = gdf_output['geometry'].apply(count_coordinates)
        gdf_output["nbr_characters"] = gdf_output['geometry'].apply(get_wkt_length)
    else:
        print(
            'End of process. Geometry is no longer simplified. Break out of the loop.'
        )
        break

# Behoud de relevante attributen: typeUri, id, geometry
columns_to_keep = ['@id', '@type', 'AIMDBStatus.isActief', 'geometry']
gdf_output = gdf.filter(items=columns_to_keep)

######################################################################
### Preprocessing gdf alvorens wegschrijven
######################################################################
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
### Splits op per assettype
######################################################################
converter = OtlmowConverter()
#converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_.geojson'), list_of_objects=list_OTLAssets)
#converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_.xlsx'), list_of_objects=list_OTLAssets)
converter.create_file_from_assets(filepath=Path('./output/DA-2024-20351.csv'), list_of_objects=list_OTLAssets, split_per_type=True)