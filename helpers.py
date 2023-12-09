import base64
import datetime
import email
import json
import logging
import math
import os
import re
import signal
import smtplib
import time
import paramiko
import dialog
from email.message import EmailMessage
from stat import ST_MTIME
import requests
import sh
from filelock import Timeout
from sh import rsync, umount, mount, cryptsetup, ps, df, lsblk, smartctl, grep, awk
from resources import *


def get_logger(name):
	alogger = logging.getLogger(name)
	hdlr = logging.FileHandler('/var/log/backup_externo')
	formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
	hdlr.setFormatter(formatter)
	alogger.addHandler(hdlr)
	alogger.setLevel(logging.DEBUG)
	return alogger

version ="Version 2.0.1.7 2023"
logger = get_logger(__name__)


def crea_cuerpo_copia_ok(datos):
	s = 'Se ha realizado la copia externa en {trans} en el dispositivo con el numero de serie {serie} ' \
		'SE PUEDE CAMBIAR LA COPIA. <p>' \
		'<TABLE border="1">' \
		'<CAPTION><EM>Informaci&oacute;n de los discos</EM></CAPTION>' \
		'<TR><TR><TH><TH>Interno<TH>Externo' \
		'<TR><TH align="left">Espacio Total<TD>{internal_size}<TD>{external_size}' \
		'<TR><TH align="left">Espacio Usado<TD>{internal_used}<TD>{external_used}' \
		'<TR><TH align="left">Espacio Disponible<TD>{internal_free}<TD>{external_free}' \
		'<TR><TH align="left">Integridad<TD>{internal_integrity}<TD>{external_integrity}</TABLE><TABLE border="1">' \
		'<CAPTION><EM>Informaci&oacute;n de los volumenes</EM></CAPTION><TR>' \
		'<TR><TH>Volumen<TH>Size<TH>Used<TH>Free{volumenes}</TABLE> ' \
		'<br>Advertencias o errores: <br>. {advertencias}' \
		.format(trans=datos['transcurrido'],
				serie=datos['serie'],
				internal_size=datos['isize'],
				internal_used=datos['iused'],
				internal_free=datos['ifree'],
				external_size=datos['esize'],
				external_used=datos['eused'],
				external_free=datos['efree'],
				internal_integrity=datos['internal_smart'],
				external_integrity=datos['external_smart'],
				volumenes='\n'.join(datos['volumenes']),
				advertencias='<br>.\n'.join(datos['advertencias']))
	return s


def crea_cuerpo_update(version,news):
	s = 'Se ha actualizado la aplicación a la versión '+version +'<br>'+news
	return s

def parse(file_object, config_path):
	try:
		return json.load(file_object)
	except ValueError:
		file_object.seek(0)
		json.dump([], file_object, indent=4)
		file_object.truncate()
		tmp = open(config_path, 'r+')
		return json.load(tmp)


def leer_fichero(lock, config_path, template):
	try:
		with lock.acquire(timeout=10):
			if not os.path.exists(config_path):
				with open(config_path, 'w') as config:
					config.seek(0)
					json.dump(template, config, indent=2)
					config.truncate()
			with open(config_path, 'r') as config:
				datos = parse(config, config_path)
			return datos
	except Timeout:
		log(logger, logging.FATAL, "Otra instancia esta bloqueando el fichero")
	finally:
		lock.release()


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


def formato(device):
	try:
		mkfs_xfs = sh.Command("mkfs.xfs")
		mkfs_xfs(device)
		return True
	except Exception as e:
		log(logger, logging.FATAL, "error al formatear el dipositivo {}".format(device), e)
		return False


def is_luks(device):
	try:
		cryptsetup('isLuks', device)
		return True
	except sh.ErrorReturnCode_4:
		if existe_disco(device):
			log(logger, logging.FATAL, "El acceso al disco {} ha sido denegado.".format(device))
		else:
			log(logger, logging.FATAL,
				"El dispositivo {} no existe o el acceso al mismo ha sido denegado.".format(device))
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return False


def umount_disk(path):
	try:
		log(logger, logging.INFO, "Desmontando particion cifrada ...")
		if os.path.ismount(path):
			umount(path)
			if os.path.ismount(path):
				return False
		return True
	except sh.ErrorReturnCode_32:
		log(logger, logging.FATAL, "El punto de montaje {} no existe".format(path))
		return False
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return False


