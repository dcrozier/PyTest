# Profile for interfaces


class Interface(object):
    def __init__(self, index, name):
        self.ifName = name
        self.ifIndex = index
        self.mac_table = []
        self.flag = 0
