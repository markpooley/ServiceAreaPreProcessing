# ServiceAreaPreProcessing
Set of scripts and corresponding tools to clean and pre process data for service area generation from geographic features.
There are host of scripts/tools to be used in the following order

##1. Tie Resolver

Takes, as input, a csv of recipient ZCTAs containing ties for provider ZCTAs. Provider ZCTAs are chosen in the following manner:

1. If any of the potential provider ZCTAs match the recpient ZCTA then the matching set is chosen.

2. If any of the candicate providers are adjacent to the recipient ZCTA, the provider sharing the longest common boundary with the recpient ZCTA is chosen.

3. In the event criteria 1 is not met, the closest provider ZCTA is identified by calculating the distance between the recipient and provider centroid.

Ouput is written to a CSV in a user specified location in the same format as the input CSV.

##2. Zip to ZCTA Crosswalk
Retrieves the most recent national Zip to ZCTA crosswalk from UDS (located at http://udsmapper.org/zcta-crosswalk.cfm) and saves it in a user specified folder. The crosswalk is migrated to a temporary table in a user specified geodatabase/workspace where all the of Iowa Zip codes are found and written to a new table in the same format.


The national table is deleted after processing is complete

## 3. Dyad Table ZCTA Checker
Checks that all recpient and provider ZCTAS found in the Dyad Table are also in the ZCTA shapefile that will be used for generating service areas

A warning is generated if ZCTAs in the dyad table are not found in the shapefile/feature class, as well as the number of visits/data that will not be accounted for.

##4. Dyad Table ZCTA Reconciler
Uses the crosswalk table generated from Zip to ZCTA crosswalk script to update the dyad table with the correct ZCTA assignments.



