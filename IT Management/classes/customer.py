# Profile for customer site


class Customer(object):
    def __init__(self, name):
        self.name = name
        self.community_string = ''
        self.iplist = []
        self.username = ''
        self.psk = ''
        self.enable = ''
        self.tftp = ''
