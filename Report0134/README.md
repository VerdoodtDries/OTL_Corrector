# [Report0134](https://docs.google.com/spreadsheets/d/1sBbUS5sMO1gwDwvy7-I-V3BcZHzR_aMI3nDHoiQY7Sk/edit?gid=1679953537#gid=1679953537) Dubbele Straatkolken

## Samenvatting
Opschonen van dubbele Straatkolken, namelijk straatkolken die zich binnen **X** meter afstand van elkaar bevinden.

## Stappen
- Read the Excel Report listing the incorrect OTL-assets
- Download the data via the API
- Convert the data to a geopandas geodataframe
- Deactivate the assets without Z-value, or Z-value = 0.
- Convert the data into the otlmow-model
- Write to Excel, ready for upload to DAVIE