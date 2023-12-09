#!/usr/bin/env python3
import argparse
import atexit
import logging
from datetime import datetime
import pathlib
import pprint
import signal
import base64
from sh import mv
from resources import *
import helpers
import os
import paramiko
import shutil
from filelock import FileLock
from dialog import Dialog

config_path = "/virtual/scripts/backup_externo.config"
config_lock_path = "/virtual/scripts/backup_externo.config.lock"
lock = FileLock(config_lock_path, timeout=10)
logger = helpers.get_logger(__name__)
datos = []
client = None


# noinspection PyTypeChecker
def configura_parametros():
	global datos
	config = {}
	disco_to_save = []
	machines = []
	try:
		empresa= datos['config']['empresa']
		item= datos['config']['item']
		disco_interno= datos['config']['disco_interno']
		smart = datos['config']['smart']
		email_smtp= datos['config']['email_smtp']
		email_login= datos['config']['email_login']
		email_from= datos['config']['email_from']
		email_responsables = datos['config']['email_responsables']
		luks_phrase = datos['config']['luks_phrase']
		luks_phrase_url= datos['config']['luks_phrase_url']
		luks_phrase_user= datos['config']['luks_phrase_user']
		luks_phrase_pass = datos['config']['luks_phrase_pass']
		vmc = datos['config']['vmc']
		if vmc:
			dom0 = datos['config']['dom0']
			dom0_backup = datos['config']['dom0_backup']
		code = None
		d = Dialog(dialog="dialog", DIALOGRC=helpers.dialogrc)
		d.set_background_title("CONFIGURACION DE BACKUP")
		while code != d.ESC and code != d.CANCEL:
			if vmc:
				code, tag = d.menu("Seleccione una de las siguientes opciones."
				                   " Use escape o cancelar para salir del menu sin guardar",
			                        choices=[("Modo", "Modo de operación Virtual/Directo (Virtual)"),
			                                 ("General", "Parámetros de la aplicación"),
			                                 ("Correo", "Parámetros para notificaciones"),
			                                 ("Cifrado", "Parámetros de cifrado"),
			                                 ("Discos", "Discos asociados para copia"),
			                                 ("Maquinas", "Discos incluidos de maquinas virtuales"),
			                                 ("Guardar", "Guardar los datos y salir del menu")], width=100)
			else:
				code, tag = d.menu("Seleccione una de las siguientes opciones."
				                   " Use escape o cancelar para salir del menu sin guardar",
				                   choices=[("Modo", "Modo de operación Virtual/Directo (Directo)"),
				                            ("General", "Parámetros de la aplicación"),
				                            ("Correo", "Parámetros para notificaciones"),
				                            ("Cifrado", "Parámetros de cifrado"),
				                            ("Discos", "Discos asociados para copia"),
				                            ("Maquinas", "Discos incluidos de maquinas virtuales"),
				                            ("Guardar", "Guardar los datos y salir del menu")], width=100)
			if tag == "Modo":
				if d.yesno("El sistema de Backup esta implemetado en una maquina virtual?") == d.OK:
					vmc = True
					dom0 = ''
					dom0_backup = ''
				else:
					vmc = False
			elif tag == "General":
				if not vmc:
					elements = [("Nombre de la empresa", 1, 1, empresa, 1, 35, 40, 40, 0x0),
					            ("Item del la maquina", 2, 1, item, 2, 35, 40, 40, 0x0),
					            ("Path disco backup interno", 3, 1, disco_interno, 3, 35, 40, 40, 0x0),
					            ("Opciones extra SMART", 4, 1, smart, 4, 35, 40, 40, 0x0)]
				else:
					elements = [("Nombre de la empresa", 1, 1, empresa, 1, 35, 40, 40, 0x0),
					            ("Item del la maquina", 2, 1, item, 2, 35, 40, 40, 0x0),
					            ("Direccion IP dom0", 3, 1, dom0, 3, 35, 40, 40, 0x0),
					            ("Nombre maquina backup", 4, 1, dom0_backup, 4, 35, 40, 40, 0x0),
					            ("Path disco backup interno en dom0", 5, 1, disco_interno, 5, 35, 40, 40, 0x0),
					            ("Opciones extra SMART", 6, 1, smart, 6, 35, 40, 40, 0x0)]
				code, fields = d.mixedform("General: Complete los datos que se solicitan.", elements, width=100)
				if code == d.OK:
					empresa = fields[0]
					item = fields[1]
					if vmc:
						dom0 = fields[2]
						dom0_backup = fields[3]
						disco_interno = fields[4]
						smart = fields[5]
					else:
						disco_interno = fields[2]
						smart = fields[3]

			elif tag == "Correo":
				elements = [("Servidor SMTP", 1, 1, email_smtp, 1, 50, 50, 50, 0x0),
				            ("Login SMTP (user:password)", 2, 1, email_login, 2, 50, 50, 50, 0x0),
				            ("Email desde (Si esta soportado por el servidor)", 3, 1, email_from, 3,50, 50,50, 0x0),
				            ("Email notificaciones (A,B,C...)", 4, 1, email_responsables, 4, 50, 50, 255, 0x0)]
				code, fields = d.mixedform("Correo: Complete los datos que se solicitan.", elements, width=100)
				if code == d.OK:
					email_smtp = fields[0]
					email_login = fields[1]
					email_from = fields[2]
					email_responsables = fields[3]
			elif tag == "Cifrado":
				elements = [("Passprhase crypto [****]", 1, 1, "", 1, 50, 50, 255, 0x1),
				            ("Passprhase crypto URL", 2, 1, luks_phrase_url, 2, 50, 50, 255, 0x0),
				            ("Passprhase crypto URL User ", 3, 1, luks_phrase_user, 3, 50, 50, 255,0x0),
				            ("Passprhase crypto URL Pass [****]", 4, 1, "", 4, 50, 50, 255, 0x1)]
				code, fields = d.mixedform("Correo: Complete los datos que se solicitan.", elements, width=100)
				if code == d.OK:
					luks_phrase = fields[0]
					luks_phrase_url = fields[1]
					luks_phrase_user = fields[2]
					luks_phrase_pass = fields[3]
			elif tag == "Discos":
				all_items = []
				all_devices = []
				saved_serials = []
				for disco in datos['config']['discos']:
					tag = disco['serial']
					hotplug = 'no hotplug'
					if disco['hotplug']:
						hotplug = 'hotplug'
					all_devices.append(disco)
					all_items.append(
						(tag, disco['model'] + ' ' + disco['serial'] + ' (/dev/' + disco['name'] + ') ' + hotplug, True))
					saved_serials.append(disco['serial'])
				discos = helpers.list_devices(client)
				for disco in discos:
					tag = disco['serial']
					hotplug = 'no hotplug'
					if disco['hotplug']:
						hotplug = 'hotplug'
					if tag not in saved_serials:
						all_devices.append(disco)
						all_items.append(
							(tag, disco['model'] + ' ' + disco['serial'] + ' (/dev/' + disco['name'] + ') ' + hotplug,
							 False))

				code, tags = d.buildlist(
					"Utilize las teclas de cursor y la barra espaciadora para colocar en la lista de la "
					"derecha los discos que desea utilizar."
					"De igual forma deje en la lista de la izquierda los excluidos",
					items=all_items, visit_items=True, width=150)
				if code == d.OK:
					for device in all_devices:
						if device['serial'] in tags:
							disco_to_save.append(device)
			elif tag == "Maquinas":
				acode = None
				while acode != d.ESC and acode != d.CANCEL:
					acode, atag = d.menu("Seleccione una de las siguientes opciones."
					                   " Use escape o cancelar para salir del menu sin guardar",
					                   choices=[("Nuevo", "Añade un cliente a la lista de maquinas"),
					                            ("Eliminar", "Elimina un cliente a la lista de maquinas"),
					                            ("Modificar", "Modifica un cliente a la lista de maquinas"),
					                            ("Discos", "Añadir un disco de la maquina"),
					                            ("Guardar", "Guardar los datos y salir del menu")], width=100)
					if atag == "Nuevo":
						server_name = 'prometeo'
						server_hostname = '192.168.4.200'
						json_clients = []
						while 1:
							elements = [("Nombre", 1, 1, server_name, 1, 15, 25, 25, 0x0),
							            ("Hostname", 2, 1, server_hostname, 2, 15, 25, 25, 0x0)]
							vcode, vfields = d.mixedform("1º Indique el nombre del cliente que se utiliza en la tarea de elkarbackup.\n"
							                           "2º Indique la direccion ip de la maquina dom0 correspondiente.", elements,
							                           width=50, height=12)
							if vcode == d.OK:
								server_name = vfields[0]
								server_hostname = vfields[1]
								json_machines = helpers.select_machines_discs(server_name, server_hostname, d)
								json_clients.append({"client":server_name,"machines":json_machines})
								print(json_clients)
								break
							else:
								break
							#machines.append({'client':name})
					elif atag == "Eliminar":
						pass
			elif tag == "Guardar":
				config['last_device'] = datos['config']['last_device']
				config['vmc'] = vmc
				config['empresa'] = empresa
				config['item'] = item
				if vmc:
					config['dom0'] = dom0
					config['dom0_backup'] = dom0_backup
				config['disco_interno'] = disco_interno
				config['discos'] = disco_to_save
				config['email_smtp'] = email_smtp
				config['email_login'] = email_login
				config['email_from'] = email_from
				config['email_responsables'] = email_responsables
				config['smart'] = smart
				if luks_phrase != '':
					config['luks_phrase'] = base64.b64encode(luks_phrase.encode('utf-8')).decode('utf-8')
				else:
					config['luks_phrase'] = datos['config']['luks_phrase']
				config['luks_phrase_url'] = luks_phrase_url
				config['luks_phrase_user'] = luks_phrase_user
				config['luks_phrase_pass'] = luks_phrase_pass
				backup = {'config': config, 'tareas': datos['tareas']}
				helpers.guardar_datos(config_path, backup, lock)
				print('Configuracion guardada con exito')
				break;

	except Exception as e:
		helpers.log(logger, logging.FATAL, '', e)
		print(e)





