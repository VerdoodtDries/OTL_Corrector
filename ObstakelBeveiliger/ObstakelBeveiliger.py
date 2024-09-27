######################################################################
### Import packages
######################################################################
import uuid
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
from shapely.geometry import Point, Polygon, LineString
from shapely import count_coordinates, remove_repeated_points, force_3d
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
### Functions
######################################################################
# Function to convert LineString to Polygon
def linestring_to_polygon(geom):
    if isinstance(geom, LineString):
        coords = list(geom.coords)
        # Ensure the LineString is closed
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        return force_3d(Polygon(coords))  # Convert to Polygon
    return geom

######################################################################
### Print meta_info as the Asset
######################################################################
print('Aanpassing aan de Obstakelbeveiliger:'
      '\n- Sluiten linestring tot een polygoon'
      '\n- Bufferen linestring naar een polygoon - Wijzigen assettype:'
      '\n\t- deactiveren Obstakelbeviliger'
      '\n\t- aanmaken van het juiste assettype.')

obstakelbeveiliger_type_uri = 'https://wegenenverkeer.data.vlaanderen.be/ns/onderdeel#Obstakelbeveiliger'
obstakelbeveiliger = dynamic_create_instance_from_uri(obstakelbeveiliger_type_uri)
print(meta_info(obstakelbeveiliger))


######################################################################
### Define variables
######################################################################
filename = r"C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\ObstakelBeveiliger\[RSA] Geometrie is consistent met GeometrieArtefact_Obstakelbeveiliger_20240906.xlsx"
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

# Convert dictionary to pandas dataframe and transpose rows and columns
df = pd.DataFrame(data=asset_dicts_dict).transpose()
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
# Merge gdf en df_input
columns_to_keep = ['uuid', 'opmerkingen']
df_input = df_input.filter(items=columns_to_keep)
df_input.index = df_input['uuid']

columns_to_keep = ['@type', 'geometry']
gdf = gdf.filter(items=columns_to_keep)

gdf = pd.merge(gdf, df_input, how='left', left_index=True, right_index=True)

# Print de verschillende waardes en aantallen van de kolom 'opmerkingen'.
gdf_opmerkingen_value_counts = gdf['opmerkingen'].value_counts()
print(gdf_opmerkingen_value_counts)


# Rename geodataframe
gdf = gdf.rename(columns={'uuid': 'assetId.identificator', '@type':'typeURI'})
gdf['isActief'] = True  # Set default value True

# Sluit Linestring
gdf_close_linestring = gdf[gdf['opmerkingen'] == 'dries: Obstakelbeveiliger > Sluit Linestring']
gdf_close_linestring['assetId.identificator'] = gdf_close_linestring['assetId.identificator'] + '-b25kZXJkZWVsI09ic3Rha2VsYmV2ZWlsaWdlcg'
gdf_close_linestring.loc[:,'geometry'] = gdf_close_linestring.geometry.apply(linestring_to_polygon)

# Buffer Linestring
gdf_buffer_linestring = gdf[gdf['opmerkingen'] == 'dries: Obstakelbeveiliger > Buffer asset']
gdf_buffer_linestring['assetId.identificator'] = gdf_buffer_linestring['assetId.identificator'] + '-b25kZXJkZWVsI09ic3Rha2VsYmV2ZWlsaWdlcg'
gdf_buffer_linestring.loc[:,'geometry'] = force_3d(gdf_buffer_linestring.geometry.buffer(0.25))

# Deactiveren ObstakelBeveiliger + Aanmaken nieuwe asset GeleideConstructie
##gdf_obstakelbeveiliger_deactiveren1 = gdf[gdf['opmerkingen'] == 'dries: Geleideconsructie >> Wijzig assettype']
##gdf_obstakelbeveiliger_deactiveren1['isActief'] = False

