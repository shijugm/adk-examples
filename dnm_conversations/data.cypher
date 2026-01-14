CREATE CONSTRAINT FOR (s:State) REQUIRE s.stateId IS UNIQUE;
CREATE CONSTRAINT FOR (f:Facility) REQUIRE f.facilityId IS UNIQUE;
CREATE CONSTRAINT FOR (a:Article) REQUIRE a.articleId IS UNIQUE;
CREATE CONSTRAINT FOR (v:ArticleVisit) REQUIRE v.visitId IS UNIQUE;

// 1. Create States
UNWIND [
  {id: 'VIC', name: 'Victoria'},
  {id: 'NSW', name: 'New South Wales'},
  {id: 'QLD', name: 'Queensland'},
  {id: 'WA', name: 'Western Australia'},
  {id: 'SA', name: 'South Australia'},
  {id: 'TAS', name: 'Tasmania'}
] AS stateData
CREATE (s:State {stateId: stateData.id, stateName: stateData.name});

// 2. Create 50 Facilities with weighted distribution
UNWIND range(1, 50) AS i
WITH i,
     CASE 
       WHEN i <= 15 THEN 'VIC' // 15 in Melbourne
       WHEN i <= 30 THEN 'NSW' // 15 in Sydney
       WHEN i <= 40 THEN 'QLD' // 10 in Brisbane
       WHEN i <= 44 THEN 'WA'
       WHEN i <= 48 THEN 'SA'
       ELSE 'TAS' 
     END AS targetState
MATCH (s:State {stateId: targetState})
CREATE (f:Facility {
  facilityId: 'FAC' + i,
  facilityName: 'Facility ' + i + ' (' + targetState + ')'
})
CREATE (f)-[:BELONGS_TO]->(s);


// Delivered ARTICLES

UNWIND range(1, 1000) AS id 
Call { 
with id
 // 1. Pick Origin and Destination States
 MATCH (s:State) WITH collect(s) AS states, id
 WITH states[toInteger(rand()*size(states))] AS fromS, 
states[toInteger(rand()*size(states))] AS toS, id
 
// 2. Create Article (Random Date in 2025)
 MERGE (a:Article { articleId: 'ART-' + id})
SET
 a.articleName = 'ART-' + id,
 a.fromState = fromS.stateId,
 a.toState = toS.stateId,
 a.createDate = datetime('2025-01-01T00:00:00') + duration({
 days: toInteger(rand()*364), 
hours: toInteger(rand()*23)
 })
 
MERGE (j:Journey {journeyId: 'ART-' + id , articleStatus: 'D' })
MERGE (a)-[:HAS_JOURNEY]->(j)
 
WITH a, j, id , fromS, toS
 // 3. Select Start Facility (must be in fromState)
 MATCH (startF:Facility)-[:BELONGS_TO]->(fromS)
 WITH a, j, id, startF, toS ORDER BY rand() LIMIT 1
 // 4. Select End Facility (must be in toS)
 MATCH (endF:Facility)-[:BELONGS_TO]->(toS)
 WITH a, j, id, startF, endF ORDER BY rand() LIMIT 1
 // 5. Select 2 to 4 random intermediate facilities
 MATCH (midF:Facility) 
WHERE midF <> startF AND midF <> endF
 WITH a, j, id, startF, endF, midF ORDER BY rand() 
LIMIT (2 + toInteger(rand()*3)) 
// 6. Assemble the full route
 
WITH a, j, id, startF, endF, collect(midF) AS midList
 WITH a, j, id, [startF] + midList + [endF] AS route
 WITH a, j, id, route, size(route) as lastIdx
 // 7. Create Visits with cumulative time increases
 UNWIND range(0, size(route)-1) AS idx
 WITH a, j, id, lastIdx , idx, route[idx] AS targetFacility
MERGE (v:ArticleVisit {
 visitId: 'V-' + id + '-' + idx})
SET
 v.entryDate = a.createDate + duration({hours: (idx * 10) + toInteger(rand()*5)}),
v.seq = idx,
 v.facilityId= targetFacility.facilityId
 
MERGE (v)-[:AT_FACILITY]->(targetFacility)
 MERGE (j)-[:INCLUDES_VISIT]->(v)
 WITH a, j, lastIdx , v ORDER BY v.entryDate
 WITH a, j , lastIdx , collect(v) AS visits
 CALL apoc.nodes.link(visits, 'NEXT_VISIT')
 WITH a, j , lastIdx , visits[0] as firstFac, visits[lastIdx -1 ] as lastFac, visits
MERGE (j)-[:FIRST_FACILITY_VISIT]->(firstFac)
MERGE (j)-[:LAST_FACILITY_VISIT]->(lastFac)
return j ,visits , a
}
return j ,a, visits;


