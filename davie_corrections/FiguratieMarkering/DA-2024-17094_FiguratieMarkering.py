import os.path
from pathlib import Path
from otlmow_model.OtlmowModel.BaseClasses.OTLObject import dynamic_create_instance_from_uri
from otlmow_converter.OtlmowConverter import OtlmowConverter
from otlmow_model.OtlmowModel.Helpers.OTLObjectHelper import print_overview_assets
from otlmow_converter.FileFormats.PandasConverter import PandasConverter

from otlmow_converter.FileImporter import FileImporter
from otlmow_model.OtlmowModel.BaseClasses.MetaInfo import meta_info
import pandas as pd

# Excel kan niet als otlmow-model worden ingelezen, omdat de geometrie definitie (multipolygon) foutief is.
# Eerst wordt de data als pandas dataframe ingelezen
# Vervolgens wordt de geometrie geschrapt/aangepast
# Tot slot wordt het pandas dataframe omgevormd naar het otlmow-model.


# Read the Excel-file as pandas dataframe
# Read the Excel file with two tabs into separate DataFrames
df_bevestiging = pd.read_excel('DA-2024-17015_export.xlsx', sheet_name='Bevestiging')
df_figuratie_markering = pd.read_excel('DA-2024-17015_export.xlsx', sheet_name='FiguratieMarkering')

# Display the first few rows of each DataFrame for verification
print("Bevestiging DataFrame:")
print(df_bevestiging.head())

print("FiguratieMarkering DataFrame:")
print(df_figuratie_markering.head())

# Filter the active records.
df_figuratie_markering_isActief = df_figuratie_markering[df_figuratie_markering['isActief'] == True]
df_bevestiging_isActief = df_bevestiging[df_bevestiging['isActief'] == True]

print("Bevestiging DataFrame, filtered for active records:")
print(df_bevestiging_isActief.head())

print("FiguratieMarkering DataFrame, filtered for active records:")
print(df_figuratie_markering_isActief.head())

# Zoek alle assets met geometrie type: Punt
df_figuratie_markering_isActief_punt = df_figuratie_markering_isActief[df_figuratie_markering_isActief['geometry'].str.contains('^POINT.*', regex=True)]
print(df_figuratie_markering_isActief_punt)

# Zoek alle assets met geometrie type: Polygoon
df_figuratie_markering_isActief_polygon = df_figuratie_markering_isActief[df_figuratie_markering_isActief['geometry'].str.contains('POLYGON.*', regex=True)]
print(df_figuratie_markering_isActief_polygon)

# Controleer of er een punt is op de locaties van de polygonen.
# Even on-hold, eventueel manueel controleren voor de 25 assets.

# Wijzig attribuutwaarde isActief naar False en schrijf data weg naar GeoJSON
df_figuratie_markering_isActief_polygon['isActief'] = False

# Schrap kolom geometrie, gebruik methode pop() om deze apart te behouden
geometrie_multipolygonen = df_figuratie_markering_isActief_polygon.pop('geometry')
# Schrap alle overtollige kolommen: toestand
df_figuratie_markering_isActief_polygon = df_figuratie_markering_isActief_polygon.drop('toestand', axis=1)

print(f'Geometrie multipolygonen: {geometrie_multipolygonen}')
print(f'df_figuratie_markering_isActief_polygon: {df_figuratie_markering_isActief_polygon}')


# Convert the pd dataframe to the OTL-model
otlmow_converter = OtlmowConverter()
pandas_converter = PandasConverter(settings=otlmow_converter.settings)
otl_assets = pandas_converter.convert_dataframe_to_objects(dataframe=df_figuratie_markering_isActief_polygon)
print(f'otl_assets:\n{otl_assets}')
print_overview_assets(otl_assets)

# Convert (write) to GeoJSON
otlmow_converter.create_file_from_assets(filepath=Path('FiguratieMarkering.geojson'), list_of_objects=otl_assets)















