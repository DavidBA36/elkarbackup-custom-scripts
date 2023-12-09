#!/usr/bin/env python3
import argparse
import atexit
import signal
import helpers

config_path = "/etc/samba/smbsnap.conf"
logger = helpers.get_logger(__name__)


def exit_handler():
    pass


def exit_program(signum, frame):
    pass


def main():
    # signal.signal(signal.SIGINT, exit_program)  # si la aplicacion es matada, terminada
    # signal.signal(signal.SIGTERM, exit_program)
    atexit.register(exit_handler)
    ap = argparse.ArgumentParser(prog='WindowsSnaps', usage='%(prog)s [options]',
                                 description='Gestiona Snapshots de Windows')
    ap.add_argument("-w", required=False, action='store_true', help="Ver configuracion")
    ap.add_argument("-s", required=False, action='store_true', help="Configurar WindowsSnaps")
    ap.add_argument("-c", required=False,
                    choices=['mount', 'umount', 'snap', 'clean', 'cleanall', 'autosnap', 'autoresize'], help="Comando")
    ap.add_argument("-l", required=False, help="LV number")
    ap.add_argument("-n", required=False, help="Snap-Set Number")
    ap.add_argument("-V", action="version", version='%(prog)s 1.0')
    args = ap.parse_args()
    lv_number = 'all'
    snapset_number = '0'
    if args.c is not None:
        if args.l is not None:
            lv_number = args.l
        if args.n is not None:
            snapset_number = args.n
        helpers.process_command(args.c, config_path, lv_number, snapset_number)
    helpers.process_command('autosnap', config_path, 'all', '0')

if __name__ == '__main__':
    main()