def monta_disco(device, path):
	try:
		if not os.path.ismount(path):
			mount(device, path)
			if os.path.ismount(path):
				return True
		else:
			return True
		return False
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return False


def luks_abre_canal(device, channel, password):
	try:
		log(logger, logging.INFO, "Abriendo el canal cifrado...")
		cryptsetup('luksOpen', device, channel, _in=password)
		return True
	except sh.ErrorReturnCode_5:
		log(logger, logging.WARNING, "El canal ya estaba abierto")
		return True
	except Exception as e:
		log(logger, logging.FATAL, "no se ha podido al abrir el canal cifrado", e)
		return False


def luks_cierra_canal(channel):
	try:
		if existe_disco('/dev/mapper/backup-externo'):
			cryptsetup('luksClose', channel)
		return True
	except Exception as e:
		log(logger, logging.FATAL, "No se ha podido liberar el canal cifrado", e)
		return False


def luks_formatea(device, password):
	try:
		log(logger, logging.INFO, "Formateando canal cifrado...")
		cryptsetup('luksFormat', device, _in=password)
		return True
	except Exception as e:
		log(logger, logging.FATAL, "no se ha podido crear el canal cifrado", e)
		return False


def luks_uuid(device):
	try:
		return cryptsetup('luksUUID', device).rstrip().replace('-', '')
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return ''


def is_luks_device_open(device):
	uuid = luks_uuid(device)
	if luks_uuid(device) != '':
		for file in os.listdir('/dev/disk/by-id/'):
			if file.find(uuid) != -1:
				return True
	return False


def is_dev_attached(dom0, domain, front_device):
	try:
		cmd = "xl list -l "+domain
		stdin, stdout, stderr = dom0.exec_command(cmd)
		vm = json.loads(stdout.read().decode('utf-8').rstrip())
		if vm is not None:
			for disk in (vm[0]['config']['disks']):
				if disk['vdev'] == front_device:
					return True
		return False
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return False


def dom0_detach_disk(dom0, domain, front_device):
	try:
		if is_dev_attached(dom0, domain, front_device):
			log(logger, logging.INFO, 'desvinculando disco {} de la maquina virtual'.format(front_device))
			cmd = "xl block-detach {} {} ".format(domain, front_device)
			stdin,  stdout, stderr = dom0.exec_command(cmd)
			stdout.channel.recv_exit_status()
			log(logger, logging.INFO, 'disco desvinculando con exito')
		return True
	except Exception as e:
		log(logger, logging.FATAL, msg_e_disco_no_vinculado, e)
		return False


def dom0_attach_disk(dom0, domain, back_device, front_device):
	try:
		if not is_dev_attached(dom0, domain, front_device):
			log(logger, logging.INFO,
				'vinculando disco {} a la maquina virtual como {}'.format(back_device, front_device))
			cmd = "xl block-attach {} phy:{} {} w".format(domain, back_device, front_device)
			stdin,  stdout, stderr = dom0.exec_command(cmd)
			stdout.channel.recv_exit_status()
			time.sleep(5)
		return True
	except Exception as e:
		log(logger, logging.FATAL, msg_e_disco_vinculado, e)
		return False


def find_device(dom0, serial_list):
	try:
		# listamos los discos en lsbkl y consultamos a smartctl el numero de serie
		# de cada dispositivo hasta localizar la primera coincidencia de la lista
		if dom0 is not None:  # si el dominio no es nulo lanzaremos las ordenes al dom0
			cmd = "lsblk -J -e 7,11 -d -o name,serial,model,size,mountpoint"
			stdin, stdout, stderr = dom0.exec_command(cmd)
			devices = stdout.read().decode('utf-8')
		else:  # si el dominio no nulo lanzaremos las ordenes al sistema local
			devices = lsblk("-J", "-e", "7,11", "-d", "-o", "name,serial,model,size,mountpoint")
		discs = json.loads(devices)
		for device in discs['blockdevices']:
			serial = device['serial']
			log(logger, logging.DEBUG, serial)
			if serial in serial_list:
				return serial, '/dev/'+device['name']
		return None, None
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return None, None