def rotar_disco(serial):
	global datos
	try:
		for tarea in datos['tareas']:
			if helpers.lee_contador(datos, tarea['cliente'], tarea['trabajo'], serial) > 0:
				path_interno_tarea = tarea['ubicacion']
				path_externo_tarea = tarea['ubicacion'].replace("/interno", "/externo/interno")

				internal = helpers.get_full_path(path_interno_tarea)
				external = helpers.get_full_path(path_externo_tarea)

				for cdate, path in external:
					if os.path.basename(path) != ".sync":
						nombre = helpers.buscar_interno_por_fecha(cdate, internal)
						if nombre is not None:
							if os.path.basename(nombre) != os.path.basename(path):
								nombre = nombre.replace("/interno", "/externo/interno")
								helpers.log(logger, logging.INFO, "se ha renombrado el directory de: {} a: {} ".format(
									path, nombre))
								mv(path, nombre)
							else:
								helpers.log(logger, logging.INFO, "{} es identico a {} no se realizan cambios".format(
									path, nombre))
						else:
							shutil.rmtree(path)
							helpers.log(logger, logging.INFO, path + " borrado")
				helpers.cambia_contador(datos, tarea['cliente'], tarea['trabajo'], tarea['ubicacion'], serial)
	except Exception as e:
		helpers.log(logger, logging.FATAL, '', e)
	finally:
		helpers.guardar_datos(config_path, datos, lock)


