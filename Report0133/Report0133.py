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

boom_type_uri = 'https://wegenenverkeer.data.vlaanderen.be/ns/onderdeel#Boom'
boom = dynamic_create_instance_from_uri(boom_type_uri)

######################################################################
### Define variables
######################################################################
filename = r"C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\Report0133\[RSA] Dubbele bomen_20240716.xlsx"
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
asset_uuids = df_input['boom1_uuid'].tolist()
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
### Bereken het aantal waardes dat voorkomt bij attributen
### Bereken de fuzzystring gelijkenis van attributen
### Bereken of attributen tegenstrijdig zijn
######################################################################
# Oplijsten van de attributen waarop een score wordt berekend. Verhoog met 1 als er een waarde beschikbaar is.
# Beter zou zijn: alle attributen wiens naam start met AIM; Boom; VegetatieElement
lst_attributen_score = ["AIMNaamObject.naam", "VegetatieElement.hoogte", "AIMObject.datumOprichtingObject",
                        "Boom.heeftLuchtleiding", "VegetatieElement.soortnaam", "Boom.boomspiegel",
                        "Boom.eindbeeld"]  # "AIMObject.notitie"
# Bereken de fuzzystring matching score. Dit percentage duidt de gelijkenis tussen twee attributen aan. Controleer of bepaalde attributen ongeveer gelijkaardig zijn.
lst_attributen_fuzzystring = ["VegetatieElement.soortnaam"]
# Bereken of bepaalde attributen tegenstrijdige informatie bevatten. Dit zijn kritieke attributen die identieke moeten zijn.
lst_attributen_tegenstrijdig = ["AIMNaamObject.naam"]  # Kritieke attributen waarvoor we detecteren of ze tegenstrijdig zijn.


# Instantiate attributes
gdf['score_number_attributes'] = 0  ## Integer
gdf['score_fuzzystringmatch'] = 0.0  ## Float
gdf['score_conflicting_attributes'] = False  ## Boolean


# Outer loop in the dataframe
for i in range(0, len(gdf), 2):
    row1 = gdf.iloc[i]
    row2 = gdf.iloc[i + 1]
    row1 = row1.fillna(value='')
    row2 = row2.fillna(value='')

    # Inner loop to calculate scores
    # Loop to calculate the score. Score indicates the number of attributes that have a value
    score1 = 0
    score2 = 0
    for attr_name in lst_attributen_score:
        if row1[attr_name] and row1[attr_name] != '':  # Has a value
            score1 += 1
        if row2[attr_name] and row2[attr_name] != '':  # Has a value
            score2 += 1
    column_index = gdf.columns.get_loc('score_number_attributes')
    gdf.iloc[i, column_index] = score1
    gdf.iloc[i + 1, column_index] = score2

    # Loop to calculate the fuzzymatch score. Percentage indicates similarity between values
    for attr_name in lst_attributen_fuzzystring:
        value1 = str(row1[attr_name])
        value2 = str(row2[attr_name])
        partial_ratio = fuzz.partial_ratio(value1, value2)

    column_index = gdf.columns.get_loc('score_fuzzystringmatch')
    gdf.iloc[i, column_index] = partial_ratio
    gdf.iloc[i + 1, column_index] = partial_ratio

    # Loop to calculate tegenstrijdige attributen
    for attr_name in lst_attributen_tegenstrijdig:
        value1 = row1[attr_name]
        value2 = row2[attr_name]
        # Controle: de waarden zijn tegenstrijdig
        column_index = gdf.columns.get_loc('score_conflicting_attributes')
        if value1 != value2:
            gdf.iloc[i, column_index] = True
            gdf.iloc[i + 1, column_index] = True

######################################################################
### Filter data op basis van:
###     Fuzzystringmatch
###     tegenstrijdige attributen
###     absoluut aantal voorkomen van een bepaalde set van attributen
######################################################################
# Filter het dataframe.
# Maak een dataframe voor manuele inspectie: gdf_output_inspectie
# Selecteer alle records waarbij score_fuzzystringmatch < 0.75 (bepaalde threshold)
gdf_output_fuzzystringmatch = gdf[gdf['score_fuzzystringmatch'] < 70.0].copy()

# Selecteer alle records waarbij score_conflicting_attributes = True
gdf_output_conflictingAttributes = gdf[gdf['score_conflicting_attributes'] == True].copy()

# Maak een dataframe voor DAVIE: gdf_output
min_values = gdf.groupby('id_duplicate_asset')['score_number_attributes'].transform('min')
# Create a boolean mask for the rows where 'value' is equal to the minimum value in the group
boolean_mask = gdf['score_number_attributes'] == min_values
# Optionally, use the boolean mask to filter the DataFrame
gdf_output = gdf[boolean_mask]


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
### Splits per provincie
######################################################################
gdf_output_WVL = gdf_output[gdf_output['PROVINCIE'] == 'West-Vlaanderen']
gdf_output_OVL = gdf_output[gdf_output['PROVINCIE'] == 'Oost-Vlaanderen']
gdf_output_ANT = gdf_output[gdf_output['PROVINCIE'] == 'Antwerpen']
gdf_output_VLB = gdf_output[gdf_output['PROVINCIE'] == 'Vlaams-Brabant']
gdf_output_LIM = gdf_output[gdf_output['PROVINCIE'] == 'Limburg']

######################################################################
### Converteer gdf naar dictionary
######################################################################
## Convert gdf to list of OTLAssets
list_OTLAssets = gdf_to_OTLAssets(gdf_output)
list_OTLAssets_WVL = gdf_to_OTLAssets(gdf_output_WVL)
list_OTLAssets_OVL = gdf_to_OTLAssets(gdf_output_OVL)
list_OTLAssets_ANT = gdf_to_OTLAssets(gdf_output_ANT)
list_OTLAssets_VLB = gdf_to_OTLAssets(gdf_output_VLB)
list_OTLAssets_LIM = gdf_to_OTLAssets(gdf_output_LIM)

