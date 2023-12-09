#!/usr/bin/env python3

import os
import paramiko


sysinfo = '/backup/dom0/sys_info'
xenconfig = '/backup/dom0/xenconfig.gz'
key = paramiko.RSAKey.from_private_key_file("/var/lib/elkarbackup/.ssh/id_rsa")
client = paramiko.SSHClient()


def get_env_vars():
	env = {
		'level': str(os.environ.get('ELKARBACKUP_LEVEL')),
		'event': str(os.environ.get('ELKARBACKUP_EVENT')),
		'url': str(os.environ.get('ELKARBACKUP_URL')),
		'id': str(os.environ.get('ELKARBACKUP_ID')),
		'path': str(os.environ.get('ELKARBACKUP_PATH')),
		'status': str(os.environ.get('ELKARBACKUP_STATUS')),
		'client-name': str(os.environ.get('ELKARBACKUP_CLIENT_NAME')),
		'job-name': str(os.environ.get('ELKARBACKUP_JOB_NAME')),
		'owner-email': str(os.environ.get('ELKARBACKUP_OWNER_EMAIL')),
		'recipient-list': str(os.environ.get('ELKARBACKUP_RECIPIENT_LIST')),
		'client-total-size': str(os.environ.get('ELKARBACKUP_CLIENT_TOTAL_SIZE')),
		'job-total-size': str(os.environ.get('ELKARBACKUP_JOB_TOTAL_SIZE')),
		'job-run-size': str(os.environ.get('ELKARBACKUP_JOB_RUN_SIZE')),
		'client-start-time': str(os.environ.get('ELKARBACKUP_CLIENT_STARTTIME')),
		'client-end-time': str(os.environ.get('ELKARBACKUP_CLIENT_ENDTIME')),
		'job-start-time': str(os.environ.get('ELKARBACKUP_JOB_STARTTIME')),
		'job-end-time': str(os.environ.get('ELKARBACKUP_JOB_ENDTIME')),
		'user': str(os.environ.get('USER'))
	}
	return env


def ssh_cmd(cmd):
	global client
	stdin, stdout, stderr = client.exec_command(cmd)
	stdout.channel.recv_exit_status()


def main():
	global client
	try:
		elkarbackup = get_env_vars()
		if elkarbackup.get('level') != 'JOB':
			print('Solo permitido a nivel de tarea')
			exit(1)
		if elkarbackup.get('event') == 'PRE':
			client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			user, host = elkarbackup.get('url').split('@')
			host = host.split(':')[0]
			client.connect(hostname=host, username=user, pkey=key)
			# Lista todos los grupos lógicos
			ssh_cmd('echo  "#########################" > {sysinfo}'.format(sysinfo=sysinfo))
			ssh_cmd('echo  "####Listado de Grupos####" >> {sysinfo}'.format(sysinfo=sysinfo))
			ssh_cmd('echo -e "#########################\n" >> {sysinfo}'.format(sysinfo=sysinfo))
			ssh_cmd('vgs >> {sysinfo}'.format(sysinfo=sysinfo))
			# Lista todos los volúmenes lógicos
			ssh_cmd('echo -e  "\n############################" >> {sysinfo}'.format(sysinfo=sysinfo))
			ssh_cmd('echo  "####Listado de Volumenes####" >> {sysinfo}'.format(sysinfo=sysinfo))
			ssh_cmd('echo -e  "############################\n" >> {sysinfo}'.format(sysinfo=sysinfo))
			ssh_cmd('lvs >> {sysinfo}'.format(sysinfo=sysinfo))
			# Lista todas las máquinas virtuales
			ssh_cmd('echo -e "\n###########################" >> {sysinfo}'.format(sysinfo=sysinfo))
			ssh_cmd('echo  "####Listado de Maquinas####" >> {sysinfo}'.format(sysinfo=sysinfo))
			ssh_cmd('echo -e  "###########################\n" >> {sysinfo}'.format(sysinfo=sysinfo))
			ssh_cmd('xl list >> {sysinfo}'.format(sysinfo=sysinfo))
			# Hace una copia de la carpeta /etc/xen y la comprime
			ssh_cmd('tar cf - "/etc/xen" | gzip > {xenconfig}'.format(xenconfig=xenconfig))
			exit(0)
		else:
			print('Solo permitido antes de ejecutar la tarea')
			exit(1)
	except Exception as e:
		print(e)
		exit(1)


if __name__ == '__main__':
	main()
