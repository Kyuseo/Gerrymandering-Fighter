import json

with open('precincts.json') as f:
    precincts = json.load(f)

for p in precincts:
    print(precincts[p]["name"])
