#!/usr/bin/python
import yaml
import re
from ciscoconfparse import CiscoConfParse
import time
from threading import Thread
import sys
import paramiko
import os

paramiko.util.log_to_file("paramiko.log")

# Loads saved data
if os.path.isfile('../access.yml'):
    with open('../access.yml', 'r') as stream:
        loaded_data = yaml.load(stream)
else:
    sys.exit('access.yml missing')


# Sends commands
def send_command(*commands, **kwargs):
    configure = kwargs.pop('configure', False)
    read = kwargs.pop('read', False)
    chan = kwargs.pop('chan', False)
    command = '\n'.join(commands)
    if configure:
        command = 'conf t\n' + command + '\n end\n'
    time.sleep(.25)
    chan.send(command + '\n')
    if read:
        time.sleep(5)
        recv = chan.recv(102400)
        return recv


# Connection Info
USERNAME = loaded_data['user_name']
PASSWORD = loaded_data['pre_shared_key']
IP = loaded_data['ip_addresses']


def login(ip, username, password):
    counter = 0
    while True:
        counter += 1
        try:
            # Opens SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password)
            chan = ssh.invoke_shell()
            time.sleep(1)
            return ssh, chan
        except paramiko.SSHException:
            if counter == 5:
                sys.exit('Failed to Connnect')
            continue


def standardize_configs(chan):
    output = send_command('enable', '!Tmgmt', 'skip', 'sh run', read=True, chan=chan)

    # Captures running config
    capture = re.findall(r'!\r\nver.*end', output, re.S).pop()

    # Parses running config
    output = CiscoConfParse(capture.splitlines())

    # Corrects DNS Setting
    x = output.find_lines(r'ip dns server-address.*')
    output.replace_lines(r'ip dns server-address.*', r'ip dns server-address 10.210.1.214 10.220.1.200')
    print('Correcting dns entry')
    send_command('no {0}'.format(x.pop()), 'ip dns server-address 10.210.1.214 10.220.1.200', configure=True, chan=chan)

    # Enables IGMP Snooping globally
    output.insert_after(r'hostname', r'ip multicast active')
    print('Enabling "ip multicast"')
    send_command('ip multicast active', configure=True, chan=chan)

    # Iterates through interfaces and cleans up misconfigurations
    for interface in output.find_objects(r'^interface.+'):
        has_loop_detection = interface.has_child_with(r'loop-detection')
        has_bpdu_guard = interface.has_child_with(r'stp-bpdu-guard')
        has_root_protection = interface.has_child_with(r'spanning-tree\sroot-protect')
        has_no_flow_control = interface.has_child_with(r'no\sflow-control')
        is_layer3_intf = (interface.has_child_with(r'ip\s+add')) or ('interface ve.*' in interface.text)

        # Temporarily disabled
        #
        # # Remove loop-detection misconfiguration
        # if has_loop_detection and has_bpdu_guard:
        #     interface.delete_children_matching('loop-detection')
        #     print('Removing "loop-detection" from {0}'.format(interface.text))
        #     send_command(interface.text, 'no loop-detection', configure=True)
        #
        # # Remove spanning-tree root-protect misconfiguration
        # if has_root_protection:
        #     interface.delete_children_matching(r'spanning-tree\sroot-protect')
        #     print('Removing "spanning-tree root-protect" from {0}'.format(interface.text))
        #     send_command(interface.text, 'no spanning-tree root', configure=True)

        # Adds IGMP snooping and QoS to Layer 3 interfaces
        if is_layer3_intf and not ('loopback' in interface.text or 'management' in interface.text):
            interface.append_to_family(r' trust dscp')
            print('Adding "trust dscp" to {0}'.format(interface.text))
            send_command(interface.text, 'trust dscp', configure=True, chan=chan)
            interface.append_to_family(r' ip igmp version 2')
            print('Adding "ip igmp version 2" to {0}'.format(interface.text))
            send_command(interface.text, 'ip igmp version 2', configure=True, chan=chan)

        # # enables flow-control
        # if has_no_flow_control:
        #     interface.delete_children_matching(r'no\sflow-control.+')
        #     print('Enabling "flow-control" on {0}'.format(interface.text))
        #     send_command(interface.text, 'flow-control', configure=True, chan=chan)
    return output


def do_stuff():
    for ip in IP:
        ssh, channel = login(ip, USERNAME, PASSWORD)
        output = standardize_configs(chan=channel)
        # Saves configuration backup
        output.commit()
        output.save_as('test_config.cfg')
        # Closes the connection
        print('Closing SSH to {0}'.format(ip))
        ssh.close()


thread = Thread(target=do_stuff)
threads = []
counter = 0
t = {}
for i in range(len(IP)):
    counter += 1
    t[IP[i]] = thread
    if counter == 20:
        t[IP[i]].join()
        counter = 0
    threads.append(t[IP[i]])
    t[IP[i]].start()