# noinspection PyTypeChecker
def agregar_rotacion(elkarbackup):
	"""
		agregar_rotacion(elkarbackup)

		Registra una tarea de rotacion que se aplicara mas tarde al disco externo.
	"""
	global datos
	try:
		if not helpers.cambia_contador(datos, elkarbackup.get('client-name'), elkarbackup.get('job-name'),
		                               elkarbackup.get('path'), None):
			dt = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
			discos = []
			for disco in datos['config']['discos']:
				discos.append({'serial': disco['serial'], 'contador': 1})

			tarea = {'cliente': elkarbackup.get('client-name'),
			         'trabajo': elkarbackup.get('job-name'),
			         'ubicacion': elkarbackup.get('path'),
			         'fecha_hora': dt,
			         'discos': discos}
			datos['tareas'].append(tarea)
			helpers.log(logger, logging.INFO, "Se ha registrado el cliente: {} con el trabajo {}".format(
				elkarbackup.get('client-name'), elkarbackup.get('job-name')))
		exit(0)
	except Exception as e:
		helpers.log(logger, logging.FATAL, '', e)
		exit(1)
	finally:
		helpers.guardar_datos(config_path, datos, lock)


def prepara_disco(serial):
	"""
		prepara_disco(rsakey, serial)

		Prepara un disco para usarlo como backup externo
	"""
	global datos
	global client
	disco_backup = '/dev/xvde'
	try:
		if helpers.print_yn_question(
				'A elegido preparar el disco con el numero de serie {}. Ocasiona perdida de datos. Esta seguro? y/N:'.format(
						serial)):
			helpers.log(logger, logging.INFO, 'Verificando el estado del dispositivo')
			current_serial, current_device = helpers.find_device(client, [serial], datos['config']['smart'])
			if current_device is None:
				helpers.log(logger, logging.ERROR, 'Disco con numero de serie {} no encontrado'.format(serial))
				exit(1)
			if not datos['config']['vmc']:
				disco_backup = current_device

			helpers.restablece_estado(client, disco_backup)
			passphrase = helpers.get_luks_passprase(datos)
			if passphrase is None:
				exit(1)
			if datos['config']['vmc']:
				if not helpers.dom0_attach_disk(client, 'backup.hvm', current_device, 'xvde'):
					exit(1)
			helpers.log(logger, logging.INFO, 'Creando canal cifrado en disco {} ({})'.format(disco_backup, serial))
			if not helpers.luks_formatea(disco_backup, passphrase):
				exit(1)
			helpers.log(logger, logging.INFO, msg_i_luks_open.format(disco_backup, serial))
			if not helpers.luks_abre_canal(disco_backup, 'backup-externo', passphrase):
				exit(1)
			helpers.log(logger, logging.INFO, 'Formateando /dev/mapper/backup-externo')
			if not helpers.formato('/dev/mapper/backup-externo'):
				exit(1)
			helpers.log(logger, logging.INFO, 'Cerrando canal backup-externo')
			if not helpers.luks_cierra_canal('backup-externo'):
				exit(1)
	except Exception as e:
		helpers.log(logger, logging.FATAL, '', e)
	finally:
		if datos['config']['vmc']:
			helpers.dom0_detach_disk(client, 'backup.hvm', 'xvde')


