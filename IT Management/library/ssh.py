import paramiko
import time
import socket

paramiko.util.log_to_file("logs\\paramiko.log")


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
    command = '\n'.join(commands)
    if configure:
        command = 'conf t\n' + command + '\n end\n'
    time.sleep(.25)
    chan.send(command + '\n')
    if read:
        time.sleep(5)
        recv = chan.recv(102400)
        return recv


def get_running_config(chan, enable_password):
    """
    captures the running config
    :param chan: ssh channel
    :param enable_password: enable password
    :return: running config
    """
    from ciscoconfparse import CiscoConfParse
    import re

    # sends 'show running-config' to device
    running_config = send_command('enable', enable_password, 'skip', 'sh run', read=True, chan=chan)

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
            ssh.connect(ip, username=username, password=password)
            chan = ssh.invoke_shell()
            time.sleep(2)
            return chan, ssh
        except socket.error:
            return 0, 0
        except paramiko.ssh_exception.SSHException:
            if counter == 3:
                return 0, 0
            continue
