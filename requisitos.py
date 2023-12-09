#!/usr/bin/env python3

import subprocess
import sys


if __name__ == '__main__':
	print("Instalando dependencias...")
	dependencies = ['sh', 'paramiko', 'filelock', 'requests']
	subprocess.call([sys.executable, '-m', 'pip', 'install'] + dependencies)
