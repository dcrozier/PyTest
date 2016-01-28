#!/usr/bin/python
import yaml
import re
from ciscoconfparse import CiscoConfParse
import time
import paramiko

username = 'itmgmt'
password = '!QAZ2wsx'
ip = '10.141.0.1'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ip, username=username, password=password)

chan = ssh.invoke_shell()
list = ['enable', username, password, 'skip', 'sh run']
command = '\n'.join(list)
chan.send(command + '\n')

# time.sleep(5)

while not chan.recv_ready(): time.sleep(1)
output = chan.recv(102400)
output = re.findall(r'!\r\nver.*end', output, re.S).pop()
output = CiscoConfParse(output.splitlines())

for interface in output.find_objects(r'^interface.+'):
    has_loop_detection = interface.has_child_with(r'\sloop-detection')
    has_root_protection = interface.has_child_with(r'spanning-tree\sroot-protect')
    has_no_flow_control = interface.has_child_with(r'no\sflow-control')
    is_layer3_intf = interface.has_child_with(r'\s+ip\s+add.*')

    ## Remove loop-detection misconfiguration
    if has_loop_detection:
        interface.delete_children_matching('loop-detection')

    ## Remove spanning-tree root-protect misconfiguration
    if has_root_protection:
        interface.delete_children_matching(r'spanning-tree\sroot-protect')

    if is_layer3_intf and not ('loopback' in interface.text):
        interface.append_to_family(r' trust dscp')
        interface.append_to_family(r' ip igmp version 3')

    ## enables flow-control
    if has_no_flow_control:
        interface.delete_children_matching(r'no\sflow-control.+')

## Remove loop-detection misconfigurations
output.delete_lines(r'loop-detection')
output.delete_lines(r'errdisable recovery cause loop-detect')
output.delete_lines(r'errdisable recovery cause all')
output.replace_lines(r'ip dns server-address.*', r'ip dns server-address 10.210.1.214 10.220.1.200')
output.insert_after(r'hostname', r'ip multicast active')

if output.has_line_with('boot sys fl sec'):
    chan.send('sh fl\n')
    while not chan.recv_ready(): time.sleep(1)
    response = chan.recv(1024)
    x = re.findall('([0-9a-z]+.bin)', response, re.IGNORECASE)
    if x[0] == x[1]:
        output.delete_lines(r'boot sys fl sec')


output.commit()
output.save_as('test_config.cfg')
ssh.close()
print(output)
