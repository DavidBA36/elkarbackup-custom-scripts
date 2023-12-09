#!/usr/bin/env python3
import json
import mysql.connector
import paramiko
import helpers

key = paramiko.RSAKey.from_private_key_file("/var/lib/elkarbackup/.ssh/id_rsa")
client = paramiko.SSHClient()
logger = helpers.get_logger(__name__)


def main():
    global client
    try:
        db = mysql.connector.connect(host="localhost", user="backup", passwd="1q2w3e4r",
                                     database="BackupExterno", autocommit=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute('select * from config')
        result = cursor.fetchone()
        if result is not None:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=result['DOM0'], username=result['USER'], pkey=key)
            stdin, stdout, stderr = client.exec_command('ls /etc/xen/auto/')
            machines = stdout.read().decode('utf-8').rstrip().split('\n')
            if len(machines) == 0:
                exit(1)
            lista = []
            for machine in machines:
                stdin, stdout, stderr = client.exec_command("xl list -l " + machine)
                vm = json.loads(stdout.read().decode('utf-8').rstrip())
                if vm is not None:
                    lista.extend([{'nombre': machine, 'discos': vm[0]['config']['disks']}])
                else:
                    exit(1)
            json_dump = json.dumps(lista)
            print(json_dump)
            exit(0)
    except Exception as e:
        print(e)
        exit(1)


if __name__ == '__main__':
    main()
