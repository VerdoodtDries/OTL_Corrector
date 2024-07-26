/* postgres
-- Date: Jul 26, 2024
-- Time: 10:19:09 AM
-- Author: Dries Verdoodt
-- Objective: Detecteer alle assets waarbij de lengte van de WKT string langer is dan 32,767 karakters
-- Oplijsten: uuid, assettype, aantal karakters
*/
with cte_geometrie as (
	-- aantal: 292
	select
		g.assetuuid
		, char_length(g.wkt_string) as lengte_wkt_string
		, 'OTL' as "databron"
	from geometrie g 
	where char_length(g.wkt_string) >= 32767
), cte_locatie as (
	-- aantal: 226
	select
		l.assetuuid
		, char_length(l.geometrie) as lengte_wkt_string
		, 'LGC' as "databron"
	from locatie l
	where char_length(l.geometrie) >= 32767
)
-- Mergen van LGC en OTL tabellen
, cte_lgc_otl_geometrie as (
	select
		assetuuid
		, min(lengte_wkt_string) as lengte_wkt_string
		, string_agg(databron, '; ') as databron
	from (
		select * from cte_geometrie g
		union
		select * from cte_locatie l
	)
	group by assetuuid
	order by assetuuid
)
--select * from cte_lgc_otl_geometrie
-- main query
select
	a."uuid" 
	, at.uri
	, g.lengte_wkt_string
	, g.databron
from assets a
inner join cte_lgc_otl_geometrie g on a.uuid = g.assetuuid
left join assettypes at on a.assettype = at."uuid" 
order by at.uri