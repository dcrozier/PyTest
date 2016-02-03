#!/usr/bin/python
import os
import re
from datetime import timedelta

import netaddr
import yaml
from pysnmp.entity.rfc3413.oneliner import cmdgen

import interface_profile


# Sends and receives an SNMP query
def get(community_string, ip, mib, request):
    cmdGen = cmdgen.CommandGenerator()
    value = ()
    oid = ()
    errorindication, errorstatus, errorindex, varbindtable = cmdGen.bulkCmd(
        cmdgen.CommunityData(community_string),
        cmdgen.UdpTransportTarget((ip, 161)),
        0,
        1,
        cmdgen.MibVariable(mib, request)
    )
    if errorindication:
        print(ip + ':', errorindication)
    if errorstatus:
        try:
            print('%s at %s' % (errorstatus.prettyPrint(), errorindex and varbindtable[int(errorindex) - 1] or '?'))
        except AttributeError:
            print('%s at %s' % (errorstatus, errorindex and varbindtable[int(errorindex) - 1] or '?'))
    else:
        varbindtable.pop()
        for varBindTableRow in varbindtable:
            for x, y in varBindTableRow:
                oid = oid + (x.prettyPrint(),)
                value = value + (y.prettyPrint(),)
    return value, oid


output = str()

# Loads saved data
if os.path.isfile('../access.yml'):
    with open('../access.yml', 'r') as stream:
        output = yaml.load(stream)
if os.path.isfile('../mac_inventory.yml'):
    with open('../mac_inventory.yml', 'r') as stream:
        output.update(yaml.load(stream))
    loaded_data = lambda x: output[x]
else:
    print('No data to load, file not found')
    exit()

for ip in loaded_data('ip_addresses'):

    # Gathers some data
    sysName = get(loaded_data('community_string'), ip, 'SNMPv2-MIB', 'sysName')[0][0]
    print(sysName)

    sysDescr = get(loaded_data('community_string'), ip, 'SNMPv2-MIB', 'sysDescr')[0][0]
    print(sysDescr)

    sysUpTime = get(loaded_data('community_string'), ip, 'SNMPv2-MIB', 'sysUpTime')[0][0]
    print(str(timedelta(seconds=int(sysUpTime) / 100)))

    cam_table = get(loaded_data('community_string'), ip, 'BRIDGE-MIB', 'dot1dTpFdbPort')
    print("MAC Table Loaded")

    ifIndex = get(loaded_data('community_string'), ip, 'IF-MIB', 'ifIndex')
    ifName = get(loaded_data('community_string'), ip, 'IF-MIB', 'ifName')
    print("Interface Table Loaded")

    interfaces = {}
    for i in range(len(ifIndex[0])):
        interfaces[ifIndex[0][i]] = interface_profile.Interface(ifIndex[0][i], ifName[0][i])

    # Appends MAC addresses to the interface
    for i in range(len(cam_table[0])):
        mac = re.search(r'[0-9:a-fA-F]{17}', cam_table[1][i]).group()
        interfaces[cam_table[0][i]].mac_table.append(netaddr.EUI(mac))

    for interface in interfaces:
        for mac in interfaces[interface].mac_table:
            if mac.oui in output['Access_Points']:
                interfaces[interface].flag = 1
            if mac.oui in output['IP_Speaker']:
                interfaces[interface].flag = 2
