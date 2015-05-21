# !/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------------------------------
# Name          : DyadTableZCTAReconciler.py
# Author  		: Mark Pooley (mark-pooley@uiowa.edu)
# Link    		: http://www.ppc.uiowa.edu
# Date    		: 2015-01-20 12:30:08
# Version		: $1.0$
# Description	: Simple script to check that all the ZCTAs in the dyad table
# are also in the ZCTA shapefile to be used in generating service areas.
# ---------------------------------------------------------------------------

###################################################################################################
#Import python modules
###################################################################################################
import arcpy
import os
import sets
from itertools import *
import numpy

###################################################################################################
#Input Variable loading and environment declaration
###################################################################################################
DyadTable = arcpy.GetParameterAsText(0) #dyad table
DyadTable_FieldList = [f.name for f in arcpy.ListFields(DyadTable)] # create field list from input
DyadVisits_Field = arcpy.GetParameterAsText(1)
ZCTAs = arcpy.GetParameterAsText(2) #ZCTAs
ZCTAs_FieldList = [f.name for f in arcpy.ListFields(ZCTAs)] #create field list from input
Crosswalk = arcpy.GetParameterAsText(3)

###################################################################################################
# Defining global functions
###################################################################################################


###################################################################################################
#Global variables to be used in process
###################################################################################################
DyadRec_field = [f for f in DyadTable_FieldList if 'rec' in f.lower()][0] #find rec_ZCTA field within field list
DyadProv_field = [f for f in DyadTable_FieldList if 'prov' in f.lower()][0] #find prov_ZCTA field within field list
ZCTA_field = [f for f in ZCTAs_FieldList if 'ZCTA' in f or 'ZIP' in f][0] #find ZCTA field within field list
ZCTA_List = [] # list of ZCTAs from ZCTA file
rec_ZCTAs_Misssing = [] #list of missing rec ZCTAs
prov_ZCTAs_Misssing = [] #list of misssing prov ZCTAs

###################################################################################################
#quickly get sum of visits using numpy array
###################################################################################################
VisitArray = arcpy.da.TableToNumPyArray(DyadTable,DyadVisits_Field,skip_nulls=True)
VisitsTotal = VisitArray[DyadVisits_Field].sum()
arcpy.AddMessage("{0:,} total visits found in dyad table".format(VisitsTotal))#add total to messages
del VisitArray #delete visits array, no longer needed

###################################################################################################
#Build a dictionary of assignments into memory for faster reconciling later
###################################################################################################
Crosswalk_FieldList = [f.name for f in arcpy.ListFields(Crosswalk)]
Crosswalk_ZipIndex = Crosswalk_FieldList.index([f for f in Crosswalk_FieldList if "zip" in f.lower()][0]) #pull Zip index from field list
Crosswalk_ZCTAIndex = Crosswalk_FieldList.index([f for f in Crosswalk_FieldList if "zcta" in f.lower()][0]) # pull ZCTA index from field list
ZipZCTA_Dict = {} #dictionary of assignments
featureCount = int(arcpy.GetCount_management(Crosswalk).getOutput(0))#get feature count

arcpy.SetProgressor("step","Building dictionary of assignments from crosswalk...",0,featureCount,1)
with arcpy.da.SearchCursor(Crosswalk,Crosswalk_FieldList) as cursor:
	for row in cursor:
		ZipZCTA_Dict[row[Crosswalk_ZipIndex]] = row[Crosswalk_ZCTAIndex]
		arcpy.SetProgressorPosition()


###################################################################################################
#create a list of ZCTAs from shapefile
###################################################################################################
arcpy.SetProgressorLabel("Building list of ZCTAs from {0}".format(ZCTAs))
with arcpy.da.SearchCursor(ZCTAs,ZCTA_field) as cursor:
	for row in cursor:
		ZCTA_List.append(row[0])

arcpy.AddMessage(str(len(ZCTA_List)) + " ZCTAs in shapefile")

###################################################################################################
#Check that all ZCTAs in the dyad table are in the input ZCTA shapefile
###################################################################################################
arcpy.SetProgressorLabel("Checking for ZCTAS in Dyad Table not in {0}".format(ZCTAs))
with arcpy.da.SearchCursor(DyadTable,[DyadRec_field,DyadProv_field]) as cursor:
	for row in cursor:
		if str(row[0]) not in ZCTA_List:
			rec_ZCTAs_Misssing.append(str(row[0]))
		if str(row[1]) not in ZCTA_List:
			prov_ZCTAs_Misssing.append(str(row[1]))
		else:
			pass


