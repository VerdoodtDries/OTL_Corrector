import geopandas as gpd
from shapely import LineString, Polygon

# Verbeter het asset. Vb. Verwijder dubbele opeenvolgende punten
# https://geopandas.org/en/latest/docs/reference/api/geopandas.GeoSeries.remove_repeated_points.html
# Test Geopandas function remove_repeated_points()
s = gpd.GeoSeries([
       LineString([(0, 0), (0, 0), (1, 0)]),
       Polygon([(0, 0), (0, 0.5), (0, 1), (0.5, 1), (0,0)]),
    ],)
print(s)

s = s.remove_repeated_points(tolerance=0.0)
print(s)


