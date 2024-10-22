/* postgres
-- Date: Oct 15, 2024
-- Time: 4:43:50 PM
-- Author: Dries Verdoodt
-- Objective: 
	Detecteer dubbele punten + of de dubbele punten elkaar opvolgen
*/
-- Voedingskabel: fc52ac7f-9f9e-4c32-899c-7908c7b12311
-- Signaalkabel: 3fb1b8fd-d678-4870-82d1-769cce0e447d
select *
from assets a 
where a.uuid = 'fc52ac7f-9f9e-4c32-899c-7908c7b12311';

select *
from assets a 
where a.uuid = '3fb1b8fd-d678-4870-82d1-769cce0e447d';

-- insert dummy data: geometrie van een niet-selectieve detectielus
-- Overwrite een random asset van dat type: Houten fietsbrug te Tervuren: 
update geometrie
set geometry = st_geomfromtext(wkt_string)
where assetuuid = 'fe654f6c-705b-4044-9061-e6e3cd8546bc'


-- oorspronkelijke query
WITH cte_geometrie_dubbele_punten AS (
    SELECT
        assetuuid,
        wkt_string,
        SUBSTRING("wkt_string" FROM '^[^ (]+') AS wkt_string_prefix,
        geometry,
        ST_geometrytype(geometry) as "st_geometrytype"
    FROM
        geometrie
    where
	    -- geen missing geometriën of multi-geometriën
        st_geometrytype(geometry) in ('ST_LineString', 'ST_Polygon', 'ST_Point')
        and
        ST_NPoints(st_removerepeatedpoints(geometry)) <> ST_NPoints(geometry)
)
select 
    g.assetuuid
    , at.uri as typeURI
    , at.label as assettype
    , g.wkt_string_prefix
    , ST_NPoints(g.geometry) - ST_NPoints(st_removerepeatedpoints(g.geometry)) as aantal_dubbele_punten
    -- Aantal karakters afronden tot het maximaal toegelaten aantal karakters in Google Sheets: 50.000
    , left(wkt_string, 100) as wkt_string_afgerond
FROM
    cte_geometrie_dubbele_punten g
left join assets a on g.assetuuid = a.uuid
left join assettypes at on a.assettype = at.uuid
where
    a.actief = true -- Enkel de actieve assets
    and
    at.URI !~ '^(https://grp.).*' -- Regular expression does not start with 
order by aantal_dubbele_punten desc


/*
 * Chat GPT
 * */
WITH cte_geometrie_duplicate_points AS (
    -- Step 1: Pre-filter singlepart Line and Polygon geometries, with duplicate points
    -- Detect duplicate points using the function ST_RemoveRepeatedPoints().
	-- This functions detects duplicate points, but not duplicate consecutive points
    SELECT
        g.assetuuid,
        g.geometry,
--        ST_RemoveRepeatedPoints(g.geometry) AS geometry_simplified, -- Remove repeated points
        ST_GeometryType(g.geometry) AS geom_type
    FROM
        geometrie g -- Replace with your actual table name
    left join assets a on g.assetuuid = a.uuid
    where
    	a.actief = true  -- actieve assets
        and ST_NumGeometries(g.geometry) = 1 -- Only single geometries, not multipart
        and (ST_GeometryType(g.geometry) = 'ST_LineString' OR ST_GeometryType(g.geometry) = 'ST_Polygon') -- LINESTRING or POLYGON
        and ST_NPoints(st_removerepeatedpoints(g.geometry)) <> ST_NPoints(g.geometry)  -- dubbele punten in geometrie, niet per se naast elkaar
--        and g.assetuuid = 'fe654f6c-705b-4044-9061-e6e3cd8546bc'
),
cte_points AS (
    -- Step 2: Extract points for both LINESTRING and POLYGON geometries
    SELECT
        g.assetuuid,
        (ST_DumpPoints(g.geometry)).path[1] AS point_order, -- Get the order of the points
        (ST_DumpPoints(g.geometry)).geom AS point_geom -- Extract individual points
    FROM
        cte_geometrie_duplicate_points g
),
cte_consecutive_points AS (
    -- Step 3: Join each point with the next consecutive point in the geometry
    SELECT
        p1.assetuuid,
        p1.point_order AS order_1,
        p2.point_order AS order_2,
        p1.point_geom AS point_1,
        p2.point_geom AS point_2
    FROM
        cte_points p1
    INNER JOIN
        cte_points p2
    ON
        p1.assetuuid = p2.assetuuid -- Join points from the same geometry
        AND p2.point_order = p1.point_order + 1 -- Compare consecutive points
)
SELECT
    p.assetuuid,
    p.order_1,
    ST_AsText(p.point_1) AS point_1_text,
    ST_AsText(p.point_2) AS point_2_text
FROM
    cte_consecutive_points p
WHERE
    ST_Equals(p.point_1, p.point_2) -- Filter where consecutive points are identical
order by p.assetuuid, p.order_1
