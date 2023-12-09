#!/bin/bash

eval "$(ssh-agent)" > /dev/null
trap 'ssh-agent -k > /dev/null' EXIT

## COMANDOS
SSH=$(which ssh)
RSYNC=$(which rsync)


#ELKARBACKUP_URL=root@192.168.1.200:/backup/images
#ELKARBACKUP_LEVEL=JOB
#ELKARBACKUP_EVENT=PRE

URL=`echo $ELKARBACKUP_URL | cut -d ":" -f1`
USER="${URL%@*}"
HOST="${URL#*@}"
REMOTE_HOST=192.168.32.240
CERT_PASS=Zw8YbLZM7ZqFnNMUwY38pI42Tvs6mu3IQepJalMxqk3DorYJAt

export DISPLAY=1
echo $CERT_PASS | SSH_ASKPASS=/virtual/scripts/ap-helper.sh ssh-add /root/.ssh/id_rsa

SHPARAMS="-o StrictHostKeyChecking=no $ELKARBACKUP_SSH_ARGS"
#SHPARAMS="-i /var/lib/elkarbackup/.ssh/id_rsa -o StrictHostKeyChecking=no $ELKARBACKUP_SSH_ARGS"

if [ "$ELKARBACKUP_LEVEL" != "CLIENT" ]
then
    echo "Solo permitido a nivel de cliente" >&2
    exit 1
fi


if [ "$ELKARBACKUP_EVENT" == "PRE" ]
then
	$SSH $SSHPARAMS $USER@$HOST "$RSYNC -aXAHz --exclude=*@GMT* --delete /vitual/samba $USER@REMOTE_HOST::samba"
fi