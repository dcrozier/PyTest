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
if not os.path.isfile('yamls\\{0}.yml'.format(SITE)):
    sys.exit('Site not setup, run setup_site.py')

# Checks for mac address csv
if not os.path.isfile('csv\\{0}.csv'.format(SITE)):
    sys.exit('MAC address csv missing')

# Loads access info
with open('yamls\\{0}.yml'.format(SITE), 'r+') as f:
    saved_data = yaml.load(f)

for ip in saved_data.iplist:

    # Opens SSH connection
    print("Opening SSH connection")
    chan, ssh = library.login(ip.format(), saved_data.username, saved_data.psk)

    # Updates Boot Rom and waits for startup
    print("Loading boot loader")
    library.send_command('copy tftp flash {0} 08030d/ICX7450/Boot/spz10105.bin boot'.format(saved_data.tftp), chan=chan)

    # Visual timer to wait for boot rom to finish loading
    for t in range(30, -1, -5):
        minutes = t / 60
        seconds = t % 60
        print "%d:%2d" % (minutes, seconds)
        time.sleep(5.0)

    # Removes vlan 24 & 26
    print("Removing vlan 24 and 26")
    library.send_command('no vlan 24', 'no vlan 26', configure=True, chan=chan)

    # Adds vlan 20
    print("Adding vlan 20")
    library.send_command('vlan 20 name Servers&Printers', 'tag e 1/2/1', 'tag e 1/3/1', 'span 80', configure=True,
                         chan=chan)

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

    # Download running config
    print("Downloading running config")
    running_config = library.get_running_config(chan, saved_data.enable)

    # Activates IGMP snooping
    print("Enabling IGMP Snooping")
    library.send_command('ip multicast active', configure=True, chan=chan)

    # Activates DHCP snooping
    print("Enabling DHCP Snooping")
    for vlan_id in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        library.send_command('ip dhcp snooping vlan {0}'.format(str(vlan_id)), configure=True, chan=chan)

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

    # Reads mac to vlan spreadsheet for existing network
    print("Loading MAC address to search for")
    mac_per_vlan = defaultdict(list)
    with open('csv\\{0}.csv'.format(SITE), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key in row.keys():
                mac_per_vlan[key].append(netaddr.EUI(library.format_mac(row[key])))

    # Searches for live mac address and configures based on spreadsheet
    print("Searching interfaces for devices")
    for intf in sorted(interfaces):
        for mac in interfaces[intf].mac_table:
            for search in mac_per_vlan.items():
                if mac in search[1]:
                    print("Match found {0} : {1} : VLAN {2}".format(interfaces[intf].ifName, mac, search[0]))
                    interface_line = running_config.find_objects(
                        r'interface {0}'.format(
                            map(lambda string: string[:8] + ' ' + string[8:], [interfaces[intf].ifName])[0]
                        ),
                        exactmatch=True
                    )

                    print("Configuring {0} for VLAN {1}".format(interfaces[intf].ifName, search[0]))

                    # tag port to vlans
                    library.send_command('vlan {1} 70', 'tag {0}'.format(
                        map(lambda string: string[:8] + ' ' + string[8:], [interfaces[intf].ifName])[0], search[0]),
                                         configure=True, chan=chan)

                    # adds dual-mode for proper vlan
                    library.send_command(interface_line[0].text, 'dual-mode {0}'.format(search[0]),
                                         configure=True, chan=chan)

    # Writes memory
    print("Writing memory")
    library.send_command('write memory', configure=True, chan=chan)