def monta_externo(check):
	global datos
	global client
	serial_list = []
	# por defecto es una maquina virtual. El disco de backup siempre se vincula en xvde
	disco_backup = '/dev/xvde'
	try:
		for disco in datos['config']['discos']:
			if check:
				if disco['last_update'] == '' or (
						datetime.now() - datetime.strptime(disco['last_update'], '%d-%m-%Y')).days > 15:
					helpers.log(logger, logging.WARNING,
					            'El disco con el numero de serie {} aun no ha sido usado. Considere eliminarlo de la lista'.format(
						            disco['serial']))
			serial_list.append(disco['serial'])
		# si esta activo "vmc" es una maquina virtual y
		# configuramos el objeto del cliente ssh para realizar peticiones al dom0
		# buscamos entre los discos del dom0 o maquina local algun disco cuyo numero de serie este en serial_list
		# si no hay coincidencias salimos y generamos error
		helpers.log(logger, logging.INFO, "Buscando dispositivos")
		current_serial, current_device = helpers.find_device(client, serial_list, datos['config']['smart'])
		if current_serial is None:
			helpers.log(logger, logging.ERROR, msg_e_no_disco)
			return False, None, None
		else:
			# si no es maquina virtual el disco externo es el mismo dispositivo que sale de la consulta anterior
			if not datos['config']['vmc']:
				disco_backup = current_device
			# comprobamos si ha rotado el disco
			if check and current_serial == datos['config']['last_device']:
				helpers.log(logger, logging.WARNING, "No olvide rotar el disco de copias. HD no ha rotado.")

			datos['config']['last_device'] = current_serial

			# restablecemos el estado del disco. esto es desmontar /backup/externo y cerrar el canal cifrado
			# si es maquina virtual tambien eliminara la vinculacion del disco
			helpers.restablece_estado(client, disco_backup)
			# si es maquina virtual vinculamos el disco obtenido en find_device
			if datos['config']['vmc']:
				if not helpers.dom0_attach_disk(client, 'backup.hvm', current_device, 'xvde'):
					return False, None, None
			# comprobamos que es un disco cifrado
			if not helpers.is_luks(disco_backup):
				helpers.log(logger, logging.ERROR, msg_e_disco_no_preparado.format(current_serial))
				return False, None, None
			# abrimos el canal
			if not helpers.luks_abre_canal(disco_backup, 'backup-externo', helpers.get_luks_passprase(datos)):
				return False, None, None
			# montamos el disco
			if not helpers.monta_disco('/dev/mapper/backup-externo', '/backup/externo'):
				helpers.log(logger, logging.ERROR, msg_e_disco_no_montado)
				return False, None, None
			return True, current_serial, current_device
	except Exception as e:
		helpers.log(logger, logging.FATAL, '', e)
		return False, None, None


