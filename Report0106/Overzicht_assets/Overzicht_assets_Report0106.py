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


######################################################################
### Define variables
######################################################################
filename = r"C:\Users\DriesVerdoodtNordend\Downloads\[RSA] Geometrie is consistent met GeometrieArtefact_20240801.xlsx"
feature_type = 'Resultaat'  # This is the layer name or the Excel sheet name

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


######################################################################
### Group-by geometry-type and assettype
######################################################################
# Split input dataframe op in een gedeelte mét en een gedeelte zonder geometrie
df_input_geometrie_na = df_input[df_input['wkt_string'].isna()]
df_input_geometrie = df_input[df_input['wkt_string'].notna()]

df_input_geometrie_grouped = df_input_geometrie.groupby(by="naam", dropna=False).size().reset_index(name='count')
df_input_geometrie_na_grouped = df_input_geometrie_na.groupby(by="naam", dropna=False).size().reset_index(name='count')

######################################################################
### Write dataframe to CSV
######################################################################
# Delimiter ;
df_input_geometrie_grouped.to_csv('GeometrieArtefact_samenvatting.csv', sep=';', index=False)
df_input_geometrie_na_grouped.to_csv('GeometrieArtefact_na_samenvatting.csv', sep=';', index=False)