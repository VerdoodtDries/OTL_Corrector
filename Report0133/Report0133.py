## Import packages
from pathlib import Path
from otlmow_converter.OtlmowConverter import OtlmowConverter
from otlmow_model.OtlmowModel.Helpers.OTLObjectHelper import print_overview_assets
from otlmow_converter.FileFormats.PandasConverter import PandasConverter
from fuzzywuzzy import fuzz
from HelperFunctions.utils import split_list
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

## Variables
## filename = r"C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\Report0133\Report0133_WestVL_18_44.csv"
filename = r"C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\Report0133\[RSA] Dubbele bomen_20240716.xlsx"
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

## Functions

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
    elif extension == '.csv':
        df_input = pd.read_csv(filepath_or_buffer=filepath, delimiter=';')
except FileNotFoundError as e:
    raise FileNotFoundError(f"The file {filepath} does not exist.") from e

# Launch the API request to obtain data
asset_uuids = df_input['boom1_uuid'].tolist()
asset_uuids = [i[:36] for i in asset_uuids] # Behoud enkel de eerste 36 karakters, hetgeen overeenkomt met de uuid, en niet de volledige AIM-ID

# Launch the API request to obtain data
asset_uuids_bin100 = split_list(asset_uuids)
asset_dicts_dict = {}  # Instantiate an empty dictionary to fill later on
for bin_asset_uuids in asset_uuids_bin100:
    # Bewaar de resultaten per match
    object_generator = eminfra_importer.import_assets_from_webservice_by_uuids(asset_uuids=bin_asset_uuids)
    print(f'Type: {type(object_generator)}\nResponse: {object_generator}')
    asset_dicts_dict |= AssetUpdater.get_dict_from_object_generator(object_generator)  ## |= is the update operator for dictionaries.

# Convert the data to a dataframe. Add the column "sorted_uuids".
# This is the column to detect the duplicate assets (identical trees).
##df = pd.DataFrame.from_dict(data=asset_dicts_dict)
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


# Oplijsten van de attributen waarop een score wordt berekend. Verhoog met 1 als er een waarde beschikbaar is.
lst_attributen_score = ["AIMNaamObject.naam", "VegetatieElement.hoogte", "AIMObject.datumOprichtingObject", "Boom.heeftLuchtleiding", "VegetatieElement.soortnaam", "Boom.boomspiegel", "Boom.eindbeeld"]  # "AIMObject.notitie"
# Bereken de fuzzystring matching score. Dit percentage duidt de gelijkenis tussen twee attributen aan. Controleer of bepaalde attributen ongeveer gelijkaardig zijn.
lst_attributen_fuzzystring =["VegetatieElement.soortnaam"]
# Bereken of bepaalde attributen tegenstrijdige informatie bevatten. Dit zijn kritieke attributen die identieke moeten zijn.
lst_attributen_tegenstrijdig = ["AIMNaamObject.naam"]  # Kritieke attributen waarvoor we detecteren of ze tegenstrijdig zijn.

# Instantiate attributes
gdf['score_nbr_attributes'] = 0  ## Integer
gdf['score_fuzzystringmatch'] = 0.0  ## Float
gdf['score_tegenstrijdige_attr'] = False  ## Boolean

# Outer loop in the dataframe
for i in range(0, len(gdf), 2):
    row1 = gdf.iloc[i]
    row2 = gdf.iloc[i+1]
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
    column_index = gdf.columns.get_loc('score_nbr_attributes')
    gdf.iloc[i, column_index] = score1
    gdf.iloc[i+1, column_index] = score2

    # Loop to calculate the fuzzymatch score. Percentage indicates similarity between values
    for attr_name in lst_attributen_fuzzystring:
        value1 = str(row1[attr_name])
        value2 = str(row2[attr_name])
        partial_ratio = fuzz.partial_ratio(value1, value2)

    column_index = gdf.columns.get_loc('score_fuzzystringmatch')
    gdf.iloc[i, column_index] = partial_ratio
    gdf.iloc[i+1, column_index] = partial_ratio

    # Loop to calculate tegenstrijdige attributen
    for attr_name in lst_attributen_tegenstrijdig:
        value1 = row1[attr_name]
        value2 = row2[attr_name]
        # Controle: de waarden zijn tegenstrijdig
        column_index = gdf.columns.get_loc('score_tegenstrijdige_attr')
        if value1 != value2:
            gdf.iloc[i, column_index] = True
            gdf.iloc[i+1, column_index] = True


print('tot hier')

# Kolom toevoegen: record behouden. Voor iedere combinatie (id_duplicate_asset) eenmaal True en eenmaal False toevoegen.

# Wegschrijven naar een JSON dataframe om objecten te deactiveren.