def realiza_backup():
	global datos
	global client
	bdata = {}
	hora_inicio = datetime.now()
	# necesitamos los datos del fichero json
	if datos is None:
		exit(1)

	try:
		# cargo las series de los discos en una lista para usar mas tarde
		status_ok, current_serial, current_device = monta_externo(True)
		if not status_ok:
			helpers.log(logger, logging.INFO, "Error montando el disco externo")
			exit(1)
		else:
			helpers.log(logger, logging.INFO, "Sincronizando datos...")
			# rotamos los directorios del disco externo
			rotar_disco(current_serial)
			# para cada tarea de backup comprobamos la fecha de la ultima sincronizacion para elaborar una lista de exlusion
			# excluiremos todo lo sea mas antiguo que el numero de dias especificados donde el minimo es 1
			# .sync nunca de excluye
			# una vez elaborada la lista lanzamos la sincronizacion
			# si no hay tareas, no hay rotaciones y lo sincronizamos todo, por si viene de viejo
			excludes = pathlib.Path('/virtual/scripts/exclude-file.txt')
			excludes.touch(exist_ok=True)

			if len(datos['tareas']) == 0:
				if not helpers.sincroniza_todo('/backup/interno/', '/backup/externo/interno/',
				                               '/backup/bk_all_disk.log'):
					helpers.log(logger, logging.ERROR, msg_e_sync_error.format('/backup/interno'))
			else:
				for tarea in datos['tareas']:
					last_update_str = helpers.get_current_disk_info(datos, current_serial, 'last_update')
					if last_update_str != '':
						last_update = datetime.strptime(last_update_str, '%d-%m-%Y')
						days_diff = (datetime.now() - last_update).days
						if days_diff == 0:
							days_diff = 1
						helpers.obtener_exluidos(tarea['ubicacion'], days_diff)

					link_dest = tarea['ubicacion'] + '/.sync'
					source_path = pathlib.Path(tarea['ubicacion'])
					source = source_path.as_posix() + '/'
					dest = tarea['ubicacion'].replace("/interno", "/externo/interno") + '/'
					if not os.path.exists(dest):
						pathlib.Path(dest).mkdir(parents=True, exist_ok=True)
					flog = source_path.parent.parent.as_posix() + '/bk_' + tarea['trabajo'] + '.log'
					if not helpers.sincroniza(link_dest, source, dest, flog):
						helpers.log(logger, logging.ERROR, msg_e_sync_error.format(tarea['ubicacion']))

			# enviamos el informe
			bdata['volumenes'] = helpers.get_info_volumes()
			bdata['serie'] = current_serial
			bdata['isize'], bdata['iused'], bdata['ifree'] = helpers.get_space('/backup/interno')
			bdata['esize'], bdata['eused'], bdata['efree'] = helpers.get_space('/backup/externo')
			bdata['transcurrido'] = str(datetime.now() - hora_inicio).split('.', 2)[0]
			bdata['external_smart'] = helpers.get_smart_status(client, current_device)
			bdata['internal_smart'] = helpers.get_smart_status(client, datos['config']['disco_interno'])
			bdata['advertencias'] = helpers.warnings
			helpers.update_current_disk_date(datos, current_serial, datetime.today().strftime('%d-%m-%Y'))
			body = helpers.crea_cuerpo_copia_ok(bdata)
			if helpers.send_mail(datos, body, 'SE PUEDE CAMBIAR LA COPIA', 'servicio backup'):
				helpers.warnings.clear()
			exit(0)
	except Exception as e:
		helpers.log(logger, logging.FATAL, '', e)
		exit(1)
	finally:
		# pase lo que pase desmontaremos el disco, cerramos el canal, desvinculamos el disco y guardamos los datos
		helpers.umount_disk('/backup/externo')
		helpers.luks_cierra_canal('backup-externo')
		if datos['config']['vmc']:
			helpers.dom0_detach_disk(client, 'backup.hvm', 'xvde')
		helpers.guardar_datos(config_path, datos, lock)


