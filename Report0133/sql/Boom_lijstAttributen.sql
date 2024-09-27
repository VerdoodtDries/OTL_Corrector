/* postgres
-- Date: Jul 26, 2024
-- Time: 3:47:46 PM
-- Author: Dries Verdoodt
-- Objective: Lijst alle attributen op van een boom
*/

-- Selecteer alle attributen van een boom
-- cd77f043-dc69-46ae-98a1-da8443ca26bf
select a.*
from attribuutkoppelingen ak
left join attributen a on ak.attribuutuuid = a.uuid
where ak.assettypeuuid = 'cd77f043-dc69-46ae-98a1-da8443ca26bf' 