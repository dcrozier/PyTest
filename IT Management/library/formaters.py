import re


def format_mac(mac):
    if not mac:
        return '0000.0000.0000'
    mac = re.sub('[.:-]', '', mac).lower().split()  # remove delimiters and convert to lower case
    mac = ''.join(mac.pop(0).split())  # remove whitespaces

    try:
        assert len(mac) == 12  # length should be now exactly 12 (eg. 008041aefd7e)
    except AssertionError:
        print("Invalid MAC: '{0}' Ignoring".format(mac))
        return '0000.0000.0000'
    assert mac.isalnum()  # should only contain letters and numbers
    # convert mac in canonical form (eg. 00:80:41:ae:fd:7e)
    mac = ":".join(["%s" % (mac[i:i+2]) for i in range(0, 12, 2)])
    return mac

