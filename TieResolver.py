# !/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------------------------------
# Name          : TieResolver.py
# Author  		: Mark Pooley (mark-pooley@uiowa.edu)
# Link    		: http://www.ppc.uiowa.edu
# Date    		: 2015-01-20 12:39:50
# Version		: $1.0$
# Description	:Takes as input a table of ties and a table of near pologyons.
# Ties are resolved by choosing the provider ZCTA that shares the longest
# common boundary with the recipient ZCTA. If none of the candidate provider
# ZCTAs are adjacent, then the nearest is selected calculating the distance
# between the rec_ZCTA and the prov_ZCTA
# ---------------------------------------------------------------------------

###################################################################################################
#Import python modules
###################################################################################################

import arcpy
from arcpy import env
import math
import csv
import os
from operator import itemgetter
from collections import defaultdict

###################################################################################################
#Input Variable loading and environment declaration
###################################################################################################
tieTable = arcpy.GetParameterAsText(0) #table of recipient provider ties
nbrTable = arcpy.GetParameterAsText(1) #table of polygon neighbors generated from ZCTAs
ZCTAs = arcpy.GetParameterAsText(2) #ZCTAs input
outputLocation = arcpy.GetParameterAsText(3) #location of output file
outFile = arcpy.GetParameterAsText(4) #name of ouput file
#check if '.csv' at end of outFile name, if not add it.
if outFile[:-4] != '.csv':
	outFile = outFile + '.csv'

outFile = os.path.join(outputLocation,outFile) #concantenate path and file name so it gets stored in correct location

env.workspace = arcpy.GetParameterAsText(5)
env.overwriteOutput = True

###################################################################################################
# Defining global functions
###################################################################################################

#define function that will be used to calculate the distance between paired points. Cursor data will be fed into this
def distanceXY(lat1, long1, lat2, long2):

    # Convert latitude and longitude to
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0

    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians

    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians

    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + math.cos(phi1)*math.cos(phi2))
    arc = math.acos(cos)

    #multiple by 3960 to get miles
    arc = arc *3960
    return arc

###################################################################################################
#Global variables to be used in process
###################################################################################################
tempDict = defaultdict(list) #establish default dictionary to be populated with all csv entries
tieDict = {} #dictionary that will keep just ties
resolvedDict = {} #dictionary to contain resolved/matched ties
nbrTable_FieldList = [f.name for f in arcpy.ListFields(nbrTable)]
ZCTAs_FieldList = [f.name for f in arcpy.ListFields(ZCTAs)]
outList = [] # output list of entries that will be written to output CSV

###################################################################################################
#Pull field variables from field lists
###################################################################################################
src_ZCTA_field = [f for f in nbrTable_FieldList if 'src_' in f][0] #find src field within field list
nbr_ZCTA_field = [f for f in nbrTable_FieldList if 'nbr_' in f][0] #find nbr field within field list
ZCTA_field = [f for f in ZCTAs_FieldList if 'ZCTA' in f or 'ZIP' in f][0] #find ZCTA field within field list
length_Field = [f for f in nbrTable_FieldList if 'LENGTH' in f][0] #find LENGTH field within field list

###################################################################################################
#read in input CSV and create dictionaries of tied Rec ZCTAs
###################################################################################################

#open tieTable csv as reader csv and create a temporary dictionary of rec and prov ZCTAs from rows
with open(tieTable, "rb") as inFile:
	rowCount = 0
	#sniff into 10kb of csv to check dialect create a reader using the identified dialect and
	dialect = csv.Sniffer().sniff(inFile.read(10*1024))
	inFile.seek(0)
	reader = csv.reader(inFile, dialect) #reader object
	header = reader.next() #create header

	for row in reader:
		tempDict[row[0]].append(row[1])
		outList.append(row)
		rowCount +=1

#create new dictionary by iterating through current one and checking for value lists greater than 1
#lists greater than 1 indicate a tie
tieDict = {}
for key,value in tempDict.iteritems():
	if len(value) > 1:
		tieDict[key] = value
arcpy.AddMessage(str(len(tieDict)) + " ties found in data... ")

###################################################################################################
#Find best provider match where providers are
#adjacent/touching recipient ZCTA
###################################################################################################