def select_machines_discs(server_name, server_hostname, vdialog:dialog):
	"""
	:type server_name: string
	:type server_hostname: string
	:type vdialog: dialog
	:return json_string
	"""
	json_machines=[]
	dom0_server = paramiko.SSHClient()
	dom0_server.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	key = paramiko.RSAKey.from_private_key_file("/home/david/.ssh/id_rsa", password="*$$27C865*")
	dom0_server.connect(hostname=server_hostname, username='root', pkey=key)
	if dom0_server.get_transport() is not None and dom0_server.get_transport().is_active():
		stdin, stdout, stderr = dom0_server.exec_command('ls /etc/xen/auto/')
		machines = stdout.read().decode('utf-8').rstrip().split('\n')
		if len(machines) == 0:
			log(logger, logging.FATAL, 'No hay maquinas en auto', None)
			exit(1)
		for machine in machines:
			items = []
			stdin, stdout, stderr = dom0_server.exec_command("xl list -l " + machine)
			vm = json.loads(stdout.read().decode('utf-8').rstrip())
			text = "Seleccione los discos de la maquina {} que pertenece al cliente: {}({})".format(machine, server_name, server_hostname)
			if vm is not None:
				print(vm[0]['config']['disks'])
				for disk in vm[0]['config']['disks']:
					items.append((disk['pdev_path'], machine, False))
				ccode, ctags = vdialog.checklist(text, choices=items, width=120)
				json_disks = []
				for element in ctags:
					json_disks.append(element)
				json_machines.append({"name": machine,"disks":json_disks})
		vdialog.yesno("Resultado de la seleccion:\n"+json.dumps(json_machines, indent=2)+"\nEsta deacuerdo con la selección?", width=60, height=40)
	return json_machines


def list_devices(dom0):
	try:
		# listamos los discos en lsbkl y consultamos a smartctl el numero de serie
		if dom0 is not None:  # si el dominio no es nulo lanzaremos las ordenes al dom0
			cmd = "lsblk -J -e 7,11 -d -o name,serial,model,size,mountpoint"
			stdin, stdout, stderr = dom0.exec_command(cmd)
			devices = stdout.read().decode('utf-8')
		else:  # si el dominio no nulo lanzaremos las ordenes al sistema local
			devices = lsblk("-J", "-e", "7,11", "-d", "-o", "name,serial,model,size,hotplug")
		discs = json.loads(devices)
		return discs['blockdevices']
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return None, None

def obtener_exluidos(path, dias):
	try:
		if dias == 0:
			dias = 1
		now = time.time()
		if os.path.isfile("/virtual/scripts/exclude-file.txt"):
			os.remove("/virtual/scripts/exclude-file.txt")
		textfile = open("/virtual/scripts/exclude-file.txt", "w")
		for directorio in os.listdir(path):
			if directorio.upper() != '.SYNC' and \
					os.stat(os.path.join(path, directorio)).st_mtime < now - (dias * 86400):
				textfile.write(directorio + "\n")
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return None


def send_mail(datos, body, subject, servicio):
	try:
		if datos['config']['email_smtp'] != '' and  datos['config']['email_login'] != '' and datos['config']['email_responsables'] != '':
			msg = EmailMessage()
			msg['Subject'] = '[{}][{}][BACKUP]{}'.format(datos['config']['empresa'], datos['config']['item'], subject)
			msg['From'] = datos['config']['email_from']
			msg['To'] = datos['config']['email_responsables']
			msg['Date'] = email.utils.formatdate(localtime=True)
			msg.set_content('<html><body><p>'+body+'</p><p> Correo enviado automaticamente por '+servicio+' '+version+' </body></html>')
			msg.set_type('text/html')
			server = smtplib.SMTP(datos['config']['email_smtp'])
			user, password = datos['config']['email_login'].split(':')
			server.login(user, password)
			server.send_message(msg)
			server.quit()
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return False


def sincroniza(link_dest, source, dest, log_file):
	try:
		log(logger, logging.INFO, "sincronizando {} en {} log:{}".format(source, dest, log_file))
		rsync('-H',
				'--numeric-ids',
				'--stats',
				'-vaXA',
				'--delete',
				'--link-dest={}'.format(link_dest),
				'--exclude-from=''/virtual/scripts/exclude-file.txt''',
				'--out-format=\"%t %f %i %\'\'\'b\"',
				source,
				dest,
				_out=log_file)
		return True
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return False


