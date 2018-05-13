import pysal
import shapefile
import json

'''
For each precinct: 
    * pid, PA_GEO_ID, index 15: Precinct ID
    * name, NAMELSAD10, index 6: Name of precinct
    * tpop, POP100, index 33: Total population
    * vap, VAP, index 17: Voting age population
    * demv, USCDV2010, index 52: Democratic congressional votes cast
    * repv, USCRV2010, index 53: Republican congressional votes cast
    * dist, US_HOUSE_D, index 37: District number in Pennsylvania
    * neighbors
'''
precincts = {}
pa = shapefile.Reader('data/pa_final.shp')
for r in pa.records():
    pid = str(r[15]-1)
    p = {"pid": pid, "name": r[6], "tpop": r[33], "vap": r[17], "demv": int(r[52]), "repv": int(r[53]), "dist": r[37]}
    if pid in precincts:
        raise Exception("pid already in precincts")
    precincts[pid] = p

w = pysal.weights.Rook.from_shapefile("data/pa_final.shp")
for i in range(len(w.neighbors)):
    pid = str(i)
    neighbors = [str(x) for x in w.neighbors[i]]
    precincts[pid]["neighbors"] = neighbors

with open('precincts.json', 'w') as out:
    json.dump(precincts, out)

