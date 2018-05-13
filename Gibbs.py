import json
import random
import collections
import copy
from dbfpy import dbf

'''
For each precinct:
    * pid, PA_GEO_ID, index 15: Precinct ID
    * name, NAMELSAD10, index 6: Name of precinct
    * tpop, POP100, index 33: Total population
    * vap, VAP, index 17: Voting age population
    * demv, USCDV2010, index 52: Democratic congressional votes cast
    * repv, USCRV2010, index 53: Republican congressional votes cast
    * dist, US_HOUSE_D, index 37: District number in Pennsylvania
    * neighbors: list of string pIDs of neighbors
'''
class District:
    def __init__(self):
        self.democraticVotes = 0
        self.republicanVotes = 0
        self.population = 0
        self.precincts = set()

    # used to measure 'goodness' in terms of population vs ideal population
    def districtPopulationGap(self):
        diff = abs(idealPopulationPerDistrict - self.population)
        return diff / float(idealPopulationPerDistrict)



# SECTION: Init
NUM_DISTRICTS = 19
districts = [District() for x in range(20)]   #idx maps to the district. NOTE: District 0 is no mans land. Ignore completely
totalPopulation= 0
idealPopulationPerDistrict = 0
totalVoters = 0

with open('precincts.json') as json_data:
    precincts = json.load(json_data)

for pId in precincts:
    idx = precincts[pId]["dist"] #idx = districtnumber
    precinctDistrict = districts[idx]
    precinctDistrict.democraticVotes += precincts[pId]['demv']
    precinctDistrict.republicanVotes += precincts[pId]['repv']
    precinctDistrict.population += precincts[pId]['tpop']
    precinctDistrict.precincts.add(pId)
    if idx != '0':  #ignore no mans land
        totalPopulation += precincts[pId]['tpop']
        totalVoters += precincts[pId]['demv'] + precincts[pId]['repv']

idealPopulationPerDistrict = totalPopulation/NUM_DISTRICTS


# SECTION: Helpers
'''
used to measure 'goodness' in terms of efficiency.
d: districts array
'''
def efficiencyGap(d):
    wastedDemVotes = 0
    wastedRepVotes = 0
    for i in range(1, NUM_DISTRICTS+1):
        district = d[i]
        votesNeededToWin = (district.democraticVotes + district.republicanVotes) / 2

        if district.democraticVotes == district.republicanVotes:
            continue
        elif district.democraticVotes < votesNeededToWin:
            wastedDemVotes += district.democraticVotes
            wastedRepVotes += district.republicanVotes - votesNeededToWin
        else:
            wastedRepVotes += district.republicanVotes
            wastedDemVotes += district.democraticVotes - votesNeededToWin
    return abs(wastedDemVotes - wastedRepVotes) / float(totalVoters)


'''
used to measure 'goodness' of the population. Returns as a percentage over all districts
d: districts array
'''
def populationGap(d):
    totalGap = 0.0
    for idx, district in enumerate(d):
        if idx == 0: continue   # no mans land
        totalGap += district.districtPopulationGap()
    return totalGap / NUM_DISTRICTS  # get average gap

# Function: Weighted Random Choice
# --------------------------------
# Given a dictionary of the form element -> weight, selects an element
# randomly based on distribution proportional to the weights. Weights can sum
# up to be more than 1.
def weightedRandomChoice(weightDict):
    # print (weightDict)
    weights = []
    elems = []
    for elem in weightDict:
        weights.append(weightDict[elem])
        elems.append(elem)
    total = sum(weights)
    key = random.uniform(0, total)
    runningTotal = 0.0
    chosenIndex = None
    for i in range(len(weights)):
        weight = weights[i]
        runningTotal += weight
        if runningTotal > key:
            chosenIndex = i
            return elems[chosenIndex]
    raise Exception('Should not reach here')




print ('BEFORE: ')
print (efficiencyGap(districts))
print (populationGap(districts))


def legalChange(currentDistrictIdx, pId):
    currentDistrictPrecincts = copy.deepcopy(districts[currentDistrictIdx].precincts)  #make a copy?
    #if i remove this precinct from the current district, is that gonna break it?
    # print(pId)
    currentDistrictPrecincts.remove(pId)
    nconnectedComponents = 0
    startNode = currentDistrictPrecincts.pop()
    currentDistrictPrecincts.add(startNode)
    queue = collections.deque()
    queue.append(startNode)
    foundNodes = set()
    foundNodes.add(startNode)
    while len(queue) > 0:
        currStr = queue.popleft()
        curr = precincts[currStr]
        # print(currStr)
        currentDistrictPrecincts.remove(currStr)
        for neighbor in curr["neighbors"]:
            neighborNode = precincts[neighbor]
            if neighbor != pId and neighborNode["dist"] == currentDistrictIdx and neighbor not in foundNodes:
                foundNodes.add(neighbor)
                queue.append(neighbor)
    return len(currentDistrictPrecincts) == 0

    #run dfs on startNode and see if currentDistrictPrecincts empty