// Facility

 
UNWIND range(1001, 1150)  AS id 
Call { 
with id
 // 1. Pick Origin and Destination States
 MATCH (s:State) WITH collect(s) AS states, id
 WITH states[toInteger(rand()*size(states))] AS fromS, 
states[toInteger(rand()*size(states))] AS toS, id
 
// 2. Create Article (Random Date in 2025)
 MERGE (a:Article { articleId: 'ART-' + id})
SET
 a.articleName = 'ART-' + id,
 a.fromState = fromS.stateId,
 a.toState = toS.stateId,
 a.createDate = datetime('2025-01-01T00:00:00') + duration({
 days: toInteger(rand()*364), 
hours: toInteger(rand()*23)
 })
 
MERGE (j:Journey {journeyId: 'ART-' + id , articleStatus: 'F' })
MERGE (a)-[:HAS_JOURNEY]->(j)
 
WITH a, j, id , fromS, toS
 // 3. Select Start Facility (must be in fromState)
 MATCH (startF:Facility)-[:BELONGS_TO]->(fromS)
 WITH a, j, id, startF, toS ORDER BY rand() LIMIT 1
 // 4. Select End Facility (must be in toS)
 MATCH (endF:Facility)-[:BELONGS_TO]->(toS)
 WITH a, j, id, startF, endF ORDER BY rand() LIMIT 1
 // 5. Select 2 to 4 random intermediate facilities
 MATCH (midF:Facility) 
WHERE midF <> startF AND midF <> endF
 WITH a, j, id, startF, endF, midF ORDER BY rand() 
LIMIT (2 + toInteger(rand()*3)) 
// 6. Assemble the full route
 
WITH a, j, id, startF, endF, collect(midF) AS midList
 WITH a, j, id, [startF] + midList AS route
 WITH a, j, id, route, size(route) as lastIdx
 // 7. Create Visits with cumulative time increases
 UNWIND range(0, size(route)-1) AS idx
 WITH a, j, id, lastIdx , idx, route[idx] AS targetFacility
MERGE (v:ArticleVisit {
 visitId: 'V-' + id + '-' + idx})
SET
 v.entryDate = a.createDate + duration({hours: (idx * 10) + toInteger(rand()*5)}),
v.seq = idx,
 v.facilityId= targetFacility.facilityId
 
MERGE (v)-[:AT_FACILITY]->(targetFacility)
 MERGE (j)-[:INCLUDES_VISIT]->(v)
 WITH a, j, lastIdx , v ORDER BY v.entryDate
 WITH a, j , lastIdx , collect(v) AS visits
 CALL apoc.nodes.link(visits, 'NEXT_VISIT')
 WITH a, j , lastIdx , visits[0] as firstFac, visits[lastIdx -1 ] as lastFac, visits
MERGE (j)-[:FIRST_FACILITY_VISIT]->(firstFac)
MERGE (j)-[:LAST_FACILITY_VISIT]->(lastFac)
return j ,visits , a
}
return j ,a, visits;




// TRIP 


UNWIND range(1151, 1250)  AS id 
Call { 
with id
 // 1. Pick Origin and Destination States
 MATCH (s:State) WITH collect(s) AS states, id
 WITH states[toInteger(rand()*size(states))] AS fromS, 
states[toInteger(rand()*size(states))] AS toS, id
 
// 2. Create Article (Random Date in 2025)
 MERGE (a:Article { articleId: 'ART-' + id})
SET
 a.articleName = 'ART-' + id,
 a.fromState = fromS.stateId,
 a.toState = toS.stateId,
 a.createDate = datetime('2025-01-01T00:00:00') + duration({
 days: toInteger(rand()*364), 
hours: toInteger(rand()*23)
 })
 
MERGE (j:Journey {journeyId: 'ART-' + id , articleStatus: 'T' })
MERGE (a)-[:HAS_JOURNEY]->(j)
 
WITH a, j, id , fromS, toS
 // 3. Select Start Facility (must be in fromState)
 MATCH (startF:Facility)-[:BELONGS_TO]->(fromS)
 WITH a, j, id, startF, toS ORDER BY rand() LIMIT 1
 // 4. Select End Facility (must be in toS)
 MATCH (endF:Facility)-[:BELONGS_TO]->(toS)
 WITH a, j, id, startF, endF ORDER BY rand() LIMIT 1
 // 5. Select 2 to 4 random intermediate facilities
 MATCH (midF:Facility) 
WHERE midF <> startF AND midF <> endF
 WITH a, j, id, startF, endF, midF ORDER BY rand() 
LIMIT (2 + toInteger(rand()*3)) 
// 6. Assemble the full route
 
WITH a, j, id, startF, endF, collect(midF) AS midList
 WITH a, j, id, [startF] + midList  AS route
 WITH a, j, id, route, size(route) as lastIdx
 // 7. Create Visits with cumulative time increases
 UNWIND range(0, size(route)-1) AS idx
 WITH a, j, id, lastIdx , idx, route[idx] AS targetFacility
MERGE (v:ArticleVisit {
 visitId: 'V-' + id + '-' + idx})
SET
 v.entryDate = a.createDate + duration({hours: (idx * 10) + toInteger(rand()*5)}),
v.seq = idx,
 v.facilityId= targetFacility.facilityId
 
MERGE (v)-[:AT_FACILITY]->(targetFacility)
 MERGE (j)-[:INCLUDES_VISIT]->(v)
 WITH a, j, lastIdx , v ORDER BY v.entryDate
 WITH a, j , lastIdx , collect(v) AS visits
 CALL apoc.nodes.link(visits, 'NEXT_VISIT')
 WITH a, j , lastIdx , visits[0] as firstFac, visits[lastIdx -1 ] as lastFac, visits
MERGE (j)-[:FIRST_FACILITY_VISIT]->(firstFac)
MERGE (j)-[:LAST_FACILITY_VISIT]->(lastFac)
return j ,visits , a
}
return j ,a, visits;