def sincroniza_todo(source, dest, log_file):
	try:
		log(logger, logging.INFO, "sincronizando {} en {} log:{}".format(source, dest, log_file))
		rsync('-H',
				'--numeric-ids',
				'--stats',
				'-vaXA',
				'--delete',
				'--exclude-from=''/virtual/scripts/exclude-file.txt''',
				'--out-format=\"%t %f %i %\'\'\'b\"',
				source,
				dest,
				_out=log_file)
		return True
	except Exception as e:
		log(logger, logging.FATAL, '', e)
		return False



def restablece_estado(dom0, disco_backup):
	# Si esta montado es muy probable que el canal este abierto, lo primero sera desmontar y luego verificar el canal
	try:
		log(logger, logging.INFO, "Liberando canal cifrado...")
		if os.path.ismount('/backup/externo'):
			log(logger, logging.INFO, "el directorio /backup/externo ya esta montado,intentando desmontar")
			if not umount_disk('/backup/externo'):
				log(logger, logging.ERROR, "No se ha podido desmontar el destino /backup/externo previamente montado")
				exit(1)

		if existe_disco(disco_backup) and is_luks(disco_backup):
			if is_luks_device_open(disco_backup):
				log(logger, logging.INFO, "El canal backup-externo ya esta abierto, intentando cerrar")
				if not luks_cierra_canal('backup-externo'):
					exit(1)
				else:
					log(logger, logging.WARNING, msg_w_canal_abierto.format(disco_backup))
		if dom0 is not None:
			dom0_detach_disk(dom0, 'backup.hvm', 'xvde')
	except Exception as e:
		log(logger, logging.FATAL, '', e)


def busca_tarea(datos, cliente, trabajo):
	if len(datos) > 0:
		for tarea in datos['tareas']:
			if tarea['cliente'] == cliente and tarea['trabajo'] == trabajo:
				return tarea
	return None


def buscar_interno_por_fecha(fecha, lista):
	for cdate, path in lista:
		if cdate == fecha and os.path.basename(path) != ".sync":
			return path
	return None


def cambia_contador(datos, cliente, trabajo, ubicacion, serial):
	try:
		tarea = busca_tarea(datos, cliente, trabajo)
		if tarea is not None:
			dt = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
			tarea['fecha_hora'] = dt
			tarea['ubicacion'] = ubicacion
			for disco in tarea['discos']:
				if serial is not None:
					if disco['serial'] == serial:
						disco['contador'] = 0
						log(logger, logging.INFO, "Cliente: {} Trabajo: {} Disco: {} puesto a cero".format(
							cliente, trabajo, disco['serial']))
				else:
					disco['contador'] = disco['contador'] + 1
					log(logger, logging.INFO, "Cliente: {} Trabajo: {} Disco: {} incrementado en 1".format(
						cliente, trabajo, disco['serial']))
			return True
		return False
	except Exception as e:
		log(logger, logging.FATAL, '', e)


def lee_contador(datos, cliente, trabajo, serial):
	tarea = busca_tarea(datos, cliente, trabajo)
	if tarea is not None:
		for disco in tarea['discos']:
			if disco['serial'] == serial:
				return disco['contador']
	return 0


def get_full_path(fpath):
	result = (os.path.join(fpath, file_name) for file_name in os.listdir(fpath))
	result = ((os.stat(path), path) for path in result)
	result = ((stat[ST_MTIME], path) for stat, path in result)
	result = sorted(result)
	return result


def get_luks_passprase(datos):
	if datos['config']['luks_phrase'] == '' and datos['config']['luks_phrase_url'] == '':
		log(logger, logging.ERROR, "no se ha especificado phrase o phrase url")
		return None
	else:
		if datos['config']['luks_phrase'] != '':
			return base64.b64decode(datos['config']['luks_phrase'].encode('utf-8')).decode('utf-8')
		elif datos['config']['luks_phrase_user'] != '' and datos['config']['luks_phrase_pass'] != '':
			response = requests.get(datos['config']['luks_phrase_url'],
									verify=True,
									auth=(datos['config']['luks_phrase_user'], datos['config']['luks_phrase_pass']))
			return base64.b64decode(response.content).decode('utf-8')
		else:
			log(logger, logging.ERROR, "no se ha especificado phrase_user y phrase_pass")
			return None