ZCTAs_missing = set(chain(rec_ZCTAs_Misssing,prov_ZCTAs_Misssing)) #create a set of unique missing ZCTAs
arcpy.AddMessage(str(len(ZCTAs_missing)) + " ZCTAs in Dyad Table that aren't in the ZCTA shapefile...")

rec_ZCTAs_Misssing = list(set(rec_ZCTAs_Misssing))#remove duplicates using set, and create a list froms set
prov_ZCTAs_Misssing = list(set(prov_ZCTAs_Misssing)) #remove duplicates using set, create a list from set

###################################################################################################
#Reconcile missing recipient ZCTAs in the Dyad Table
###################################################################################################
recIndex = DyadTable_FieldList.index([f for f in DyadTable_FieldList if "rec" in f.lower()][0])#get recipient field index
rec_unresolved = [] # list of those unresolved
rec_resolved = [] #list of resolved
Visits_Missed = 0 #track the number of visits
arcpy.SetProgressor("step","Reconciling recipient ZCTAs...",0,len(rec_ZCTAs_Misssing),1)
for i in rec_ZCTAs_Misssing:
	recQuery = DyadRec_field + " = " + i #query
	with arcpy.da.UpdateCursor(DyadTable,DyadTable_FieldList,recQuery) as cursor:
		for row in cursor:
			if str(row[recIndex]) in ZipZCTA_Dict.keys(): #check for entry in the dictionary
				row[recIndex] = int(ZipZCTA_Dict[str(row[recIndex])]) #reassign if found
				rec_resolved.append(ZipZCTA_Dict[str(row[recIndex])]) #append the assignment to the resolved list
				cursor.updateRow(row) #update row
			else:
				Visits_Missed += row[DyadTable_FieldList.index("VISITS_DYAD")]
				rec_unresolved.append(i)
			arcpy.SetProgressorPosition()

rec_resolved = list(set(rec_resolved))#remove duplicates
rec_unresolved = list(set(rec_unresolved)) #remove duplicates and create a list

del rec_ZCTAs_Misssing #don't need the orignal list anymore
###################################################################################################
#Reconcile missing provider ZCTAs in the Dyad Table
###################################################################################################
provIndex = DyadTable_FieldList.index([f for f in DyadTable_FieldList if "prov" in f.lower()][0])#get provider field index
prov_unresolved = [] #list of those unresolved
prov_resolved = [] #list of resolved
arcpy.SetProgressor("step","Reconciling provider ZCTAs...",0,len(prov_ZCTAs_Misssing),1)
for i in prov_ZCTAs_Misssing:
	provQuery = DyadRec_field + " = " + i
	with arcpy.da.UpdateCursor(DyadTable,DyadTable_FieldList,provQuery) as cursor:
		for row in cursor:
			if str(row[provIndex]) in ZipZCTA_Dict.keys():
				row[provIndex] = int(ZipZCTA_Dict[str(row[provIndex])])
				prov_resolved.append(ZipZCTA_Dict[str(row[provIndex])])
				cursor.updateRow(row)
			else:
				prov_unresolved.append(i)

			arcpy.SetProgressorPosition()
prov_resolved = list(set(prov_resolved))#remove duplicates
prov_unresolved = list(set(prov_unresolved))#remove duplicates

del prov_ZCTAs_Misssing #don't need the original list anymore
arcpy.AddMessage("{0} recipient ZCTAs resolved (found in dyad table with corresponding entry in crosswalk)...".format(len(rec_resolved)))
arcpy.AddMessage("{0} ZCTAs in Dyad table, but not found in crosswalk...".format(len(rec_unresolved)))
arcpy.AddMessage("resolved provider ZCTAs: {0}".format(prov_resolved))
arcpy.AddMessage("unresolved provider ZCTAs: {0}".format(prov_unresolved))
arcpy.AddMessage("{0:.4%} of visits will be unaccounted for...".format(float(Visits_Missed)/float(VisitsTotal)))

