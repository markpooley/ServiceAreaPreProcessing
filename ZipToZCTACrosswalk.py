# !/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------------------------------
# Name          :ZipToZCTACrosswalk.py
# Author  		: Mark Pooley (mark-pooley@uiowa.edu)
# Link    		: http://www.ppc.uiowa.edu
# Date    		: 2015-01-28 15:50:59
# Version		: $1.0$
# Description	: Asks user to input a URL where the crosswalk table is located and uses urllib to
# download the table and import it to a geodatabase. All instances of Zip Codes in Iowa are found
# and written to a new table named by the user. The temporary national table is deleted.
#-------------------------------------------------------------------------------------------------

###################################################################################################
#Import python modules
###################################################################################################
import os
import arcpy
import urllib #used to download file from url
from arcpy import env

###################################################################################################
#Input Variable loading and environment declaration
###################################################################################################
url = str(arcpy.GetParameterAsText(0)) #url of crosswalk
TableLocation = os.path.realpath(str(arcpy.GetParameter(1)))#where the Zip to ZCTA crosswalk will get put
TableName = str(arcpy.GetParameterAsText(2)) #name of the final table
OutputLocation = arcpy.GetParameterAsText(3) #location where table will be saved
ZipCodes = arcpy.GetParameterAsText(4)#Zip Codes

###################################################################################################
#Retrieve the most recent version of the crosswalk and put in user specified directory
###################################################################################################
crosswalkName = url.split('/')[-1]#file name split at the last / to name it
crosswalk = os.path.join(TableLocation,crosswalkName) #join path and name of the crosswalk
arcpy.AddMessage("Native crosswalk location: {0} \nCrosswalk name: {1}".format(TableLocation,crosswalkName))
arcpy.SetProgressorLabel("Downloading most recent version of the crosswalk...")
urllib.urlretrieve(url,crosswalk) #retrieve actual crosswalk from the url

###################################################################################################
#Convert excel Table in geodatabase, cull through it for all the Iowa Zip Codes and write them to
#to a new table
###################################################################################################
arcpy.SetProgressorLabel("Exporting excel file to table in geodatabase...")
TempTable = os.path.join(OutputLocation,'Temp_National_Table') #join path and name for the temp table
NationalTable = arcpy.ExcelToTable_conversion(crosswalk,TempTable) #create temporary table
NationalTable_FieldList = [f.name for f in arcpy.ListFields(NationalTable)] #create field list from table
State_Field = [f for f in NationalTable_FieldList if "STATE" in f or "State" in f][0] #find state field
Zip_Index = NationalTable_FieldList.index([f for f in NationalTable_FieldList if "ZIP" in f][0])
ZCTA_Index = NationalTable_FieldList.index([f for f in NationalTable_FieldList if "ZCTA" in f][0])
arcpy.AddMessage("State field found, named: {0}".format(State_Field))

ZipCount = 0 #tracking variable for number of Zips in Iowa

arcpy.SetProgressorLabel("finding number of zip codes in Iowa...")
#find all the Iowa Zip Codes and count them
with arcpy.da.SearchCursor(NationalTable,NationalTable_FieldList)as cursor:
	for row in cursor:
		if row[NationalTable_FieldList.index(State_Field)] == 'IA' or row[NationalTable_FieldList.index(State_Field)] == "IOWA":
			ZipCount +=1
arcpy.AddMessage("{0} Zip Codes found for Iowa".format(ZipCount))

###################################################################################################
#Go through national table and pull all the instances of Iowa and write to a new table
###################################################################################################
IowaCrosswalk = arcpy.CreateTable_management(OutputLocation,TableName,NationalTable) #create new dyad table using old as template
IowaCrosswalk_FieldList = [f.name for f in arcpy.ListFields(IowaCrosswalk)] #create field list from crosswalk
Zip_ZCTA_Dict = {}

arcpy.SetProgressor("step","Writing Iowa Zip codes to a new table from national table...",0,ZipCount,1)
with arcpy.da.SearchCursor(NationalTable,NationalTable_FieldList)as cursor:
	for row in cursor:
		#find instances of Iowa in the state attribute and write to a new table
		if row[NationalTable_FieldList.index(State_Field)] == 'IA' or row[NationalTable_FieldList.index(State_Field)] == "IOWA":
			Zip_ZCTA_Dict[str(row[Zip_Index])] = str(row[ZCTA_Index]) #populate zip to ZCTA dictionary, converting data to strings
			with arcpy.da.InsertCursor(IowaCrosswalk,IowaCrosswalk_FieldList) as iowa:
				iowa.insertRow(row)
			arcpy.SetProgressorPosition()

###################################################################################################
#Delete Temp National Table - It's no longer needed
###################################################################################################
arcpy.AddMessage("Deleting National Table...")
arcpy.Delete_management(NationalTable)

###################################################################################################
#Update the ZipCode file with ZCTA assignment from crosswalk
###################################################################################################
if "ZCTA" not in [f.name for f in arcpy.ListFields(ZipCodes)]: #look for ZCTA field, if not in the fild list, add it
	arcpy.AddField_management(ZipCodes,"ZCTA","TEXT")
ZipCodes_FieldList = [f.name for f in arcpy.ListFields(ZipCodes)]
Zip_Index = ZipCodes_FieldList.index([f for f in ZipCodes_FieldList if 'zcta' in f.lower()][0])#pull the index of the Zip field
ZCTA_Index = len(ZipCodes_FieldList) - 1 #ZCTAs was added last, so it's the last entry in the field list

featureCount = int(arcpy.GetCount_management(ZipCodes).getOutput(0)) #get number of features in ZCTAs

#look through the ZCTA file and update ZCTA field from crosswalk
arcpy.SetProgressor("step","determing Zip to ZCTA assignment from crosswalk",0,featureCount,1)
with arcpy.da.UpdateCursor(ZipCodes,ZipCodes_FieldList) as cursor:
	for row in cursor:
		if row[Zip_Index] in Zip_ZCTA_Dict.keys(): #look for Zip in the Zip dictionary keys
			row[ZCTA_Index] = Zip_ZCTA_Dict[row[Zip_Index]] #update the ZCTA field by using the dictionary
			cursor.updateRow(row)#update row
		arcpy.SetProgressorPosition()

###################################################################################################
#Final Output and cleaning of temp data/variables
###################################################################################################
arcpy.AddMessage("Iowa Zip To ZCTA crosswalk Table Name:{0}".format(TableName))
arcpy.AddMessage("Iowa Zip To ZCTA crosswalk Table Location:{0}".format(os.path.realpath(str(IowaCrosswalk))))
arcpy.AddMessage("Process complete!")