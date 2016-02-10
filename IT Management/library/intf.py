# Profile for interfaces


class Interface(object):
    def __init__(self, index, name):
        self.ifName = name
        self.ifIndex = index
        self.mac_table = []
        self.flag = None
        self.command_name = 'interface {0}'.format(' '.join([self.ifName[:8], self.ifName[8:]]))
