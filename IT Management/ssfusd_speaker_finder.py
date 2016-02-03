import yaml
import os
import sys
import re
import library
import csv
from collections import defaultdict
import netaddr

print("Post Deployment - South San Francisco")
SITE = raw_input("School Code: ").upper()

# Checks for site yaml file
if not os.path.isfile('yamls\\{0}.yml'.format(SITE)):
    sys.exit('Site not setup, run setup_site.py')

# Checks for mac address csv
if not os.path.isfile('csv\\{0}.csv'.format(SITE)):
    sys.exit('MAC address csv missing')

# Loads access info
with open('yamls\\{0}.yml'.format(SITE), 'r+') as f:
    saved_data = yaml.load(f)

# Reads mac to vlan spreadsheet for existing network
print("Loading MAC address to search for")
mac_per_vlan = defaultdict(list)
with open('csv\\{0}.csv'.format(SITE), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        for key in row.keys():
            mac_per_vlan[key].append(netaddr.EUI(library.format_mac(row[key])))

with open('saved_data\\oui_discovery.yml', 'r') as f:
    oui_discovery = yaml.load(f)

for ip in saved_data.iplist:

    # Loads MAC-Table
    print("Loading MAC Table")
    cam_table = library.get(saved_data.community_string, ip.format(), 'BRIDGE-MIB', 'dot1dTpFdbPort')
    print("MAC Table Loaded")

    # Loads Interface Index table
    print("Loading interface index")
    ifIndex = library.get(saved_data.community_string, ip.format(), 'IF-MIB', 'ifIndex')
    ifName = library.get(saved_data.community_string, ip.format(), 'IF-MIB', 'ifName')
    print("Interface index Loaded")

    # Initialize interface class
    print("Organizing data")
    interfaces = {}
    for i in range(len(ifIndex[0])):
        interfaces[ifIndex[0][i]] = library.Interface(ifIndex[0][i], ifName[0][i])

    # Appends MAC addresses table to the interface class
    for i in range(len(cam_table[0])):
        mac = re.search(r'[0-9:a-fA-F]{17}', cam_table[1][i]).group()
        interfaces[cam_table[0][i]].mac_table.append(netaddr.EUI(mac))

    # Searches for live mac address and configures based on spreadsheet
    print("Searching interfaces for devices")
    for intf in sorted(interfaces):
        for mac in interfaces[intf].mac_table:
            for search in mac_per_vlan.items():
                if mac in search[1]:
                    print ()