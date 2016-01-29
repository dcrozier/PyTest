#!/usr/bin/python
import csv
import yaml
import os
from datetime import timedelta
import re
from pysnmp.entity.rfc3413.oneliner import cmdgen


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
if os.path.isfile('../ssfusd.yml'):
    with open('../ssfusd.yml', 'r') as stream:
        output = yaml.load(stream)
if os.path.isfile('../mac_inventory.yml'):
    with open('../mac_inventory.yml', 'r') as stream:
        output.append(yaml.load(stream))
    loaded_data = lambda x: output[x]
else:
    print('No data to load, file not found')
    exit()

# opens csv file
f = open('../inventory.csv', 'w+')
writer = csv.writer(f)
writer.writerow(('sysName', 'sysUpTime', 'IP Address', 'sysDescr'))

for ip in loaded_data('ip_addresses'):

    # Gathers some data
    sysName = get(loaded_data('community_string'), ip, 'SNMPv2-MIB', 'sysName')[0][0]
    sysDescr = get(loaded_data('community_string'), ip, 'SNMPv2-MIB', 'sysDescr')[0][0]
    sysUpTime = get(loaded_data('community_string'), ip, 'SNMPv2-MIB', 'sysUpTime')[0][0]
    dot1dTpFdbPort = get(loaded_data('community_string'), ip, 'BRIDGE-MIB', 'dot1dTpFdbPort')
    ifindex = get(loaded_data('community_string'), ip, 'IF-MIB', 'ifIndex')

    # Sets cam_table variable
    cam_table = {}
    for port in ifindex[0]: cam_table[port] = []

    # Appends MAC addresses to the interface
    mac = lambda x: re.search(r'[0-9:a-fA-F]{17}', x).group()
    for port in dot1dTpFdbPort[0]: cam_table[port].append(mac(dot1dTpFdbPort[1][dot1dTpFdbPort[0].index(port)]))

    print(sysName, str(timedelta(seconds=int(sysUpTime) / 100)), ip, sysDescr)
    writer.writerow((sysName, timedelta(seconds=int(sysUpTime) / 100), ip, sysDescr))

f.close()