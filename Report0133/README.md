# [Report0133](https://docs.google.com/spreadsheets/d/1rh9WX_zT9KjLPac9B4jg5p5rXKDBRlMIlkJVZKoQWd4/edit?gid=0#gid=0) Dubbele bomen

## Samenvatting
Het doel is om 2 bomen die op nagenoeg dezelfde locatie staan met elkaar te verglijken.
Wat is de afstand tussen de bomen?
Zijn de attributen complemententair/aanvullend of net tegenstrijdig?

## Stappen
- Read the Excel Report listing the incorrect OTL-assets
- Download the data via the API
- Convert the data to a geopandas geodataframe
- Compare the attributes
- *Neem een beslissing voor de juiste boom. Een boom deactiveren, de andere behouden en attributen en relaties overdragen*
- Convert the data into the otlmow-model
- Write to GeoJSON, ready for upload to DAVIE