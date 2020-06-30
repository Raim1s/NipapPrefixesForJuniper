#!/usr/bin/python
import sys,ast
import ncclient
from ncclient import manager
import xml.etree.ElementTree as ET
import re
from datetime import date
from jinja2 import Template

def writeFileContentToVariable(inputFileName):
   with open(inputFileName, 'r') as f:
      return f.read().replace('\n','')

def getInterfaces(switch, bkId, username, idRsaKeyFilename):
    with manager.connect(host=switch, port=830, username=username, key_filename=idRsaKeyFilename, device_params={'name': 'junos'}, hostkey_verify=False) as m:
        intefaceList = list()
        rpc = """<get-interface-information><descriptions/></get-interface-information>"""
        obj = m.rpc(rpc).data_xml.replace('\n','')
        root = ET.fromstring(obj)
        for x in root.findall('.interface-information/physical-interface'):
            description = x.find('./description').text
            name = x.find('./name').text
            #if re.search(r'^BK-{0} //'.format(bkId), description):
            if bkId in description:
                intefaceList.append(name)
        interfaces = {'switch': switch, 'interfaces': intefaceList}
    return(interfaces)

def deleteUnusedACL(switch, username, idRsaKeyFilename):
    interfaceFilters = set()
    filters = set()
    with manager.connect(host=switch, port=830, username=username, key_filename=idRsaKeyFilename, device_params={'name': 'junos'}, hostkey_verify=False) as m:
        rpc ="""
            <get-config>
                <source>
                    <running/>
                </source>
                <filter type="subtree">
                    <configuration>
                        <interfaces/>
                    </configuration>
                </filter>
            </get-config>
        """
        obj = m.rpc(rpc).data_xml.replace('\n','')
        root = ET.fromstring(obj)
        for x in root.findall("./data/configuration/interfaces/interface/*/family/ethernet-switching/filter/"):
            if re.search(r'^ACL-BK-', x.text):
                # print("Interface filters:", x.text, "Sukurtas automato")
                interfaceFilters.add(x.text)
            # else:
            #     print("Interface filters:", x.text)

        rpc ="""
            <get-config>
                <source>
                    <running/>
                </source>
                <filter type="subtree">
                    <configuration>
                        <firewall/>
                    </configuration>
                </filter>
            </get-config>
        """
        obj = m.rpc(rpc).data_xml.replace('\n','')
        root = ET.fromstring(obj)
        for x in root.findall("./data/configuration/firewall/family/ethernet-switching/filter/name"):
            if re.search(r'^ACL-BK-', x.text):
                # print("Filters:", x.text, "Sukurtas automato")
                filters.add(x.text)
            # else:
            #     print("Filters:", x.text)

        unusedFilter = filters - interfaceFilters

        if len(unusedFilter) != 0:
            deleteFilterTemplate = """
                <config>
                    <configuration>
                            <firewall>
                                <family>
                                    <ethernet-switching>
                                        {%- for name in filterName %}
                                        <filter operation="delete">
                                            <name>{{name}}</name>
                                        </filter>
                                        {%- endfor %}
                                    </ethernet-switching>
                                </family>
                            </firewall>
                    </configuration>
                </config>
            """
            t = Template(deleteFilterTemplate)
            root = t.render(filterName=unusedFilter)

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

    return("There is no unused filters")



def configureAccessList(switch, bkId, username, idRsaKeyFilename, ipList):
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
    root = t.render(id=bkId ,data=ipList)

    with manager.connect(host=switch, port=830, username=username, key_filename=idRsaKeyFilename, device_params={'name': 'junos'}, hostkey_verify=False) as m:

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

def configureInputAccessList(switch, bkId, username, idRsaKeyFilename, interfaceList):

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
    root = t.render(id=bkId ,data=interfaceList)

    with manager.connect(host=switch, port=830, username=username, key_filename=idRsaKeyFilename, device_params={'name': 'junos'}, hostkey_verify=False) as m:

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
# Get switch IPs from switchIPs.txt and set default filenames
##############################################################################
with open('switchIPs.txt', 'r') as f:
   switchList = f.read().split('\n')
switchList = filter(None,switchList)

username = "nipapAutomation"
idRsaKeyName = "id_rsa"

today = date.today()
ymdToday = today.strftime('%Y-%m-%d')
outFilenamePrefixes = 'nipap_prefixes_' + today.strftime('%Y-%m-%d')
##############################################################################
# Configure switches

# Permissions required on switch:
# class ACL {
#     permissions [ configure firewall-control interface-control network view ];
#     allow-configuration "(interfaces .* unit 0 family ethernet-switching filter input ACL-BK-.*)|(firewall family ethernet-switching filter ACL-BK-.*)";
#     deny-configuration ".*;";
# }

##############################################################################
config = ast.literal_eval(writeFileContentToVariable(outFilenamePrefixes))
for item in config:
    for switch in switchList:
        print(switch)
        interfaceList = getInterfaces(switch, item['bkId'], username, idRsaKeyName)
        if len(interfaceList['interfaces']) != 0:
            print(interfaceList['interfaces'])
            print("Configuring ACL")
            print(configureAccessList(switch, item['bkId'], username, idRsaKeyName, item['ipList']))
            print("Configuring Interface")
            print(configureInputAccessList(switch, item['bkId'], username, idRsaKeyName, interfaceList['interfaces']))
        print(deleteUnusedACL(switch, username, idRsaKeyName))
