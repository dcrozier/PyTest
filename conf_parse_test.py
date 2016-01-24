#!/usr/bin/python

from ciscoconfparse import CiscoConfParse

def standardize_intfs(parse):

    data_vlan = list()
    facilitys_vlan = list()
    wifi_vlans = list()
    unknown_ports = list()

    ## Search all switch interfaces and modify them
    # r'^interface.+?thernet' is a regular expression, for ethernet intfs
    for intf in parse.find_objects(r'^interface.+?thernet'):

        has_loop_detection = intf.has_child_with(r'\sloop-detection')
        has_root_protection = intf.has_child_with(r'spanning-tree\sroot-protect')
        has_no_flow_control = intf.has_child_with(r'no\sflow-control')
        has_access_point_configuration = intf.has_child_with(r'\sdual-mode\s+11')
        has_hvac_configuration = intf.has_child_with(r'\sdual-mode\s+24')
        has_data_port_configuration = intf.has_child_with(r'\sdual-mode\s+42')

        ## Remove loop-detection misconfiguration
        if has_loop_detection:
            intf.delete_children_matching('loop-detection')

        ## Remove spanning-tree root-protect misconfiguration
        if has_root_protection:
            intf.delete_children_matching(r'spanning-tree\sroot-protect')

        ## enables flow-control
        if has_no_flow_control:
            intf.delete_children_matching(r'no\sflow-control.+')

        ## Names AP uplink ports
        if has_access_point_configuration:
            intf.delete_children_matching(r'port-name')
            intf.append_to_family(' port-name AP')
            wifi_vlans.append(intf)

        elif has_hvac_configuration:
            facilitys_vlan.append(intf)

        elif has_data_port_configuration:
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

    ## Cleans up the vlan configuration
    for vlan in parse.find_objects(r'^vlan\s\d+\s.+'):
        if ('11' in vlan.text) or ('41' in vlan.text) or ('56' in vlan.text):
            parse.replace_children(vlan.text, r' tagged.*', ' tagged {0}'.format(' '.join([port.text[10:] for port in wifi_vlans])))
        elif '24' in vlan.text:
            parse.replace_children(vlan.text, r' tagged.*', ' untagged {0}'.format(' '.join([port.text[10:] for port in facilitys_vlan])))
        elif ('41' in vlan.text) or ('22' in vlan.text):
            parse.replace_children(vlan.text, r' tagged.*', ' tagged {0}'.format(' '.join([port.text[10:] for port in data_vlan])))

        else:
            vlan.delete_children_matching(r' tagged')

## Parse the config
parse = CiscoConfParse('brocade_conf.cfg')

## Search and standardize the configuration
standardize_intfs(parse)
parse.commit()     # commit() **must** be called before searching again

## Write the new configuration
parse.save_as('brocade_conf.cfg.new')

