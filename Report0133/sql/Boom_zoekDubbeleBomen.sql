/*
 * Alle bomen, met aanduiding van ident2, ident8, provincie en de dubbele bomen binnen een afstand van X meter 
 * */

/*
select
boom1_ident8, count(boom1_ident8)
from (
*/
with
cte_boom AS (
	SELECT
		a.uuid
		, a.toestand
		, a.actief
		, a.naam
		-- Convert JSON5 to JSON
		, replace(
			replace(
				replace(
					replace(
						replace(
							replace(
				    			replace(
				    				replace(
				    					REPLACE(
				        					w.waarde
				        					-- dubbel weglatingsteken door enkel aanhalingsteken
				            				, '"'
				            				, '''')
			            				-- enkel weglatingsteken dubbelpunt spatie enkel weglatingsteken
										, ''': '''
										, '": "')
									-- enkel weglatingsteken komma spatie enkel weglatingsteken
									, ''', '''
									, '", "')
								-- sluit curly bracket enkel weglatingsteken
			            		, '}'''
								, '}"')
							-- open curly bracket enkel weglatingsteken
		            		, '{'''
		            		, '{"')
	            		-- enkel weglatingsteken sluit curly-bracket
						, '''}'
						, '"}')
					-- enkel weglatingsteken open curly-bracket
					, '''{'
					, '"{')
				-- twee opeenvolgend dubbel weglatingsteken
				, '""'
				, '"')
			-- twee opeenvolgend dubbel weglatingsteken (nogmaals)
			, '""'
			, '"')::json
			as soortnaam
		, g.wkt_string
		, l.ident2
		, l.ident8
		-- Vervang door geom-kolom zodra beschikbaar
		, g.geom
	FROM assets a
	LEFT JOIN geometrie g ON a.uuid = g.assetuuid
	left join locatie l on a.uuid = l.assetuuid
	left join attribuutwaarden w on a.uuid = w.assetuuid
	where
		a.assettype = 'cd77f043-dc69-46ae-98a1-da8443ca26bf' -- Boom
		and
		a.actief = true
		and
		a.toestand = 'in-gebruik'
		and
		w.attribuutuuid = '27803bbe-ddf0-46c8-8107-130df29de615' -- soortnaam
	--limit 100
),
-- Voeg de informatie van de provincie en de gemeente toe aan iedere boom, m.a.w. binnen welke gridcell is de boom gelegen.
-- Dit dient om de spatial query te versnellen.
cte_boom_index as (
	-- Voeg de gridcell toe aan iedere boom
	select
		boom.*
		, gem.provincie as prv_naam
		, gem.niscode as gem_niscode
		, gem.gemeente as gem_naam
	from cte_boom boom
	-- Join op fictieve tabel zonder spatial index
	--inner join cte_provincies prv on st_intersects(boom.geom, prv.geom)
	-- Join op locale tabel mét spatial index
	inner join gemeente gem on st_intersects(boom.geom, gem.geom)
	where
--		gem.provincie = 'West-Vlaanderen'
		gem.provincie = 'Oost-Vlaanderen'
--		gem.provincie = 'Antwerpen'
--		gem.provincie = 'Vlaams Brabant'
--		gem.provincie = 'Limburg'
-- Main query
--select * from cte_boom_provincies;
)
select
	b1.uuid as boom1_uuid
	, b1.ident2 as boom1_ident2
	, b1.ident8 as boom1_ident8
	, b1.prv_naam as boom1_provincie
	, b1.gem_naam as boom1_gemeente
	, b1.naam as boom1_naam
	, b1.soortnaam->>'DtcVegetatieSoortnaam.soortnaamWetenschappelijk' AS boom1_soortnaamWetenschappelijk
    , b1.soortnaam->>'DtcVegetatieSoortnaam.soortnaamNederlands' AS boom1_soortnaamNederlands
	, b1.geom as boom1_geom
	, ROUND(ST_Distance(b1.geom, b2.geom)::numeric, 3) as afstand
	, b2.uuid as boom2_uuid
	, b2.ident2 as boom2_ident2
	, b2.ident8 as boom2_ident8
	, b2.prv_naam as boom2_provincie
	, b2.gem_naam as boom2_gemeente
	, b2.naam as boom2_naam
	, b2.soortnaam->>'DtcVegetatieSoortnaam.soortnaamWetenschappelijk' AS boom2_soortnaamWetenschappelijk
    , b2.soortnaam->>'DtcVegetatieSoortnaam.soortnaamNederlands' AS boom2_soortnaamNederlands
	, b2.geom as boom2_geom
-- Join een boom met zichzelf
from cte_boom_index b1
--left join cte_boom_index b2 on  -- left join: alle bomen, inclusief dubbels
inner join cte_boom_index b2 on  -- inner join: enkel dubbele bomen
	-- Expliciet de provincienaam en gridcel naam definiëren.
	-- Een spatial index neemt dit voor haar rekening, maar de query is alsnog sneller door deze attributen te gebruiken.
	-- In dezelfde provincie
	b1.prv_naam = b2.prv_naam
	and
	-- In dezelfde gemeente
	b1.gem_naam = b2.gem_naam
	and
	-- Geen vergelijking van een boom met zichzelf
	b1.uuid <> b2.uuid
	-- De bufferafstand tussen 2 bomen is kleiner dan een gegeven afstand (te bepalen)
	and
	st_dwithin(b1.geom, b2.geom, 0.01)
--	st_dwithin(b1.geom, b2.geom, 1)
--	st_dwithin(b1.geom, b2.geom, 5)
order by b1.uuid, b2.uuid
/*
)
group by boom1_ident8
*/