######################################################################
### Schrijf weg naar DAVIE-file
######################################################################
# Volledige export van alle bomen verwerken en wegschrijven naar JSON/Excel files.
# GEOJSON formaat is ongeldig DAVIE formaat. Zie: https://github.com/davidvlaminck/OTLMOW-Converter/issues/21
converter = OtlmowConverter()
if list_OTLAssets_WVL:
    converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_West-Vlaanderen.geojson'), list_of_objects=list_OTLAssets_WVL)
    converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_West-Vlaanderen.xlsx'), list_of_objects=list_OTLAssets_WVL)

if list_OTLAssets_OVL:
    converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_Oost-Vlaanderen.geojson'), list_of_objects=list_OTLAssets_OVL)
    converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_Oost-Vlaanderen.xlsx'), list_of_objects=list_OTLAssets_OVL)

if list_OTLAssets_ANT:
    converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_Antwerpen.geojson'), list_of_objects=list_OTLAssets_ANT)
    converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_Antwerpen.xlsx'), list_of_objects=list_OTLAssets_ANT)

if list_OTLAssets_VLB:
    converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_Vlaams-Brabant.geojson'), list_of_objects=list_OTLAssets_VLB)
    converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_Vlaams-Brabant.xlsx'), list_of_objects=list_OTLAssets_VLB)

if list_OTLAssets_LIM:
    converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_Limburg.geojson'), list_of_objects=list_OTLAssets_LIM)
    converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_Limburg.xlsx'), list_of_objects=list_OTLAssets_LIM)

######################################################################
### Schrijf weg naar DAVIE-file ter visuele inspectie van de resultaten
######################################################################
gdf_inspection = gdf.copy()
# Maak een dataframe voor DAVIE: gdf_output
min_values = gdf_inspection.groupby('id_duplicate_asset')['score_number_attributes'].transform('min')
# Create a boolean mask for the rows where 'value' is equal to the minimum value in the group
# Use the boolean mask to set the attribute 'AIMDBStatus.isActief'
gdf_inspection.loc[gdf['score_number_attributes'] == min_values, 'AIMDBStatus.isActief'] = False

# Preprocessing alvorens weg te schrijven
# Behoud sommige attributen
columns_to_keep = [
    '@type'
    , '@id'
    , 'AIMObject.notitie'
    , 'AIMObject.datumOprichtingObject'
    , 'AIMDBStatus.isActief'
    , 'AIMNaamObject.naam'
    , 'VegetatieElement.soortnaam'
    , 'Boom.boomspiegel'
    , 'VegetatieElement.hoogte'
    , 'AIMToestand.toestand'
    , 'AIMObject.typeURI'
    , 'Boom.heeftLuchtleiding'
    , 'AIMObject.assetId'
    , 'Boom.eindbeeld'
    , 'PROVINCIE'
    , 'geometry'
    , 'id_duplicate_asset'
    , 'score_number_attributes'
    , 'score_fuzzystringmatch'
    , 'score_conflicting_attributes'
]
gdf_inspection = gdf_inspection.filter(items=columns_to_keep)
## print(f'Geodataframe to export: {gdf_output}')

# Rename columns
gdf_inspection = gdf_inspection.rename(
    columns={
        '@id': 'assetId.identificator'
        , "@type": 'typeURI'
        , 'AIMDBStatus.isActief': 'isActief'
        , 'AIMObject.notitie': 'notitie'
        , 'AIMObject.datumOprichtingObject': 'datumOprichtingObject'
        , 'AIMNaamObject.naam': 'naam'
        , 'VegetatieElement.soortnaam': 'soortnaam'
        , 'Boom.boomspiegel': 'boomspiegel'
        , 'VegetatieElement.hoogte': 'hoogte'
        , 'AIMToestand.toestand': 'toestand'
        , 'Boom.heeftLuchtleiding': 'heeftLuchtleiding'
        , 'Boom.eindbeeld': 'eindbeeld'
    })
# Keeping only the part after the last forward slash and replacing the original column
gdf_inspection['assetId.identificator'] = gdf_inspection['assetId.identificator'].str.split('/').str[-1]

# Convert geometries to WKT. Na dit punt wordt de geodataframe een normaal dataframe.
gdf_inspection['geometry'] = gdf_inspection['geometry'].apply(lambda geom: geom.wkt)

# Write to Excel
gdf_inspection.to_excel('DA-2024-xxxxx_Boom_dubbels_niet_davie_conform.xlsx', index=False, engine='openpyxl')

# Om alle attributen weg te schrijven naar een DAVIE-conform bestand, dient nog wat post-processing te gebeuren aan de attributen.
# Columns to replace NaN with an empty string
#string_columns = ['eindbeeld']
# Columns to replace NaN with an empty list
#list_columns = ['boomspiegel']
# Replace NaN values with an empty string in specific columns
#gdf_inspection[string_columns] = gdf_inspection[string_columns].fillna('')
# Replace NaN values with an empty list in specific columns
#gdf_inspection[list_columns] = gdf_inspection[list_columns].map(lambda x: [] if pd.isna(x) else x)

## Convert gdf to list of OTLAssets
#list_OTLAssets = gdf_to_OTLAssets(gdf_inspection)

#converter.create_file_from_assets(filepath=Path('DA-2024-xxxxx_Boom-dubbels.xlsx'), list_of_objects=list_OTLAssets)