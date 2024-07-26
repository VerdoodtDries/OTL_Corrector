import os
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import contextily as ctx
import geopandas as gpd
from otlmow_model.OtlmowModel.BaseClasses.OTLObject import OTLObject

def get_wkt_length(geometry):
    """
    Returns the length of the Well-Known Text (WKT) representation of a geometry object.

    Args:
        geometry: A geometry object.

    Returns:
        int: The length of the WKT representation of the geometry object.
    """
    return len(geometry.wkt)

def gdf_to_OTLAssets(gdf):
    """
    Converts a geodataframe to a list of OTLObject objects representing assets.

    Args:
        gdf: A geopandas geodataframe containing asset data.

    Returns:
        list: A list of OTLObject objects representing assets after conversion.

    Raises:
        KeyError: If the 'assetId.identificator' key is missing in the geodataframe.

    Examples:
        gdf = geopandas.GeoDataFrame(...)
        list_OTLAssets = gdf_to_OTLAssets(gdf)
    """

    # Convert geodataframe to a dictionary
    list_of_dict = gdf.to_dict(orient='records')

    # Edit the attribute assetId.identificator.
    for list_element in list_of_dict:
        list_element['assetId'] = {'identificator': list_element['assetId.identificator']}
        del list_element['assetId.identificator'] # verwijder dit dictionary element

    # Transform the dictionary to the OTLObject object. This has a built-in validation.
    list_OTLAssets = []
    # dict to otlmow model
    for asset in list_of_dict:
        ##print(f'Asset: {asset}')
        OTLAsset = OTLObject.from_dict(asset)
        ##print(f'OTL-asset: {OTLAsset}')
        list_OTLAssets.append(OTLAsset)

    return list_OTLAssets


def split_list(input_list, max_elements=100):
    """
    Splits a list into multiple lists of a specified maximum number of elements.

    Parameters:
    input_list (list): The list to be split.
    max_elements (int): The maximum number of elements per sublist.

    Returns:
    list of lists: A list containing the sublists.
    """
    # Use list comprehension to create the sublists
    return [input_list[i:i + max_elements] for i in range(0, len(input_list), max_elements)]


def plot_gdf(gdf, filename, fanout=False, color='red', figsize=(10, 10), dpi=100):
    """
    Plot each individual record of a GeoDataFrame and save as PNG images.

    :param gdf: Geodataframe. If crs is missing, coordinates are projected to Belgian Lambert72 (EPSG:31370).
    :param filename: Output filename
    :param fanout: create a map for each geopandas record
    :param color: color of the marker
    :param figsize: figure size tuple (width, height)
    :param dpi: Dots per square inch
    :return:
    """
    # Set CRS to Lambert72 if missing
    if gdf.crs is None:
        gdf.set_crs("EPSG:31370", inplace=True)

    # Convert to Web Mercator (EPSG:3857) for compatibility with contextily
    gdf_web_mercator = gdf.to_crs(crs="EPSG:3857")

    output_dir = 'plots'
    os.makedirs(output_dir, exist_ok=True)

    # Helper function is only available inside the context of the actual function
    def plot_record(record, output_path):
        fig, ax = plt.subplots(figsize=figsize)
        record.plot(ax=ax, color=color, legend=True)

        # Disable scientific notation and use plain style
        formatter = ScalarFormatter(useOffset=False, useMathText=True)
        formatter.set_scientific(False)
        ax.xaxis.set_major_formatter(formatter)
        ax.yaxis.set_major_formatter(formatter)

        # Crop the figure
        minx, miny, maxx, maxy = record.buffer(distance=100).total_bounds
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)

        # Add the OpenStreetMap basemap
        ctx.add_basemap(ax=ax, source=ctx.providers.OpenStreetMap.Mapnik)

        # Save the plot as a PNG image
        plt.savefig(output_path, dpi=dpi)
        plt.close()

    if fanout:
        # Create a map for each individual record
        for index, row in gdf_web_mercator.iterrows():
            output_path = os.path.join(output_dir, f"{filename}_{index}.png")
            plot_record(gdf_web_mercator.loc[[index]], output_path)
    else:
        # Plot all records on one map
        output_path = os.path.join(output_dir, f"{filename}.png")
        plot_record(gdf_web_mercator, output_path)