# SECTION: Gibbs
# loop over all precincts and switch districts probablistically.
# Most precincts will be surrounded by precincts of the same district and will not change.
# TODO: do batches of n
for i in range(50):
    for pId in precincts:
        precinct = precincts[pId]
        if precinct['dist'] == 0: continue   #no mans land

        # get all possible neighbors the precinct can change into. Includes self.
        neighboringPrecinctIdxs = precinct['neighbors']
        possibleDistricts = [precinct['dist']]
        myDistrict = precinct['dist']

        for neighborIdx in neighboringPrecinctIdxs:
            neighborDistrict = precincts[neighborIdx]['dist']
            if neighborDistrict != 0 and neighborDistrict not in possibleDistricts:
                if legalChange(myDistrict, pId):
                    possibleDistricts.append(neighborDistrict)


        # usually means surrounded by precincts of the same district
        if len(possibleDistricts) == 1:
            continue

        # get prob distribution of the neighbors and choose. Brunt of Gibbs.
        # tryout and choose
        choices = collections.defaultdict(float)
        origDistIdx = precinct['dist']

        popGoodness = {}   # population goodness
        effGoodness = {}   # efficiency goodness

        for choice in possibleDistricts:
            #rem from orig, put it in the new, calc goodness, update choices map, put it back (update remove)
            tempDistricts = copy.deepcopy(districts)
            #mod orig idx
            tempDistricts[origDistIdx].population -= precinct['tpop']
            tempDistricts[origDistIdx].democraticVotes -= precinct['demv']
            tempDistricts[origDistIdx].republicanVotes -= precinct['repv']
            #add to new idx
            tempDistricts[choice].population += precinct['tpop']
            tempDistricts[choice].democraticVotes += precinct['demv']
            tempDistricts[choice].republicanVotes += precinct['repv']

            # population
            oldPop = districts[origDistIdx].districtPopulationGap() + districts[choice].districtPopulationGap()
            newPop = tempDistricts[origDistIdx].districtPopulationGap() + tempDistricts[choice].districtPopulationGap()  #double counts if stying the same, prob fine?
            popMeasurement = oldPop - newPop

            popGoodness[choice] = popMeasurement
            effGoodness[choice] = efficiencyGap(tempDistricts)

            # choices[choice] = popMeasurement + efficiencyGap(tempDistricts) #populationGap(tempDistricts)

        # print('pop ', popGoodness)
        # print('eff ', effGoodness)

        delta = .00001

        minPop = min(popGoodness.itervalues())
        minEff = min(effGoodness.itervalues())
        # print('choices before: ', choices)
        # mod choices to remove negatives and 0s

        normPop = 0
        normEff = 0

        for key in popGoodness:
            popGoodness[key] -= minPop - delta
            normPop += popGoodness[key]**2
            effGoodness[key] -= minEff - delta
            effGoodness[key] = 1/(effGoodness[key])
            normEff += effGoodness[key]**2
        normEff = normEff ** .5
        normPop = normPop ** .5
        for key in effGoodness:
            effGoodness[key] /= normEff
            popGoodness[key] /= normPop
            choices[key] = 1.4 * popGoodness[key] + effGoodness[key]

        # print('eff :', effGoodness)
        # print('pop :', popGoodness)
        # print('choices: ', choices)


        newDistrict = weightedRandomChoice(choices)

        #mod orig idx
        districts[origDistIdx].population -= precinct['tpop']
        districts[origDistIdx].democraticVotes -= precinct['demv']
        districts[origDistIdx].republicanVotes -= precinct['repv']
        districts[origDistIdx].precincts.remove(pId)
        #add to new idx
        districts[newDistrict].population += precinct['tpop']
        districts[newDistrict].democraticVotes += precinct['demv']
        districts[newDistrict].republicanVotes += precinct['repv']
        districts[newDistrict].precincts.add(pId)

        precinct['dist'] = newDistrict

    if i % 10 == 0:
        print('iteration: ', i)
        print('popGap: ', populationGap(districts))
        print('efficiencyGap: ', efficiencyGap(districts))


# print ('AFTER 1 ITER: ')
print ('final eff: ', efficiencyGap(districts))
print ('final pop: ',  populationGap(districts))


# print out final assignment
# districtMap = {i: [] in range(NUM_DISTRICTS + 1)}
# for pId in precincts:
#     precinct = precincts[pId]
#     districtMap[precinct['dist']].append(pId)
#
# print districtMap
#


db = dbf.Dbf("new_data/pa_new.dbf")
for i in range(len(db)):
    rec = db[i]
    pId = rec['PA_GEO_ID'] - 1
    rec['US_HOUSE_D'] = precincts[str(pId)]['dist']
    rec.store()
    del rec
