#!/usr/bin/env python3
import helpers
from resources import *
config_path = "/virtual/scripts/backup_externo.config"
config_lock_path = "/virtual/scripts/backup_externo.config.lock"
datos = []

def install():
	from crontab import CronTab
	my_cron = CronTab(user='root')
	job = my_cron.new(command='python3 /virtual/scripts/installer.py -u', comment='backup_externo_cron')
	job.minute.every(10)
	my_cron.write()
	
def download_latest_version(url,version,news):
	print("downloading")
	import requests, zipfile, io
	global datos
	r = requests.get(url, verify=False, stream=True)
	z = zipfile.ZipFile(io.BytesIO(r.content))
	z.extractall('/virtual/scripts/')
	r_news = requests.get(news, verify=False, allow_redirects=True)
	body = helpers.crea_cuerpo_update(version,r_news.text)
	if helpers.send_mail(datos, body, 'UPDATE SUCESSFULL', 'servicio backup'):
		helpers.warnings.clear()
	
def update():
	import requests
	import configparser
	from packaging import version
	import os.path
	url = 'https://updates.emite.net/EServices/UServices.ini'
	r = requests.get(url, verify=False, allow_redirects=True)
	with open('/virtual/scripts/UServices.ini', 'wb') as f:
		f.write(r.content)
	UServices = configparser.ConfigParser()
	UServices.read('/virtual/scripts/UServices.ini')
	if not os.path.isfile('/virtual/scripts/app_info.ver'):
		print('app_info not exist')
		download_latest_version(UServices['update2']['url'],UServices['update2']['ver'],UServices['update2']['news'])
	else:	
		app_info = configparser.ConfigParser()
		app_info.read('/virtual/scripts/app_info.ver')
		if version.parse(UServices['update2']['ver']) > version.parse(app_info['APP_INFO']['ver']):
			download_latest_version(UServices['update2']['url'],UServices['update2']['ver'],UServices['update2']['news'])
		else:
			print("app is updated aborting")
	
	
def uninstall():
	from crontab import CronTab
	my_cron = CronTab(user='root')
	my_cron.remove(comment='backup_externo_cron')
	my_cron.write()
	
def main():
	global datos
	import subprocess
	import sys
	import argparse
	print("Instalando dependencias...")
	dependencies = ['packaging','croniter','python-crontab','sh', 'paramiko', 'filelock', 'requests']
	subprocess.call([sys.executable, '-m', 'pip', 'install'] + dependencies)
	from filelock import FileLock
	datos = helpers.leer_fichero(FileLock(config_lock_path, timeout=10), config_path, helpers.config_template)
	ap = argparse.ArgumentParser(prog='Backup externo installer', usage='%(prog)s [options]', description='')
	ap.add_argument("-i", required=False, action='store_true', help="Instalar")
	ap.add_argument("-u", required=False, action='store_true', help="Actualizar")
	ap.add_argument("-d", required=False, action='store_true', help="desinstalar")
	ap.add_argument("-V", action="version", version='%(prog)s 1.0')
	args = ap.parse_args()
	if args.u:
		update()
	elif args.i:
		install()
	elif args.i:
		unistall()
	
if __name__ == '__main__':
	main()
	