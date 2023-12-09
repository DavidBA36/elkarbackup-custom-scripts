#!/usr/bin/env python3
import json
import os
import re
import logging
import paramiko


key = paramiko.RSAKey.from_private_key_file("/var/lib/elkarbackup/.ssh/id_rsa")
client = paramiko.SSHClient()
devices = ['hda','sda', 'xvda', 'xvdb']

def get_logger(name):
	alogger = logging.getLogger(name)
	hdlr = logging.FileHandler('/var/log/backup/xenvms.log')
	formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
	hdlr.setFormatter(formatter)
	alogger.addHandler(hdlr)
	alogger.setLevel(logging.DEBUG)
	return alogger
	
logger = get_logger(__name__)


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
	
def find_mapper_parent(mapper_device):
	global client
	stdin, stdout, stderr = client.exec_command('dmsetup deps -o devname {}'.format(mapper_device))
	result = stdout.read().decode('utf-8').rstrip()
	match = re.match(r".*\((.*)-(.*)\)", result)
	if match is not None and len(match.groups()) > 0:
		return match.group(1), match.group(2)
	return None
	
	
def ssh_cmd(cmd):
	global client
	stdin, stdout, stderr = client.exec_command(cmd)
	return True if stdout.channel.recv_exit_status() == 0 else False


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
			print('Conecting to: {} with user {}'.format(host, user))
			client.connect(hostname=host, username=user, pkey=key)
			stdin, stdout, stderr = client.exec_command('ls /etc/xen/auto/')
			machines = stdout.read().decode('utf-8').rstrip().split('\n')
			if len(machines) == 0:
				print('No hay maquinas en auto')
				exit(1)
			for machine in machines:
				stdin, stdout, stderr = client.exec_command("xl list -l " + machine)
				vm = json.loads(stdout.read().decode('utf-8').rstrip())
				if vm is not None:
					print('Procesando '+machine)
					pydev = None
					print(vm[0]['config']['disks'])
					for disk in vm[0]['config']['disks']:
						logger.debug("Comprobando " + disk.get('vdev'))
						if disk.get('vdev') in devices:
							pydev = disk['pdev_path']
							if pydev is not None:
								ruta_volumen = pydev
								nombre_vol = pydev.split('/')[3]
								print('Analizando disco virtual...'+ruta_volumen)
								logger.debug("Analizando disco virtual " +ruta_volumen)
								if 'mapper' in pydev:  # hay que localizar a que volumen pertenece este mapper
									grupo,  nombre_vol = find_mapper_parent(pydev)
									ruta_volumen = '/dev/{}/{}'.format(grupo, nombre_vol)
								
								print('Verficando la existencia de un snapshot volumen primario')
								if ssh_cmd('lvs | grep {}_snapshot'.format(nombre_vol)):
									if not ssh_cmd('lvremove -f {}_snapshot'.format(ruta_volumen)):
										print('no se ha podido borrar el volumen')
										exit(1)
								print('Crendo snapshot del volumen primario')
								if not ssh_cmd('lvcreate -s -n {}_snapshot -L 10G {}'.format(nombre_vol, ruta_volumen)):
									print('no se ha podido crear el volumen')
									exit(1)
								print('Volcando datos y comprimiendo snapshot')
								if not ssh_cmd('dd if={}_snapshot conv=sync,noerror bs=64K | gzip -c > /backup/images/{}.img.gz'.format(ruta_volumen, nombre_vol)):
									print('no se ha podido volcar el volumen')
									exit(1)
								print('borrando snapshot')
								if not ssh_cmd('lvremove -f {}_snapshot'.format(ruta_volumen)):
									print('no se ha podido borrar el volumen')
									exit(1)
								
							else:
								print('No se han encontrado discos')
								logger.debug("No se han encontrado discos")
								exit(1)
				else:
					print('la maquina ' + machine + 'no esta disponible')
					logger.debug('la maquina ' + machine + 'no esta disponible')
			exit(0)
		else:
			print('Solo permitido antes de ejecutar la tarea')
			exit(1)
	except Exception as e:
		logger.debug(e)
		print(e)
		exit(1)


if __name__ == '__main__':
	main()
