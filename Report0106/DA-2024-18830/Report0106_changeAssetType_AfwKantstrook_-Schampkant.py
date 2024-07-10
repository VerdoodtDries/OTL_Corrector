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
def calculate_slope(x1, y1, x2, y2):
    """
    Calculate the slope (Richtingscoëfficiënt) of the line passing through the points (x1, y1) and (x2, y2).

    Args:
        x1 (float): x-coordinate of the first point.
        y1 (float): y-coordinate of the first point.
        x2 (float): x-coordinate of the second point.
        y2 (float): y-coordinate of the second point.

    Returns:
        float: The slope of the line.
    """
    try:
        slope = (y2 - y1) / (x2 - x1)
        return slope
    except ZeroDivisionError:
        return float('inf')  # Return infinity if the line is vertical.

def create_linestringz_from_point(point, slope=1, length=1.0):
    """
    Create a LineString from a Point with the specified slope and length.

    Args:
        point: The Point object to create the LineString from.
        slope (float): The slope of the LineString. Default is 1.
        length (float): The length of the LineString. Default is 1.

    Returns:
        LineString: The LineString Z created from the Point with the specified slope and length.
    """
    x, y, z = point.x, point.y, point.z
    if slope == float('inf'):
        point1 = (x, y - length / 2)
        point2 = (x, y + length / 2)
    else:
        dx = length / (2 * (1 + slope**2)**0.5)
        dy = slope * dx
        point1 = (x - dx, y - dy, z)
        point2 = (x + dx, y + dy, z)
    return LineString([point1, point2])





# Read the Excel file in a dataframe
excel_path = r"C:\Users\DriesVerdoodtNordend\OneDrive - Nordend\projects\AWV\python_repositories\OTL_Corrector\Report0106\DA-2024-18830\DA-2024-18819_export.xlsx"
df_KantstrookAfw = pd.read_excel(excel_path, sheet_name='KantstrookAfw', header=0)
print(df_KantstrookAfw)

# Launch the API request to obtain data
asset_uuids = df_KantstrookAfw['assetId.identificator'].tolist()
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

# Add a second geometry column
# Bereken de orientatie van de lijn gevormd door het eerste en laatste punt.
# Vervang de punt geometrie door een lijn, waarbij de lijn de afstand heeft van een Biggenrug. Gebruik als richtingscoëfficiënt de oriëntatie van de lijn.
gdf_first_record = gdf.iloc[0]
gdf_last_record = gdf.iloc[-1]

x1, y1, z1 = gdf_first_record['geometry'].x, gdf_first_record['geometry'].y, gdf_first_record['geometry'].z
x2, y2, z2 = gdf_last_record['geometry'].x, gdf_last_record['geometry'].y, gdf_last_record['geometry'].z

rico = calculate_slope(x1, y1, x2, y2)

# Apply the transformation and create a new geometry column
gdf['new_geometry'] = gdf['geometry'].apply(create_linestringz_from_point, args=(rico,))

# Convert to JSON
# Keep only some columns, rename the columns
columns_to_keep = ['@id', '@type', 'geometry', 'new_geometry']
gdf_output = gdf.filter(items=columns_to_keep).copy()

# Rename multiple columns
gdf_output = gdf_output.rename(columns={'@id': 'assetId.identificator', "@type": 'typeURI'})
# Keeping only the part after the last forward slash and replacing the original column
gdf_output['assetId.identificator'] = gdf_output['assetId.identificator'].str.split('/').str[-1]
# gdf_output = gdf_output.reset_index()
print(gdf_output)

# Copy the geodataframe
gdf_output_KantstrookAfw = gdf_output.copy()
gdf_output_SchampkantStd = gdf_output.copy()

# Aanpassingen gdf_KantstrookAfw
# Drop de overbodige geometry kolom
del gdf_output_KantstrookAfw['new_geometry']
gdf_output_KantstrookAfw['geometry'] = gdf_output_KantstrookAfw['geometry'].apply(lambda geom: geom.wkt) # Convert geometries to WKT
del gdf_output_KantstrookAfw['geometry']
gdf_output_KantstrookAfw['isActief'] = False
gdf_output_KantstrookAfw['notitie'] = 'gedeactiveerd en nieuwe nieuwe asset aangemaakt met assettype SchampkantStd'


# Aanpassingen gdf_output_SchampkantStd
# Verander typeURI van Schampkant
gdf_output_SchampkantStd['typeURI'] = 'https://wegenenverkeer.data.vlaanderen.be/ns/onderdeel#SchampkantStd'
# Convert data type geometry to WKT
del gdf_output_SchampkantStd['geometry'] # First drop the column 'geometry'.
gdf_output_SchampkantStd = gdf_output_SchampkantStd.rename(columns={'new_geometry': 'geometry'}) # Then rename new_geometry to geometry
gdf_output_SchampkantStd['geometry'] = gdf_output_SchampkantStd['geometry'].apply(lambda geom: geom.wkt) # Convert geometries to WKT
# Genereer een nieuwe willekeurige uuid
gdf_output_SchampkantStd['assetId.identificator'] = gdf_output_SchampkantStd['assetId.identificator'].apply(lambda _: uuid.uuid4())
gdf_output_SchampkantStd['toestand'] = 'verwijderd'
gdf_output_SchampkantStd['notitie'] = 'SchampkantStd gebaseerd op KantstrookAfw'
gdf_output_SchampkantStd['type'] = 'varkensrug-of-biggenrug'

## Convert gdf to list of dictionaries
list_of_dict_KantstrookAfw = gdf_output_KantstrookAfw.to_dict(orient='records')
list_of_dict_SchampkantStd = gdf_output_SchampkantStd.to_dict(orient='records')

# Edit the attribute assetId.identificator.
for list_element in list_of_dict_KantstrookAfw:
    list_element['assetId'] = {'identificator': list_element.pop('assetId.identificator')}

for list_element in list_of_dict_SchampkantStd:
    list_element['assetId'] = {'identificator': list_element.pop('assetId.identificator')}

list_OTLAssets_KantstrookAfw = []
list_OTLAssets_SchampkantStd = []

# dict to otlmow model
for asset in list_of_dict_KantstrookAfw:
    OTLAsset = OTLObject.from_dict(asset)
    #OTLAsset.notitie = 'gedeactiveerd en nieuwe nieuwe asset aangemaakt met assettype SchampkantStd'
    list_OTLAssets_KantstrookAfw.append(OTLAsset)

# dict to otlmow model
for asset in list_of_dict_SchampkantStd:
    OTLAsset = OTLObject.from_dict(asset)
    # Voeg nog een extra attribuut toe: toestand
    #OTLAsset.toestand = 'verwijderd'
    # Voeg nog een extra attribuut toe: notitie
    #OTLAsset.notitie = 'SchampkantStd gebaseerd op KantstrookAfw'
    # Voeg nog een extra attribuut toe: "type (Schampkant type)"
    ##print(meta_info(OTLAsset, attribute='type'))
    #OTLAsset.type = 'varkensrug-of-biggenrug'
    list_OTLAssets_SchampkantStd.append(OTLAsset)

converter = OtlmowConverter()
converter.create_file_from_assets(filepath=Path('DA-2024-18830_KantstrookAfw.geojson'), list_of_objects=list_OTLAssets_KantstrookAfw)
converter.create_file_from_assets(filepath=Path('DA-2024-18830_SchampkantStd.geojson'), list_of_objects=list_OTLAssets_SchampkantStd)