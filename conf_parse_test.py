#!/usr/bin/python

from ciscoconfparse import CiscoConfParse
import yaml


def standardize_intfs(parse):
    data_vlan = list()
    voice_vlan = list()
    facilitys_vlan = list()
    wifi_vlans = list()
    unknown_ports = list()

    ## Search all switch interfaces and modify them
    # r'^interface.+?thernet' is a regular expression, for ethernet intfs
    for intf in parse.find_objects(r'^interface.+'):

        has_loop_detection = intf.has_child_with(r'\sloop-detection')
        has_root_protection = intf.has_child_with(r'spanning-tree\sroot-protect')
        has_no_flow_control = intf.has_child_with(r'no\sflow-control')
        has_access_point_configuration = intf.has_child_with(r'\sdual-mode\s+11')
        has_hvac_configuration = intf.has_child_with(r'\sdual-mode\s+24')
        has_data_port_configuration = intf.has_child_with(r'\sdual-mode\s+42')
        is_layer3_intf = intf.has_child_with(r'\s+ip\s+add.*')

        ## Remove loop-detection misconfiguration
        if has_loop_detection:
            intf.delete_children_matching('loop-detection')

        ## Remove spanning-tree root-protect misconfiguration
        if has_root_protection:
            intf.delete_children_matching(r'spanning-tree\sroot-protect')

        if is_layer3_intf:
            intf.append_to_family(r' trust dscp')

        ## enables flow-control
        if has_no_flow_control:
            intf.delete_children_matching(r'no\sflow-control.+')

        ## Names AP uplink ports
        if has_access_point_configuration:
            intf.delete_children_matching(r'port-name')
            intf.append_to_family(' port-name AP')
            wifi_vlans.append(intf)
            data_vlan.append(intf)

        elif has_hvac_configuration:
            facilitys_vlan.append(intf)

        elif has_data_port_configuration:
            voice_vlan.append(intf)
            data_vlan.append(intf)

        else:
            unknown_ports.append(intf)

    for lldp in parse.find_objects(r'^lldp'):
        ## Remove LLDP misconfiguration
        if lldp.text == 'lldp run':
            pass
        else:
            lldp.delete()

    ## Remove loop-detection misconfigurations
    parse.delete_lines(r'loop-detection')
    parse.delete_lines(r'errdisable recovery cause loop-detect')
    parse.delete_lines(r'errdisable recovery cause all')

    ## Cleans up vlan configuraiton.
    vlans = [
        ('11', wifi_vlans),
        ('22', voice_vlan),
        ('24', facilitys_vlan),
        ('42', data_vlan),
        ('56', wifi_vlans)
    ]
    tagged_ports = lambda vlan: parse.replace_children(
        r'vlan\s+{0}'.format(vlan[0]), r'!', 'tagged ' + ' '.join([port_name(port) for port in sorted(vlan[1])])
    )
    port_name = lambda port: ' '.join([port.text[10:11], port.text[19:]])
    parse.replace_all_children(r'vlan.*', r'[un]?tagged.*', '!')
    for x in vlans: tagged_ports(x)
    # parse.replace_all_children(r'vlan.*', r'REPLACE', '')


## Parse the config
parse = CiscoConfParse('brocade_conf.cfg')

## Search and standardize the configuration
standardize_intfs(parse)
parse.commit()  # commit() **must** be called before searching again

## Write the new configuration
parse.save_as('brocade_conf.cfg.new')