def existe_disco(path):
	try:
		os.stat(path)
	except OSError:
		return False
	return True


def get_current_disk_info(datos, current_serial, field):
	try:
		for disco in datos['config']['discos']:
			if disco['serial'] == current_serial:
				return disco[field]
	except Exception as e:
		log(logger, logging.FATAL, '', e)


def validate_date(date_text):
	try:
		datetime.datetime.strptime(date_text, '%d-%m-%Y')
		return True
	except ValueError:
		log(logger, logging.ERROR, "Formato de fecha incorrecta, debe ser DD-MM-YYYY")
		return False


def log(flogger, severity, mensaje, extra=None):
	try:
		message_extra = ''
		if extra is not None:
			message_extra = extra
		if severity == logging.DEBUG:
			flogger.debug("%s\n%s", mensaje, message_extra)
			print('DEBUG: ', mensaje, message_extra)
		elif severity == logging.INFO:
			flogger.info("%s\n%s", mensaje, message_extra)
			print('INFO: ', mensaje, message_extra)
		elif severity == logging.WARNING:
			warnings.append(mensaje)
			flogger.warning("%s\n%s", mensaje, message_extra)
			print('WARNING: ', mensaje, message_extra)
		elif severity == logging.ERROR:
			warnings.append(mensaje)
			flogger.error("%s\n%s", mensaje, message_extra)
			print('ERROR: ', mensaje, message_extra)
		elif severity == logging.FATAL:
			warnings.append(mensaje)
			flogger.exception("%s\n%s", mensaje, message_extra, exc_info=True)
			print('EXCEPCION: ', mensaje, message_extra)
	except Exception as e:
		flogger.exception(e, exc_info=True)


def convert_size(size_bytes):
	if size_bytes == 0:
		return "0B"
	size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
	i = int(math.floor(math.log(size_bytes, 1024)))
	p = math.pow(1024, i)
	s = round(size_bytes / p, 2)
	return "%s %s" % (s, size_name[i])


def get_space(token):
	total = 0
	free = 0
	used = 0
	for line in df().splitlines():
		if token in line:
			columns = re.sub(r'\s+', ' ', line).split(' ')
			total += int(columns[1])
			used += int(columns[2])
			free += int(columns[3])
	return convert_size(total*1024), convert_size(used*1024), convert_size(free*1024)


def update_current_disk_date(datos, current_serial, new_date):
	for disco in datos['config']['discos']:
		if disco['serial'] == current_serial:
			disco['last_update'] = new_date
			break


def get_smart_status(dom0, device):
	cmd = 'smartctl -H {}'.format(device)
	if dom0 is not None:
		stdin, stdout, stderr = dom0.exec_command(cmd)
		result = stdout.read().decode('utf-8').rstrip()
	else:
		result = smartctl("-H",device)
	match = re.search(r'result:\s(.*)', result)
	if match is not None and len(match.groups()) >= 1:
		return match.group(1)
	return 'UNKNOWN'


def get_info_volumes():
	alist = []
	for line in df('-h').splitlines():
		if '/backup/interno' in line:
			columns = re.sub('\\s+', ' ', line).split(' ')
			volumes = '<TR><TH align=left>{}<TD>{}<TD>{}<TD>{}'.format(columns[5], columns[1], columns[2], columns[3])
			alist.append(volumes)
	return alist


def mata_proceso(nombre):
	procesos = ps('-A')
	for proceso in procesos.splitlines():
		if nombre in proceso:
			pid = int(proceso.split(None, 1)[0])
			os.kill(pid, signal.SIGKILL)


def guardar_datos(config_path, datos, lock):
	try:
		with lock.acquire(timeout=10):
			with open(config_path, 'w') as f:
				f.seek(0)
				json.dump(datos, f, indent=2)
				f.truncate()
	except Exception as e:
		log(logger, logging.FATAL, '', e)
	finally:
		lock.release()

