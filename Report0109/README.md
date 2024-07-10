# Report0109 remove repeated points

## Summary
The purpose is to remove repeated points that are detected in the Report0109.

- Read the Excel Report listing the incorrect OTL-assets
- Download the data via the API
- Convert the data to a geopandas geodataframe
- Apply the function [remove_repeated_points](https://geopandas.org/en/stable/docs/user_guide/geometric_manipulations.html#GeoSeries.remove_repeated_points)
- Convert the data into the otlmow-model
- Write to GeoJSON, ready for upload to DAVIE