# !/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------------------------------
# Name          : DyadTableZCTAChecker.py
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

###################################################################################################
#Input Variable loading and environment declaration
###################################################################################################
DyadTable = arcpy.GetParameterAsText(0) #dyad table
DyadTable_FieldList = [f.name for f in arcpy.ListFields(DyadTable)] # create field list from input
ZCTAs = arcpy.GetParameterAsText(1) #ZCTAs
ZCTAs_FieldList = [f.name for f in arcpy.ListFields(ZCTAs)] #create field list from input

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
#create a list of ZCTAs from shapeifle
###################################################################################################
#build a list of ZCTAs from ZCTA file
with arcpy.da.SearchCursor(ZCTAs,ZCTA_field) as cursor:
	for row in cursor:
		ZCTA_List.append(row[0])
arcpy.AddMessage(str(len(ZCTA_List)) + " ZCTAs in shapefile")

###################################################################################################
#Check that all ZCTAs in the dyad table are in the input ZCTA shapefile
###################################################################################################

with arcpy.da.SearchCursor(DyadTable,[DyadRec_field,DyadProv_field]) as cursor:
	for row in cursor:
		if str(row[0]) not in ZCTA_List:
			rec_ZCTAs_Misssing.append(str(row[0]))
		if str(row[1]) not in ZCTA_List:
			prov_ZCTAs_Misssing.append(str(row[1]))
		else:
			pass

ZCTAs_missing = set(chain(rec_ZCTAs_Misssing,prov_ZCTAs_Misssing)) #create a set of unique missing ZCTAs

###################################################################################################
#Final Output and cleaning of temp data/variables
###################################################################################################
if len(ZCTAs_missing) == 0:
	arcpy.AddMessage("Process complete! All ZCTAs in dyad table are in the ZCTA shapefile \nService Area building can commence")
else:
	arcpy.AddMessage(str(len(ZCTAs_missing)) + " ZCTAs in Dyad Table that aren't in the ZCTA shapefile.\nA different shapefile is suggested!")
	arcpy.AddMessage("Missing ZCTAs: {0}".format(ZCTAs_missing))