###################################################################################################
#Check for duplicate entries in the dyayd table, find them, update the visits field accordingly and
#delete duplicate fields
###################################################################################################
arcpy.SetProgressor("step","Checking duplicate recipient ZCTA entries in dyad table...",0,len(rec_resolved),1)
for i in rec_resolved:
	recQuery = DyadRec_field + " = " + i #query
	temp_Rec_List = []
	#-------------------------------------------------------------------------------------------
	#Look for duplicate entries of the same recipient and provider. This loop appends all the
	#providers to a list which will be checked for dupilcate entries
	#-------------------------------------------------------------------------------------------
	with arcpy.da.SearchCursor(DyadTable,DyadTable_FieldList,recQuery) as cursor:
		for row in cursor:
			temp_Rec_List.append(row[provIndex])

	#look in temp list for repeats (count > 1) and create a new list using set to
	#remove duplicates
	prov_Repeats = list(set(x for x in temp_Rec_List if temp_Rec_List.count(x) > 1))

	if not prov_Repeats: #if list is empty pass
		pass
	else:
		for j in prov_Repeats:
			maxVisits = 0
			RowKeepID = 0
			recProvQuery = DyadRec_field + " = " + str(i) + " AND " + DyadProv_field + " = " + str(j) #query
			with arcpy.da.UpdateCursor(DyadTable,DyadTable_FieldList,recProvQuery) as cursor:
				for row in cursor:
					maxVisits += row[DyadTable_FieldList.index(DyadVisits_Field)]
					row[DyadTable_FieldList.index(DyadVisits_Field)] = maxVisits
					RowKeepID = row[0] #get object ID of the row to keep which is the row with the max visits
					cursor.updateRow(row)

			#remove duplicates
			recProvQuery = DyadRec_field + " = " + str(i) + " AND " + DyadProv_field + " = " + str(j) #query
			with arcpy.da.UpdateCursor(DyadTable,DyadTable_FieldList,recProvQuery) as cursor:
				for row in cursor:
					#if row isn't the object ID to keep, delete it.
					if row[0] != RowKeepID:
						arcpy.SetProgressorLabel("{0} removed, for recipient {1}".format(j,i))
						cursor.deleteRow()

	arcpy.SetProgressorPosition()

###################################################################################################
#update number of utilizers, visits, max, and dyad_max fields for recipients that have been resolved
###################################################################################################
arcpy.SetProgressor("step","Updating vists, max visits, number of utilizers and max dyad fields for resolved ZCTAs...",0,len(rec_resolved),1)
for i in rec_resolved:
	recQuery = DyadRec_field + " = " + i #query
	maxVisits = 0
	utilizers = 0
	#aggregate visits and find the max number of visits
	with arcpy.da.SearchCursor(DyadTable,DyadTable_FieldList,recQuery) as cursor:
		for row in cursor:
			utilizers += row[DyadTable_FieldList.index(DyadVisits_Field)] #aggregate visits for the number of uitlizers
			if row[DyadTable_FieldList.index(DyadVisits_Field)] > maxVisits:
				maxVisits = row[DyadTable_FieldList.index(DyadVisits_Field)]

	#update the fields
	with arcpy.da.UpdateCursor(DyadTable,DyadTable_FieldList,recQuery) as cursor:
		for row in cursor:
			row[DyadTable_FieldList.index("MAX_VISITS")] = maxVisits
			row[DyadTable_FieldList.index("VISITS_DYAD")] = utilizers
			#assign the max accordingly
			if row[DyadTable_FieldList.index(DyadVisits_Field)] == maxVisits:
				row[DyadTable_FieldList.index("Dyad_max")] = 1
				cursor.updateRow(row)
			else:
				row[DyadTable_FieldList.index("Dyad_max")] = 0
			cursor.updateRow(row)

	arcpy.SetProgressorPosition()

####################################################################################################
#update the Base Zipcodes using the crosswalk
####################################################################################################
featureCount = int(arcpy.GetCount_management(ZCTAs).getOutput(0))
arcpy.SetProgressor('step','updating Base ZCTAs with correct ZCTA assignment',0,featureCount,1)
with arcpy.da.UpdateCursor(ZCTAs,[ZCTA_field]) as cursor:
	for row in cursor:
		try:
			row[0] = ZipZCTA_Dict[row[0]]
			cursor.updateRow(row)
		except KeyError:
			pass
		arcpy.SetProgressorPosition()


arcpy.AddMessage("Process Complete!")
