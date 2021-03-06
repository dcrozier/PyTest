import paramiko
import time
import re
import socket
from ciscoconfparse import CiscoConfParse

paramiko.util.log_to_file("logs\\paramiko.log")


class Verify(object):
    def __init__(self, conf, chan):
        self.chan = chan
        self.conf = conf
        self.before = send_command('show run {0}'.format(self.conf[0]), chan=self.chan, read=True)
        self.after = ''

    def download_after(self):
        self.chan.recv(5000)
        self.after = send_command('show run {0}'.format(self.conf[0]), chan=self.chan, read=True)

    def get_before(self):
        return CiscoConfParse(self.before.splitlines()[1:-1])

    def get_after(self):
        return CiscoConfParse(self.after.splitlines()[1:-1])


# Sends commands
def send_command(*commands, **kwargs):
    """
    :param commands: Commands to send to device
    :param kwargs: read / config flags
    :return: comand output if read flag is set
    """
    configure = kwargs.pop('configure', False)
    read = kwargs.pop('read', False)
    chan = kwargs.pop('chan', False)
    verify = kwargs.pop('verify', False)
    command = '\n'.join(commands)
    if verify:
        verifier = Verify(command.splitlines(), chan)
    if configure:
        command = 'conf t\n' + command + '\n end\n'
    chan.send(command + '\n')
    time.sleep(.5)
    if read:
        time.sleep(1)
        recv = chan.recv(65535)
        return recv
    if verify:
        verifier.download_after()
        before = verifier.get_before()
        after = verifier.get_after()
        for line in after.find_all_children(r'.*'):
            if line not in before.find_all_children(r'.*'):
                print line
        print()
    chan.recv(65535)


def get_running_config(chan, enable_password):
    """
    captures the running config
    :param chan: ssh channel
    :param enable_password: enable password
    :return: running config
    """

    # sends 'show running-config' to device
    running_config = send_command('skip', 'sh run', read=True, chan=chan)

    time.sleep(2)
    # Capture only running config data
    running_config = re.findall(r'!\r\nver.*end', running_config, re.S).pop()

    # Parses config
    running_config = CiscoConfParse(running_config.splitlines())

    print("Download complete")

    return running_config


def login(ip, username, password):
    """
    Logs into the device
    :param ip: ip address
    :param username: username
    :param password: pre-shared key
    :return: ssh connection channel
    """
    counter = 0
    while True:
        counter += 1
        try:
            # Opens SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password, look_for_keys=False, allow_agent=True)
            chan = ssh.invoke_shell()
            time.sleep(.25)
            if '>' in chan.recv(5000):
                send_command('enable', username, password, chan=chan)
            return chan, ssh
        except socket.error:
            return 0, 0
        except paramiko.ssh_exception.SSHException:
            if counter == 3:
                return 0, 0
            continue
