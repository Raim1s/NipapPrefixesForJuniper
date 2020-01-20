#!/usr/bin/python
import sys,ast
import ncclient
from ncclient import manager
import xml.etree.ElementTree as ET
#import re
from datetime import date
from jinja2 import Template

switchList = ["IP","IP","IP"]
username = "username"
password = "pass"

today = date.today()
ymdToday = today.strftime('%Y-%m-%d')
outFilenamePrefixes = 'nipap_prefixes_' + today.strftime('%Y-%m-%d')

##############################################################################
# Functions
##############################################################################

def writeFileContentToVariable(inputFileName):
  with open(inputFileName, 'r') as f:
     return f.read().replace('\n','')

def getInterfaces(switch, custId, username, password):
   with manager.connect(host=switch, port=830, username=username, password=password, device_params={'name': 'junos'}, hostkey_verify=False) as m:
       intefaceList = list()
       rpc = """<get-interface-information><descriptions/></get-interface-information>"""
       obj = m.rpc(rpc).data_xml.replace('\n','')
       root = ET.fromstring(obj)
       for x in root.findall('.interface-information/physical-interface'):
           description = x.find('./description').text
           name = x.find('./name').text
           if custId in description:
              intefaceList.append(name)
       interfaces = {'switch': switch, 'interfaces': intefaceList}
   return(interfaces)

def configureAccessList(switch, custId, username, password, ipList):
   accessListTemplate  = """
   <config>
       <configuration>
               <firewall>
                   <family>
                       <ethernet-switching>
                           <filter operation="replace">
                               <name>ACL-{{id}}</name>
                               <term>
                                   <name>AllowARP</name>
                                   <from>
                                       <ether-type>arp</ether-type>
                                   </from>
                                   <then>
                                      <accept/>
                                   </then>
                               </term>
                               <term>
                                   <name>AllowedIp</name>
                                   <from>
                                       {%- for ip in data %}
                                       <source-address>
                                           <name>{{ip}}/32</name>
                                       </source-address>
                                       {%- endfor %}
                                   </from>
                                   <then>
                                       <accept/>
                                   </then>
                               </term>
                               <term>
                                   <name>DenyAny</name>
                                   <then>
                                       <discard/>
                                   </then>
                               </term>
                           </filter>
                       </ethernet-switching>
                   </family>
               </firewall>
       </configuration>
   </config>
   """

   t = Template(accessListTemplate)
   root = t.render(id=custId ,data=ipList)

   with manager.connect(host=switch, port=830, username=username, password=password, device_params={'name': 'junos'}, hostkey_verify=False) as m:
      m.lock()

      try:
         edit_config_result = m.edit_config(config=root).data_xml
         print("Load config: ", ET.fromstring(edit_config_result)[0].tag)
      except ncclient.operations.rpc.RPCError as e:         
         print("Load config error:", e)

      validate_result = m.validate().data_xml
      print("Validate config: ", ET.fromstring(validate_result)[1].tag)
 
      compare_config_result = m.compare_configuration().data_xml
      # print("Diff: ", ET.fromstring(compare_config_result)[0][0].text)

      commit_config_result = m.commit().data_xml
      print("Commit config: ", ET.fromstring(commit_config_result)[1].tag)

      m.unlock()
        
   return(ET.fromstring(compare_config_result)[0][0].text)

def configureInputAccessList(switch, custId, username, password, interfaceList):

   interfaceAccessListTemplate = """
   <config>
       <configuration>
               <interfaces>
                   {%- for interface in data %}
                   <interface>
                       <name>{{interface}}</name>
                       <unit>
                           <name>0</name>
                           <family>
                               <ethernet-switching>
                                   <filter operation="replace">
                                       <input>ACL-{{id}}</input>
                                   </filter>
                               </ethernet-switching>
                           </family>
                       </unit>
                   </interface>
                   {%- endfor %}
               </interfaces>
       </configuration>
   </config>
   """

   t = Template(interfaceAccessListTemplate)
   root = t.render(id=custId ,data=interfaceList)

   with manager.connect(host=switch, port=830, username=username, password=password, device_params={'name': 'junos'}, hostkey_verify=False) as m:
      m.lock()

      try:
         edit_config_result = m.edit_config(config=root).data_xml
         print("Load config: ", ET.fromstring(edit_config_result)[0].tag)
      except ncclient.operations.rpc.RPCError as e:         
         print("Load config error:", e)

      validate_result = m.validate().data_xml
      print("Validate config: ", ET.fromstring(validate_result)[1].tag)

      compare_config_result = m.compare_configuration().data_xml
      # print("Diff: ", ET.fromstring(compare_config_result)[0][0].text)

      commit_config_result = m.commit().data_xml
      print("Commit config: ", ET.fromstring(commit_config_result)[1].tag)

      m.unlock()
    
   return(ET.fromstring(compare_config_result)[0][0].text)

##############################################################################
# Configure switches 
##############################################################################

config = ast.literal_eval(writeFileContentToVariable(outFilenamePrefixes))
for item in config:
   for switch in switchList:
      interfaceList = getInterfaces(switch, item['custId'], username, password)
      if len(interfaceList['interfaces']) != 0:
         print(interfaceList['interfaces'])
         print(configureAccessList(switch, item['custId'], username, password, item['ipList']))
         print(configureInputAccessList(switch, item['custId'], username, password, interfaceList['interfaces']))
