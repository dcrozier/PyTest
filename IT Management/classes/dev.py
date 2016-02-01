# Profile for device switch/router


class Device(object):
    def __init__(self, ip, host):
        self.ip_address = ip
        self.name = host
        self.interfaces = []