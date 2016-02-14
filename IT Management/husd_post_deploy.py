# coding=utf-8
import library
import re
import yaml
import netaddr
import os
import sys
import csv
from collections import defaultdict
import time

print("Post Deployment - Hayward")
SITE = raw_input("School Code: ").upper()

# Checks for site yaml file
if not os.path.isfile(os.path.sep.join(['yamls', SITE + '.yml'])):
    sys.exit('Site not setup, run setup_site.py')

# Loads access info
with open(os.path.sep.join(['yamls', SITE + '.yml']), 'r+') as f:
    saved_data = yaml.load(f)

# Checks for mac address csv
if not os.path.isfile(os.path.sep.join(['csv', saved_data.mac])):
    SEARCH = False
    print("MAC address csv missing, Skipping search")
else:
    SEARCH = True

# Checks for Port-mapping
if not os.path.isfile(os.path.sep.join(['csv', saved_data.port_map])):
    PORT_MAPPING = False
else:
    PORT_MAPPING = True

with open(os.path.sep.join(['saved data', 'oui_discovery.yml']), 'r') as f:
    oui_discovery = yaml.load(f)

# Reads mac to vlan spreadsheet for existing network
if SEARCH:
    print("Loading MAC address to search for")
    mac_per_vlan = defaultdict(list)
    with open(os.path.sep.join(['csv', saved_data.mac]), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key in row.keys():
                mac_per_vlan[key].append(netaddr.EUI(library.format_mac(row[key])))

if PORT_MAPPING:
    print("Loading port assignments")
    port_assignments = defaultdict(dict)
    iface = defaultdict(list)
    with open(os.path.sep.join(['csv', saved_data.port_map]), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'x' in row.values():
                iface['/1/'.join(row['D Port'].split('/'))].append(row.keys()[row.values().index('x')])
                port_assignments[row['Switch IP']].update(iface)

for ip in saved_data.iplist:

    # Opens SSH connection
    print("Opening SSH connection to {0}".format(ip.format()))
    chan, ssh = library.login(ip.format(), saved_data.username, saved_data.psk)

    if len(saved_data.tftp) > 3:
        # Updates Boot Rom and waits for startup
        print("Loading boot loader")
        library.send_command('copy tftp flash {0} 08030d/ICX7450/Boot/spz10105.bin boot'.format(saved_data.tftp),
                             chan=chan)

        # Visual timer to wait for boot rom to finish loading
        for t in range(30, -1, -5):
            minutes = t / 60
            seconds = t % 60
            print "%d:%2d" % (minutes, seconds),
            time.sleep(5.0)
        print("Done")

    # Removes vlan 24 & 26
    print("Removing vlan 24, 26, and 70")
    library.send_command('no vlan 24', 'no vlan 26', 'no vlan 70', configure=True, chan=chan)

    # Adds vlan 20
    print("Adding vlan 20 and 70")
    library.send_command('vlan 20 name Servers_Printers', 'tag ethernet 1/2/1', 'span 80', configure=True, chan=chan)
    library.send_command('vlan 70 name VoIP', 'tag ethernet 1/2/1', 'span 80', configure=True, chan=chan)

    if PORT_MAPPING:
        print("Applying port map")
        assignments = port_assignments[ip.format()]
        for iface in assignments:
            if iface == '½':
                assignments['1/1/2'] = assignments.pop(iface)
                iface = '1/1/2'
            if iface == '¼':
                assignments['1/1/4'] = assignments.pop(iface)
                iface = '1/1/4'
            for vlan in assignments[iface]:
                tag = "vlan {0}\ntagged ethernet {1}\n".format(vlan, iface).splitlines()
                dual = "interface ethernet {1}\ndual-mode {0}\n".format(vlan, iface).splitlines()
                print("Configuring {0} for Vlan {1}".format(iface, vlan))
                library.send_command(*tag, chan=True, configure=True)
                library.send_command(*dual, chan=True, configure=True)

    # Loads Interface Index table
    print("Loading interface index")
    ifIndex = library.get(saved_data.community_string, ip.format(), 'IF-MIB', 'ifIndex')
    ifName = library.get(saved_data.community_string, ip.format(), 'IF-MIB', 'ifName')
    print("Interface index Loaded")

    # Initialize interface class
    print("Organizing interfaces")
    interfaces = {}
    for i in range(len(ifIndex[0])):
        interfaces[ifIndex[0][i]] = library.Interface(ifIndex[0][i], ifName[0][i])

    # Enabling PoE
    for intf in interfaces:
        library.send_command(interfaces[intf].command_name, 'inline power power-by-class 3', chan=chan, configure=True)

    # Writes memory
    print("Writing memory")
    library.send_command('write memory', configure=True, chan=chan)

    # Reboots Switch and waits 5 minutes to give enough time for POE devices to powerup
    print("Reloading switch")
    library.send_command('reload after 00:00:00', chan=chan)

    # Visual timer until reboot is done
    for t in range(300, -1, -5):
        minutes = t / 60
        seconds = t % 60
        print "%d:%2d  " % (minutes, seconds),
        time.sleep(5.0)

    # Reopens SSH connection
    print("Re-opening SSH Connection")
    chan, ssh = library.login(ip.format(), saved_data.username, saved_data.psk)

    # Activates IGMP snooping
    print("Enabling IGMP Snooping")
    library.send_command('ip multicast active', configure=True, chan=chan)

    # Activates DHCP snooping
    print("Enabling DHCP Snooping")
    for vlan_id in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        library.send_command('ip dhcp snooping vlan {0}'.format(str(vlan_id)), configure=True, chan=chan)

    # Enables Flow Control
    print("Enabling Flow Control")
    library.send_command('flow-control', chan=chan, configure=True)

    # Loads MAC-Table
    print("Loading MAC Table")
    cam_table = library.get(saved_data.community_string, ip.format(), 'BRIDGE-MIB', 'dot1dTpFdbPort')
    print("MAC Table Loaded")

    # Appends MAC addresses table to the interface class
    for i in range(len(cam_table[0])):
        mac = re.search(r'[0-9:a-fA-F]{17}', cam_table[1][i]).group()
        interfaces[cam_table[0][i]].mac_table.append(netaddr.EUI(mac))

    # Searches for live mac address and configures based on spreadsheet
    print("Searching interfaces for devices")
    for interface in sorted(interfaces):
        for mac in interfaces[interface].mac_table:
            for search in oui_discovery.items():
                try:
                    if mac.oui in search[1]:
                        if interfaces[interface].flag is 'switch':
                            continue
                        interfaces[interface].flag = search[0].lower()
                        print("Interface {0}: MAC {1}: Flag: {2}".format(interfaces[interface].ifName, str(mac),
                                                                         interfaces[interface].flag))
                except netaddr.NotRegisteredError:
                    pass

    # Configures Access Points
    print("Configuring Access Points")
    for interface in sorted(interfaces):
        if interfaces[interface].flag == 'Access_Points':
            library.send_command(interfaces[interface].command_name, 'port-name **** AP ****', chan=chan,
                                 configure=True)
            print("Configuring {0} for Vlan 50".format(interfaces[interface].command_name))
            library.send_command('vlan 50', 'tag {0}'.format(interfaces[interface].command_name), chan=chan,
                                 configure=True)
            library.send_command(interfaces[interface].command_name, 'no dual', 'dual 50', chan=chan, configure=True)

    if SEARCH:
        # Searches for live mac address and configures based on spreadsheet
        print("Searching interfaces for devices")
        for intf in sorted(interfaces):

            library.send_command('vlan 20 70', 'tag {0}'.format(interfaces[intf].command_name), configure=True,
                                 chan=chan)
            library.send_command(interfaces[intf].command_name, 'dual-mode 20', 'voice 70', configure=True, chan=chan)

            for mac in interfaces[intf].mac_table:
                for search in mac_per_vlan.items():
                    if mac in search[1]:

                        if '1/2/' in interfaces[intf].ifName:
                            continue
                        print("Match found {0} : {1} : VLAN {2}".format(interfaces[intf].ifName, mac, search[0]))

                        print("Configuring {0} for VLAN {1}".format(interfaces[intf].ifName, search[0]))

                        # tag port to vlans
                        interfaces[intf].vlan = int(search[0])

                        library.send_command('vlan {0} 70'.format(search[0]),
                                             'tag {0}'.format(interfaces[intf].command_name), configure=True, chan=chan)

                        # adds dual-mode for proper vlan
                        library.send_command(interfaces[intf].command_name, 'no dual',
                                             'dual-mode {0}'.format(search[0]), 'inline power power-b 3',
                                             configure=True, chan=chan)

    # Writes memory
    print("Writing memory")
    library.send_command('write memory', configure=True, chan=chan)
