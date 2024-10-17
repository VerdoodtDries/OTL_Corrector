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
from HelperFunctions.utils import split_list, plot_gdf, gdf_to_OTLAssets
import json
import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.geometry import Point, Polygon
from shapely import count_coordinates, remove_repeated_points
import logging
import xlsxwriter
from EMInfraImporter import EMInfraImporter
from RequestHandler import RequestHandler
from RequesterFactory import RequesterFactory
from SettingsManager import SettingsManager
from AssetUpdater import AssetUpdater
import geopandas as gpd
import matplotlib
from openpyxl import load_workbook
import matplotlib.pyplot as plt
matplotlib.use('TkAgg')
import contextily as ctx
from matplotlib.ticker import ScalarFormatter
import os


######################################################################
### Define variables
######################################################################
dir = r'C:\Users\DriesVerdoodtNordend\Downloads'
filename = '[RSA] EAN-opzoeklijst_20241016.xlsx'
filepath = os.path.join(dir, filename)

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

# Install a filter on the dataframe
# Filter waar zowel asset1 en asset2 zijn ingevuld
df_input = df_input[df_input['priority'] == 2]

# Convert the datatype of the EAN-numbers from numeric to string. This will prevent rounding errors when writing to Excel.
df_input['asset1_ean'] = df_input['asset1_ean'].apply(lambda x: str(int(x)))
df_input['asset2_ean'] = df_input['asset2_ean'].apply(lambda x: str(int(x)))

# Check dat beide attributen identiek zijn: asset1_ean = asset2_ean
df_input_fouten = df_input[df_input['asset1_ean'] != df_input['asset2_ean']]
df_input = df_input[df_input['asset1_ean'] == df_input['asset2_ean']]

# Bij wijze van backup: schrijf alle fouten naar een Excel-sheet, schijf de LGC-uuid's en hun bijhorende EAN-nummer naar een Excel-sheet.
# Specify the Excel writer and use 'xlsxwriter' engine
with pd.ExcelWriter('EAN_opzoeklijst.xlsx', engine='xlsxwriter') as writer:
    df_input_fouten.to_excel(writer, sheet_name='Fouten', index=False)
    df_input.to_excel(writer, sheet_name='Ontkoppelen_EAN', index=False)

    # Access the workbook and worksheet objects
    workbook = writer.book
    worksheet_fouten = writer.sheets['Fouten']
    worksheet_ontkoppelen = writer.sheets['Ontkoppelen_EAN']

    # Define the format as text to prevent rounding and scientific notation
    text_format = workbook.add_format({'num_format': '@'})  # Text format
    int_format = workbook.add_format({'num_format': '0'})  # Integer format

    # Apply the format to the specific column
    worksheet_fouten.set_column('S:S', None, text_format)
    worksheet_fouten.set_column('T:T', None, text_format)
    worksheet_ontkoppelen.set_column('S:S', None, text_format)
    worksheet_ontkoppelen.set_column('T:T', None, text_format)



# Converteer de uuids naar een lijst
uuid_lgc = df_input['asset2_uuid'].to_list()


# Lanceer de API request om de elektrische aansluiting te ontkoppelen.
for uuid in uuid_lgc:  # Verander dit stuk nog om te loopen over alle LGC-assets.
    url = f'core/api/assets/{uuid}/kenmerken/87dff279-4162-4031-ba30-fb7ffd9c014b'
    requester.put(url=url, data='{}')

