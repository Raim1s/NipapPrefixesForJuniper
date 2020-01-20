# NipapPrefixesForJuniper
A set of Python scripts to integrate Nipap IP management software with Juniper switches in order to set IP ACLs on the Juniper's interfaces

1. printNipapPrefixesToFiles.py - a script used to connect to Nipap, collect prefix information using search filter and write prefix info to files named after the current date.

This script is intended to run once per day and running for the first time it generates one file with current Nipap prefix information. When running for the second time on the next day the script generates two files: a new file with Nipap prefix information, then compares that information with the information from previous day and generates another file with the prefixes which were removed from Nipap.

Variable customerQuery, which is used as a filter in search, can be changed to any desirable configuration according to the NIPAP API: https://nipap.readthedocs.io/en/latest/

2. SetJuniperACLs.py - a script used to configure ACLs on a Juniper switch. Firstly it collects Juniper's interfaces where interface descriptions contain the same parameter which is used in the search filter in the printNipapPrefixesToFiles.py script (in this case it is Nipap's "customer_id"). Then Nipap prefix file is read and ACLs are created/configured for the collected Juniper's interfaces in order for the specific interface to include only those IPs which are set in Nipap for the specific "customer_id" parameter. 

Note: If Juniper interfaces' descriptions do not contain the filter parameter ("customer_id"), ACLs won't be configured.

In the future SetJuniperACLs.py script will also have a function that removes deprecated ACLs from Junipers.