def exit_handler():
	global datos
	if len(helpers.warnings) > 0:
		adv = '<br>.\n'.join(helpers.warnings)
		body = msg_mail_body_warn.format(adv)
		helpers.send_mail(datos, body, msg_mail_sbj_warn, 'servicio backup')


def exit_program(signum, frame):
	# si el programa termina abruptamente nos aseguramos de eliminar el proceso rsync
	helpers.mata_proceso('rsync')


def main():
	global datos
	global client
	signal.signal(signal.SIGINT, exit_program)  # si la aplicacion es matada, terminada
	signal.signal(signal.SIGTERM, exit_program)
	try:
		datos = helpers.leer_fichero(lock, config_path, helpers.config_template)
		if datos['config']['vmc']:
			client = paramiko.SSHClient()
			client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			key = paramiko.RSAKey.from_private_key_file("/home/david/.ssh/id_rsa",password="*$$27C865*")
			client.connect(hostname=datos['config']['dom0'], username='root', pkey=key)
			if client.get_transport() is not None:
				client.get_transport().is_active()
		atexit.register(exit_handler)  # si la aplicacion finaliza
		ap = argparse.ArgumentParser(prog='rotacion_discos', usage='%(prog)s [options]',
		                             description='Realiza Backup Externo, prepara discos externos,'
		                                         'mantiene un listado de las tareas ejecutadas por elkarbackup '
		                                         'y rota los diarios del disco externo en curso.')
		ap.add_argument("-w", required=False, action='store_true', help="Ver configuracion")
		ap.add_argument("-c", required=False, action='store_true', help="Configurar Backup Externo")
		ap.add_argument("-a", required=False, action='store_true', help="Añadir Rotacion")
		ap.add_argument("-m", required=False, action='store_true', help="Monta disco externo")
		ap.add_argument("-u", required=False, action='store_true', help="Desmonta disco externo")
		ap.add_argument("-p", required=False, default=None, help="Prepara un disco externo")
		ap.add_argument("-V", action="version", version='%(prog)s 1.0')
		args = ap.parse_args()
		if args.c:
			configura_parametros()
		elif args.p is not None:
			prepara_disco(args.p)
		elif args.a:
			agregar_rotacion(helpers.get_env_vars())
		elif args.w:
			pprint.pprint(datos)
		elif args.m:
			helpers.log(logger, logging.INFO, "Montando disco externo")
			monta_externo(False)
		elif args.u:
			helpers.log(logger, logging.INFO, "Desmontando disco externo")
			helpers.umount_disk('/backup/externo')
			helpers.luks_cierra_canal('backup-externo')
			if datos['config']['vmc']:
				helpers.dom0_detach_disk(client, 'backup.hvm', 'xvde')
		else:
			configura_parametros()
	# realiza_backup()

	except Exception as e:
		helpers.log(logger, logging.FATAL, '', e)
		print(e)
	finally:
		if client is not None:
			client.close()


if __name__ == '__main__':
	main()