gdf_geleideconstructie = gdf[gdf['opmerkingen'] == 'dries: Geleideconsructie >> Wijzig assettype']
gdf_geleideconstructie.loc[:,'assetId.identificator'] = [str(uuid.uuid4()) for _ in range(len(gdf_geleideconstructie))]  # overwrite
gdf_geleideconstructie.loc[:,'typeURI'] = 'https://wegenenverkeer.data.vlaanderen.be/ns/onderdeel#Geleideconstructie'  # overwrite


# Deactiveren ObstakelBeveiliger + Aanmaken nieuwe asset GetestBeginstuk
##gdf_obstakelbeveiliger_deactiveren2 = gdf[gdf['opmerkingen'] == 'dries: Geteste Beginconstructie > Wijzig assettype']
##gdf_obstakelbeveiliger_deactiveren2['isActief'] = False

gdf_getestebeginconstructie = gdf[gdf['opmerkingen'] == 'dries: Geteste Beginconstructie > Wijzig assettype']
gdf_getestebeginconstructie.loc[:,'assetId.identificator'] = [str(uuid.uuid4()) for _ in range(len(gdf_getestebeginconstructie))]
gdf_getestebeginconstructie.loc[:,'typeURI'] = 'https://wegenenverkeer.data.vlaanderen.be/ns/onderdeel#GetesteBeginconstructie'


######################################################################
### Preprocessing gdf alvorens wegschrijven
######################################################################
# Behoud de essentiële attributen waarvan je info wilt wijzigen bij de aanlevering.
columns_to_keep = ['assetId.identificator', 'typeURI', 'isActief', 'geometry']
gdf_close_linestring = gdf_close_linestring.filter(items=columns_to_keep)
gdf_buffer_linestring = gdf_buffer_linestring.filter(items=columns_to_keep)
gdf_geleideconstructie = gdf_geleideconstructie.filter(items=columns_to_keep)
gdf_getestebeginconstructie = gdf_getestebeginconstructie.filter(items=columns_to_keep)

# Convert geometries to WKT. Na dit punt wordt de geodataframe een normaal dataframe.
gdf_close_linestring['geometry'] = gdf_close_linestring['geometry'].apply(lambda geom: geom.wkt)
gdf_buffer_linestring['geometry'] = gdf_buffer_linestring['geometry'].apply(lambda geom: geom.wkt)
gdf_geleideconstructie['geometry'] = gdf_geleideconstructie['geometry'].apply(lambda geom: geom.wkt)
gdf_getestebeginconstructie['geometry'] = gdf_getestebeginconstructie['geometry'].apply(lambda geom: geom.wkt)


######################################################################
### Converteer gdf naar dictionary
######################################################################
## Convert gdf to list of OTLAssets
list_OTLAssets_ObstakelBeveiligers1 = gdf_to_OTLAssets(gdf_close_linestring)
list_OTLAssets_ObstakelBeveiligers2 = gdf_to_OTLAssets(gdf_buffer_linestring)
list_OTLAssets_GeleideConstructie1 = gdf_to_OTLAssets(gdf_geleideconstructie)
list_OTLAssets_GetesteBeginconstructie1 = gdf_to_OTLAssets(gdf_getestebeginconstructie)


######################################################################
### Schrijf weg naar DAVIE-file
######################################################################
converter = OtlmowConverter()
converter.create_file_from_assets(filepath=Path('DA-2024-23415_Obstakelbeveiligers1.xlsx'), list_of_objects=list_OTLAssets_ObstakelBeveiligers1)
converter.create_file_from_assets(filepath=Path('DA-2024-23415_Obstakelbeveiligers2.xlsx'), list_of_objects=list_OTLAssets_ObstakelBeveiligers2)
converter.create_file_from_assets(filepath=Path('DA-2024-23415_GeleideConstructie1.xlsx'), list_of_objects=list_OTLAssets_GeleideConstructie1)
converter.create_file_from_assets(filepath=Path('DA-2024-23415_GetesteBeginconstructie1.xlsx'), list_of_objects=list_OTLAssets_GetesteBeginconstructie1)