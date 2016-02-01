import paramiko
import time
import sys

paramiko.util.log_to_file("paramiko.log")


# Sends commands
def send_command(*commands, **kwargs):
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


def login(ip, username, password):
    counter = 0
    while True:
        counter += 1
        try:
            # Opens SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password)
            chan = ssh.invoke_shell()
            time.sleep(1)
            return ssh, chan
        except paramiko.SSHException:
            if counter == 5:
                sys.exit('Failed to Connnect')
            continue