// Set dwell and transit time

MATCH (fromFac)-[r:NEXT_VISIT]->(toFac)
// with fromFac, r, toFac, 
with fromFac, r, toFac, fromFac.facilityId as frmId, toFac.facilityId as toId, fromFac.entryDate as fromdt , toFac.entryDate as toDt , 
fromFac.entryDate + duration({seconds: toInteger(rand() * duration.inSeconds(fromFac.entryDate, toFac.entryDate ).seconds)}) as exitDt
with fromFac, r, toFac, frmId, toId, duration.inSeconds(fromdt, exitDt).minutes as dwell, duration.inSeconds( exitDt, toDt).minutes as transit , fromdt, exitDt, toDt
SET 
fromFac.dwellTime = dwell,
 fromFac.lastScan = exitDt,
 r.transitTime = transit;
// set last scan for the last facility visit. 

Match (av:ArticleVisit) 
where av.lastScan is null 
with av, av.entryDate as entryDate, av.entryDate + duration({seconds: toInteger(rand() * 99000)}) as exitDt
with av, av.id as aid, duration.inSeconds(entryDate, exitDt).minutes as dwell , entryDate, exitDt 
SET 
av.dwellTime = dwell,
 av.lastScan = exitDt;


 


// set from FacId to FacId 

//delivered 
MATCH (a:Article)-[:HAS_JOURNEY]->(j:Journey)-[:LAST_FACILITY_VISIT]->(avn)
where j.articleStatus = 'D'
MATCH (j)-[:FIRST_FACILITY_VISIT]->(av1)
WITH a , j , av1 , avn
with a , av1.facilityId as f1 , avn.facilityId as fn
set 
a.fromFacilityId = f1 , 
a.toFacilityId = fn;

// inflight

MATCH (a:Article)-[:HAS_JOURNEY]->(j:Journey)-[:
INCLUDES_VISIT]->(av)
where j.articleStatus IN ['T' , 'F']
MATCH (j)-[:FIRST_FACILITY_VISIT]-(f1)
WITH a , j , f1.facilityId as firstFac, collect(av.facilityId) as afvs , a.toState as toS
call{
with afvs, toS 
MATCH (endF:Facility)-[:BELONGS_TO]->(s:State {stateId : toS})
WHERE NOT endF.facilityId IN afvs
WITH endF ORDER BY rand() LIMIT 1
return endF
}
with a, a.toState as toS , firstFac, endF.facilityId as fn
set 
a.fromFacilityId = firstFac, 
a.toFacilityId = fn;


// Create Containers
MATCH (a:Article)-[:HAS_JOURNEY]->(j:Journey)-[:LAST_FACILITY_VISIT]->(av)
where j.articleStatus = 'T'
MATCH (j)-[:FIRST_FACILITY_VISIT]->(f1)
WITH a , j , av , f1
with a.articleId as articleId, a.fromState as fromState, a.toState as toState , av.facilityId as startId , f1.facilityId as firstFac
with distinct firstFac, startId , toState
call{
with firstFac, startId , toState
MATCH (endF:Facility)-[:BELONGS_TO]->(s:State {stateId : toState})
WHERE endF.facilityId <> firstFac 
WITH endF ORDER BY rand() LIMIT 1
return endF
}
with collect( {fromFac: startId ,toFac: endF.facilityId}) as unq
UNWIND unq as u
MERGE ( c:Container {containerId : u.fromFac + "_" + u.toFac})
SET 
c.fromFacilityId = u.fromFac,
 c.toFacilityId = u.toFac ;

// Link Articles to Container 

MATCH (a:Article)-[:HAS_JOURNEY]-(j)-[:LAST_FACILITY_VISIT]-(lastVisit)
where j.articleStatus = 'T'
with a , lastVisit , a.toState as toS , a.toFacilityId as toFac , lastVisit.facilityId as startId 
call {
 WITH startId, toS
 MATCH (c:Container)
 where c.fromFacilityId = startId
 ORDER BY rand()
 LIMIT 1
 return c 
}
 MERGE (lastVisit)-[:TRANSPORTED_BY]->(c)

// Calculate Journey Time 

MATCH (j:Journey)-[:LAST_FACILITY_VISIT]->(fn)
MATCH (j)-[:FIRST_FACILITY_VISIT]->(f1)
WITH j , f1, fn
set 
j.journeyTime = duration.inSeconds(f1.entryDate ,fn.lastScan ).minutes ; 



Refine 
From fac and toFac cannot be same for any article. 
In the same state transit . The article should not cross the state 
Transits should start in the last week to 


