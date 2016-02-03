#!/usr/bin/python
# Creates access yamls
import yaml
import json
from netaddr import IPAddress, IPNetwork, iter_iprange
import re
import sys
import os
from classes import Customer

# Main definition - constants
customer = object


# =======================
#     MENUS FUNCTIONS
# =======================
# Main menu
def main_menu():

    print "Please choose the menu you want to start:\n"
    print "1. New Site"
    # print "2. Load Site"
    print "0. Quit"
    choice = raw_input("Choice: ")
    exec_menu(choice)

    return


# Execute menu
def exec_menu(choice):
    ch = choice.lower()
    if ch == '':
        menu_actions['main_menu']()
    else:
        try:
            menu_actions[ch]()
        except KeyError:
            print "Invalid selection, please try again.\n"
            menu_actions['main_menu']()
    return


# Menu 1
def NewSite():
    iplist = []
    global customer
    customer = Customer(raw_input('Customer Name: ').upper())
    customer.community_string = raw_input('SNMP Community String: ')
    customer.username = raw_input('SSH/Telnet Username: ')
    customer.psk = raw_input('SSH/Telnet Pre-shared key: ')
    customer.enable = raw_input('Enable Password: ')
    customer.tftp = raw_input('TFTP Address: ')

    print '\nTarget Devices:\n' \
          '1. Single IP address (x.x.x.x)\n' \
          '2. IP file (Must be in working directory)\n' \
          '3. Subnet (x.x.x.x/y)\n' \
          '4. Network Range (x.x.x.x - y.y.y.y)\n'
    choice = int(raw_input('Choose an option: '))

    if choice == 1:
        arg = raw_input('IP Address (x.x.x.x): ')
        ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', arg)
        ip = IPAddress(ip[0])
        iplist.append(ip)

    if choice == 2:
        ip_file = raw_input('IP File name: ')
        with open(ip_file) as f:
            buff = f.read().splitlines()
        buff = ' '.join(buff)
        ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', buff)
        for i in ip: iplist.append(IPAddress(i))

    if choice == 3:
        network = raw_input('IP Network: ')
        subnet = IPNetwork(network)
        for ip in subnet:
            iplist.append(ip)

    if choice == 4:
        ip_range = raw_input('Network Range: ')
        ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', ip_range)
        iplist = list(iter_iprange(ip[0], ip[1]))

    customer.iplist = iplist

    print "0. Save"
    choice = raw_input("Choice")
    exec_menu(choice)
    return


# Menu 2
def LoadSite():
    print "Load Site\n"
    name = raw_input('Customer Name:').upper()
    if os.path.isfile("yamls\\%s.yml" % name):
        f = open("yamls\\%s.yml" % name)
        customer = yaml.load(f)
    print "9. Back"
    print "0. Quit"
    choice = raw_input(" >>  ")
    exec_menu(choice)
    return


# Back to main menu
def back():
    menu_actions['main_menu']()


# Exit program
def leave():
    f = open('yamls\\' + customer.name + '.yml', 'w+')
    yaml.dump(customer, f, default_flow_style=False)
    f.close()
    sys.exit()


# =======================
#    MENUS DEFINITIONS
# =======================

# Menu definition
menu_actions = {
    'main_menu': main_menu,
    '1': NewSite,
    '2': LoadSite,
    '9': back,
    '0': leave,
}

# =======================
#      MAIN PROGRAM
# =======================

# Main Program
if __name__ == "__main__":
    # Launch main menu
    main_menu()
