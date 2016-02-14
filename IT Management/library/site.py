# Profile for customer site

class Site(object):
    def __init__(self, name):
        self.name = name
        self.community_string = ''
        self.iplist = []
        self.username = ''
        self.psk = ''
        self.enable = ''
        self.tftp = ''
        self.core_template = name + '-VLANs.csv'
        self.port_map = name + '-Ports.csv'
        self.mac = name + '-MAC.csv'
