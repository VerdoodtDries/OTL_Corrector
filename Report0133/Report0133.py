## Import packages
from pathlib import Path
from otlmow_converter.OtlmowConverter import OtlmowConverter
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
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('TkAgg')
import contextily as ctx
from matplotlib.ticker import ScalarFormatter


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


# Read the Excel file in a dataframe
excel_path = r"C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\Report0133\RSA_Report0133_afstand1meter_Vlaanderen.xlsx"
df_report0133 = pd.read_excel(excel_path, sheet_name='RSA_Report0133_afstand1meter_Vl', header=0)
print(df_report0133)

# Launch the API request to obtain data
typeURI = 'https://wegenenverkeer.data.vlaanderen.be/ns/onderdeel#Boom'
boom1_uuid = df_report0133['boom1_uuid'].tolist()
boom2_uuid = df_report0133['boom2_uuid'].tolist()
print(f'typeURI: {typeURI}')
print(f'boom1 uuid: {boom1_uuid}')
print(f'boom2 uuid: {boom2_uuid}')

# Development: Sample de eerste boom
# Sample the first element of the list
boom1_uuid_sample = [boom1_uuid[0]]
boom2_uuid_sample = [boom2_uuid[0]]
print(f'Sample boom1 uuid: {boom1_uuid_sample}')
print(f'Sample boom2 uuid: {boom2_uuid_sample}')


object_generator = eminfra_importer.import_assets_from_webservice_by_uuids(asset_uuids=boom1_uuid_sample)
print(f'Type: {type(object_generator)}\nResponse: {object_generator}')

#asset_dicts_dict = AssetUpdater.get_dict_from_object_generator(object_generator)
asset_dicts_dict = AssetUpdater.get_dict_from_object_generator(object_generator)


# Convert the data to a dataframe
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


# Visualise the gdf in a small map
## to do
# Convert to Web Mercator (EPSG:3857) for compatibility with contextily
gdf_wm = gdf.to_crs(epsg=3857) # Geodataframe Webmercator

# Plot the GeoDataFrame
fig, ax = plt.subplots(figsize=(10, 10))

gdf_wm.plot(ax=ax, color='green', legend=True)

# Disable scientific notation and use plain style
formatter = ScalarFormatter(useOffset=False, useMathText=True)
formatter.set_scientific(False)

# Optionally, set the number of ticks to show a better representation of full numbers
ax.xaxis.set_major_formatter(formatter)
ax.yaxis.set_major_formatter(formatter)

# Crop the figure
minx, miny, maxx, maxy = gdf_wm.buffer(distance=100).total_bounds # 100 meter buffer rondom het gdf om de bounding extent te bepalen
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)

# Add the OpenStreetMap basemap
ctx.add_basemap(ax=ax, source=ctx.providers.OpenStreetMap.Mapnik)

# Save the plot as a PNG image
plt.title('Dubbele bomen')
plt.savefig("Report0133.png", dpi=300)

# tot hier
# Add the second tree
# Add an appropriate title (both uuids) and a legend.

# Convert to JSON