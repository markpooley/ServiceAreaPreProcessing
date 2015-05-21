# !/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------------------------------
# Name          : InitialDyadTableCreator
# Author  		: Mark Pooley (mark-pooley@uiowa.edu)
# Link    		: http://www.ppc.uiowa.edu
# Date    		: 2015-05-21 11:00:38
# Version		: $1.0$
# Description	:
#--------------------------------------------------------------------------------------------------

###################################################################################################
#Import python modules
###################################################################################################
import os
import arcpy
from arcpy import env
from operator import itemgetter
from collections import defaultdict

###################################################################################################
#Input Variable loading and environment declaration
###################################################################################################
points = arcpy.GetParameterAsText(0) #points with provider zip field
memZip = arcpy.GetParameterAsText(1) #member zip field
provZip = arcpy.GetParameterAsText(2) # provider zip field
tableName = arcpy.GetParameterAsText(3) #empty table to be populated
###################################################################################################
# Defining global functions
###################################################################################################

#create dyad table in same workspace as input data and add fields
#---------------------------------------------------------------------------
outputPath = os.path.dirname(points) #get directory of points file
arcpy.AddMessage('outputPath: {0}'.format(outputPath)) # print path to tool
dyadTable = arcpy.CreateTable_management(outputPath,tableName) #create table
table_ls = ['REC_ZIP','PROV_ZIP','VISITS_DYAD','MAX_VISITS','VISITS_TOTAL'] #list of fields for table

#add fields from table_ls to to dyadTable
#---------------------------------------------------------------------------
for field in table_ls:
	arcpy.AddField_management(dyadTable,field,'LONG')

###################################################################################################
#Global variables to be used in process
###################################################################################################
memDict = defaultdict(list) #dictionary that will have a list of providers for each member zip/ZCTA
fieldList = [memZip,provZip] #create list for cursors
counterDict = defaultdict(list)#dictionary of
###################################################################################################
#create a dictionary of member zip codes and all the provider zips for each member zip
###################################################################################################
featureCount = int(arcpy.GetCount_management(points).getOutput(0))
arcpy.SetProgressor('step','getting count of all the providers for each member zip code...',0,featureCount,1)
with arcpy.da.SearchCursor(points,fieldList) as cursor:
	for row in cursor:
		memDict[row[0]].append(row[1])
		arcpy.SetProgressorPosition()
arcpy.AddMessage('{0} member zip codes found'.format(len(memDict)))


####################################################################################################
#find max visits and total visits for each member zip
####################################################################################################
#arcpy.SetProgressor('step','getting number of visits and max visits for each member zip',0,len(memDict),1)
#for key, ls in memDict.iteritems():
#	temp = dict((i, ls.count(i)) for i in ls)
#	counterDict[key].extend((sum(temp.values()),max(temp.values())))
#	arcpy.SetProgressorLabel('{0} max visits, {1} total visits for {2}'.format(max(temp.values()),sum(temp.values()),key))
#	arcpy.SetProgressorPosition()
#
####################################################################################################
#insert entries into dyad table
####################################################################################################
arcpy.SetProgressor('step','Building Dyad Table....',0,len(memDict),1)
with arcpy.da.InsertCursor(dyadTable,table_ls) as cursor:
	for key, ls in memDict.iteritems(): #pull each member zip from member dict
		temp = dict((i,ls.count(i))for i in ls) #temp dictionary of the count
		for k, v in temp.iteritems(): #
			cursor.insertRow((key,k,v,max(temp.values()),sum(temp.values())))
		arcpy.SetProgressorPosition()


###################################################################################################
#Final Output and cleaning of temp data/variables
###################################################################################################
arcpy.AddMessage("Process complete!")
