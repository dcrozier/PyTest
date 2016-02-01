
class Interface(object):
    def __init__(self, ifIndex, ifName):
        self.ifName = ifName
        self.ifIndex = ifIndex
        self.mac_table = []
        self.flag = 0
