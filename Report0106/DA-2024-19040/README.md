# Report0106

## Summary
Wijzig het assettype van OpgaandeHoutigeVegetatie naar Boom.
Het is niet toegestaan om voor een bestaand asset, diens assettype te wijzigen.
Men dient dus de huidige asset te deactiveren en een nieuwe asset aan te maken, met dezelfde eigenschappen waar mogelijk.

- Read the Excel Report listing the incorrect OTL-assets
- Download the data via the API
- Convert the data to a geopandas geodataframe
- Convert the data into the otlmow-model (correct OTL-class)
- Write to GeoJSON, ready for upload to DAVIE