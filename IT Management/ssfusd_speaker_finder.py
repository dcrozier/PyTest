import yaml
import os
import sys
import re
import library
import csv
from collections import defaultdict
import netaddr
from multiprocessing.pool import ThreadPool


print("Post Deployment - South San Francisco")

# Checks for site yaml file
if not os.path.isfile('yamls\\SSFUSD.yml'):
    sys.exit('Site not setup, run setup_site.py')

# Loads access info
with open('yamls\\SSFUSD.yml', 'r+') as f:
    saved_data = yaml.load(f)

with open('saved data\\oui_discovery.yml', 'r') as f:
    oui_discovery = yaml.load(f)

for ip in saved_data.iplist:

    print(ip.format())

    # ID Device
    print("Discovering Device")
    sysName = library.get(saved_data.community_string, ip.format(), 'SNMPv2-MIB', 'sysDescr')
    if not sysName:
        continue

    # Checks if Cisco Device
    if 'cisco' in sysName[0][0].lower():
        print('Skipping cisco device')
        continue

    chan, ssh = library.login(ip.format(), saved_data.username, saved_data.psk)
    if ssh == 0:
        continue

    running_config = library.get_running_config(chan, saved_data.enable)

    # Loads MAC-Table
    print("Loading MAC Table"),
    cam_table = library.get(saved_data.community_string, ip.format(), 'BRIDGE-MIB', 'dot1dTpFdbPort')
    print("MAC Table Loaded")

    # Loads Interface Index table
    print("Loading interface index"),
    ifIndex = library.get(saved_data.community_string, ip.format(), 'IF-MIB', 'ifIndex')
    ifName = library.get(saved_data.community_string, ip.format(), 'IF-MIB', 'ifName')
    print("Interface index Loaded")

    # Initialize interface class
    print("Organizing data")
    interface_record = {}
    for i in range(len(ifIndex[0])):
        interface_record[ifIndex[0][i]] = library.Interface(ifIndex[0][i], ifName[0][i])

    # Appends MAC addresses table to the interface class
    for i in range(len(cam_table[0])):
        mac = re.search(r'[0-9:a-fA-F]{17}', cam_table[1][i]).group()
        interface_record[cam_table[0][i]].mac_table.append(netaddr.EUI(mac))

    library.send_command('flow-control', chan=chan, configure=True)

    interface_configs = running_config.find_objects(r'interface.*')

    # Searches for live mac address and configures based on spreadsheet
    print("Searching interfaces for devices")
    for interface in sorted(interface_record):
        for mac in interface_record[interface].mac_table:
            for search in oui_discovery.items():
                try:
                    if mac.oui in search[1]:
                        if interface_record[interface].flag is 'switch':
                            continue
                        interface_record[interface].flag = search[0].lower()
                        print("Interface {0}: MAC {1}: Flag: {2}".format(
                            interface_record[interface].ifName, str(mac), interface_record[interface].flag)
                        )
                except netaddr.NotRegisteredError:
                    pass

    for interface in sorted(interface_record):
        if interface_record[interface].flag == 'ip_speaker':
            library.send_command(interface_record[interface].command_name, 'port-name **** SPEAKER ****', chan=chan, configure=True)
            library.send_command(interface_record[interface].command_name, 'inline power power-by-class 3', chan=chan, configure=True)

    print("Wait")