#main loop to iterate through the ties dictionary and
arcpy.SetProgressor("step","Checking for matching provider ZCTAs adjacent to recipients...",0,len(tieDict),1)
for key,values in tieDict.iteritems():
	srcQuery =  src_ZCTA_field + " = '" + str(key) + "'"
	dyadBorder = 0

	#first check that the rec and prov don't match. If they do, consider the tie resolved by making the provider
	#zcta that of the recipient
	if key in values:
		resolvedDict[key] = values[values.index(key)]

	else:
		#create search cursor that will look through the neighbor table first.
		#in the future look to see if neighbors and shared boreder length can be identified
		#using geomtries instead of a bulky neighbor table
		with arcpy.da.SearchCursor(nbrTable,nbrTable_FieldList,srcQuery) as cursor:
			for row in cursor:
				if row[nbrTable_FieldList.index(nbr_ZCTA_field)] in values:
					if row[nbrTable_FieldList.index(length_Field)] > dyadBorder:
						dyadBorder = row[nbrTable_FieldList.index(length_Field)]
						provZCTA = row[nbrTable_FieldList.index(nbr_ZCTA_field)]
						arcpy.SetProgressorLabel("Match Found!")
						#resolvedDict[key] = provZCTA
		if dyadBorder > 0:
			#create match from the rec and provider sharing the most boundary length
			resolvedDict[key] = provZCTA
	arcpy.SetProgressorPosition() #update progressor positon

arcpy.AddMessage(str(len(resolvedDict)) + " ties resolved by finding martching or adjacent provider ZCTAs..." )


#create set of those where neighbor search is needed because provider ZCTAS
#aren't adjacent.  Use iteritems to iterate through a dictionary correctly.
for key,value in resolvedDict.iteritems():
	if tieDict.has_key(key):
		#if key is in resolved dictionary, pop identified key from tie dictionary and keep none of the values
		tieDict.pop(key,None)

arcpy.AddMessage(str(len(tieDict)) + " remaining ties to be resolved by finding nearest provider ZCTA...")

###################################################################################################
#Find best provider match - being the closest provider to the recipient ZCTA based on the
#distance between recipient and candidate provider centroid
###################################################################################################

#loop through remaining ties to find the nearest provider ZCTA
arcpy.SetProgressor('step','finding nearest provider ZCTAs for remaining ties...',0,len(tieDict),1)
for key,values in tieDict.iteritems():
	tempDict = {} #temporary dictionary to track the best recipient provider match
	recQuery = ZCTA_field + " = '" + str(key) + "'" #query to be used for search cursor
	provDistance = 1e309 #check variable for distance checking. set to infinity for each key value

	#get recipient coordinates using Shape@TRUECENTROID
	with arcpy.da.SearchCursor(ZCTAs,["ZCTA5CE10","SHAPE@TRUECENTROID"],recQuery) as cursor:
		for row in cursor:
			recCoord = row[1]
			recX = recCoord[0] #rec lat/X var
			recY = recCoord[1] #rec lon/Y var

	#-------------------------------------------------------------------------------------------
	#iterate through provider zctas to find coordinates and pass them through the
	#distance function.
	#-------------------------------------------------------------------------------------------
	for value in values:
		provQuery = ZCTA_field + " = '" + str(value) + "'" #queary to be used for search cursor
		with arcpy.da.SearchCursor(ZCTAs,[ZCTA_field,"SHAPE@TRUECENTROID"],provQuery) as cursor:
			for row in cursor:
				provCoord = row[1] #pull coordinate pairs
				provX = provCoord[0] #prov lat/X var
				provY = provCoord[1] #prov long/Y var

				#feed coordinates into distanceXY funcation to calculate distance between the two pairs
				distance = distanceXY(recX,recY,provX,provY)
				if distance < provDistance:
					provDistance = distance # declare newly caluclate distance as the minimum distance
					tempDict[key] = value #reassign recipient and provider paring based on caluclation

	resolvedDict.update(tempDict)#update the resovled dictionary with the best fitting pair
	arcpy.SetProgressorPosition() #update progressor position through each iteration



###################################################################################################
#write final output file to CSV
###################################################################################################

arcpy.SetProgressor("step", "writing new CSV with all ties resolved",0,rowCount,1)

#open tieTable csv as reader csv and create a temporary dictionary of rec and prov ZCTAs from rows
readerFile =  open(tieTable, "rb")
dialect = csv.Sniffer().sniff(readerFile.read(10*1024)) #sniff into 10kb of csv to check dialect create a reader using the identified dialect and
readerFile.seek(0) #not sure what this does, but it's important
reader = csv.reader(readerFile, dialect) #reader object using snieefed dialect
header = reader.next() #create header

outCSV = open(outFile, 'wb') #open writer object
writer = csv.writer(outCSV,dialect) #writer object using the reader dialect
writer.writerow(header) #write header


for row in reader:
	if row[0] not in resolvedDict: #if rec ZCTA is not in the resolved Dictionary, just write the row
		writer.writerow(row)

	elif resolvedDict[row[0]] == row[1]: #if resolved dictionary value for key is equal to prov_ZCTA, write row
		writer.writerow(row)

	else:
		pass #pass, nothing to see hear, not even a slight weapons malfunction

	arcpy.SetProgressorPosition() #udpate progressor position

#close csv files.
outCSV.close()
readerFile.close()


arcpy.AddMessage("Process complete!\n" + "Output csv location: " + str(os.path.realpath(outFile)))
