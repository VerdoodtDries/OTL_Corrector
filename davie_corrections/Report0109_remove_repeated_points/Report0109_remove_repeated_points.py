# Excel kan niet als otlmow-model worden ingelezen, omdat de geometrie definitie (multipolygon) foutief is.
# Eerst wordt de data als pandas dataframe ingelezen
# Vervolgens wordt de geometrie geschrapt/aangepast
# Tot slot wordt het pandas dataframe omgevormd naar het otlmow-model.

from pathlib import Path
from otlmow_converter.OtlmowConverter import OtlmowConverter
from otlmow_model.OtlmowModel.Helpers.OTLObjectHelper import print_overview_assets
from otlmow_converter.FileFormats.PandasConverter import PandasConverter
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon

## Functions
def check_points_within_polygons(gdf_points, gdf_polygons):
    gdf_points['within'] = gdf_points.apply(
        lambda row: any(gdf_polygons.contains(row['geometry'])), axis=1)
    return gdf_points


# Read the Excel-file as pandas dataframe
df_bevestiging = pd.read_excel('DA-2024-17015_export.xlsx', sheet_name='Bevestiging')
df_figuratie_markering = pd.read_excel('DA-2024-17015_export.xlsx', sheet_name='FiguratieMarkering')

# Filter the active records.
df_figuratie_markering_isActief = df_figuratie_markering[df_figuratie_markering['isActief'] == True]
df_bevestiging_isActief = df_bevestiging[df_bevestiging['isActief'] == True]

# Zoek alle assets met geometrie type: Punt
df_figuratie_markering_isActief_punt = df_figuratie_markering_isActief[df_figuratie_markering_isActief['geometry'].str.contains('^POINT.*', regex=True)]
# Zoek alle assets met geometrie type: Polygoon
df_figuratie_markering_isActief_polygon = df_figuratie_markering_isActief[df_figuratie_markering_isActief['geometry'].str.contains('POLYGON.*', regex=True)]
print(df_figuratie_markering_isActief_punt)
print(df_figuratie_markering_isActief_polygon)

# Controleer of er een punt is op de locaties van de polygonen.
# Even on-hold, eventueel manueel controleren voor de 25 assets.
# Convert Dataframe to a GeoDataFrame
gs_point = gpd.GeoSeries.from_wkt(df_figuratie_markering_isActief_punt['geometry'])
gs_polygon = gpd.GeoSeries.from_wkt(df_figuratie_markering_isActief_polygon['geometry'])

gdf_point = gpd.GeoDataFrame(data=df_figuratie_markering_isActief_punt, geometry=gs_point, crs="EPSG:31370")
gdf_polygon = gpd.GeoDataFrame(data=df_figuratie_markering_isActief_polygon, geometry=gs_polygon, crs="EPSG:31370")

gdf_points = check_points_within_polygons(gdf_point, gdf_polygon)
# Function to check if points in gdf_point are within any polygon in gdf_polygon


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















