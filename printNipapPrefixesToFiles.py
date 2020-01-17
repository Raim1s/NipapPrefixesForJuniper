#!/usr/bin/python
import sys,ast
import pynipap
from pynipap import Prefix
from datetime import date, timedelta
#####################
# Output file names #
#####################
today = date.today()
ymdToday = today.strftime('%Y-%m-%d')
outFilenameToday = 'nipap_prefixes_' + ymdToday
outFilenameRemovedPrefixes = 'nipap_removed_prefixes_' + ymdToday
yesterday = date.today() - timedelta(days=1)
outFilenameYesterday = 'nipap_prefixes_' + yesterday.strftime('%Y-%m-%d')
########################
# Nipap authentication #
########################
pynipap.xmlrpc_uri = "http://username:password@nipap.local:1337/XMLRPC"
a = pynipap.AuthOptions({
        'authoritative_source': 'nlogin_nipap_client'
    })

customerQuery = {'val1':'customer_id','operator':'regex_match','val2':'^CUST-\d{5,}$'}
prefixSearch = Prefix.smart_search('',{},customerQuery)
nipapPrefixObjectsList = prefixSearch['result']
########################################
# Functions:                           #
# 1. Group Nipap prefix data by 'custId' #
# 2. Print variable contents to a file #
# 3. Write file contents to a variable #
########################################
def addNipapPrefixToCustomerPrefixList(customerPrefixList,customerId,nipapPrefix):
   ipList = list()
   ipList.append(nipapPrefix.split("/")[0])
   customerPrefixes = {
      'custId': customerId,
      'ipList': ipList
   }
   customerPrefixList.append(customerPrefixes)

def printVariableContentToFile(variable,outputFileName):
   orig_stdout = sys.stdout
   f = open(outputFileName,'w')
   sys.stdout = f

   print variable

   sys.stdout = orig_stdout
   f.close()

def writeFileContentToVariable(inputFileName):
   with open(inputFileName, 'r') as f:
      return f.read().replace('\n','')
########################################
# Create prefix list grouped by 'custId' #
########################################
prefixList = list()
for n in nipapPrefixObjectsList:
   if len(prefixList) == 0:
      addNipapPrefixToCustomerPrefixList(prefixList,n.customer_id,n.prefix)
   else:
      for p in prefixList:
         if p['custId'] == n.customer_id:
            addNewCustomer = False
            p['ipList'].append(n.prefix.split("/")[0])
            break
         else:
            addNewCustomer = True
      if addNewCustomer == True:
         addNipapPrefixToCustomerPrefixList(prefixList,n.customer_id,n.prefix)
##################################
# Print today's prefixes to file #
##################################
printVariableContentToFile(prefixList,outFilenameToday)
####################################################
# Find removed prefixes by checking if yesterday's #
# prefixes still exist in Nipap today              #
####################################################
try:
   nipapPrefixFileContentsToday = writeFileContentToVariable(outFilenameToday)
   nipapPrefixFileContentsYesterday = writeFileContentToVariable(outFilenameYesterday)
   removedPrefixList = list()
   for y in ast.literal_eval(nipapPrefixFileContentsYesterday):
      if y['custId'] not in nipapPrefixFileContentsToday:
         removedPrefixList.append(y['custId'])   
   printVariableContentToFile(removedPrefixList,outFilenameRemovedPrefixes)
except:
   print "File named " + outFilenameYesterday + " not found!"