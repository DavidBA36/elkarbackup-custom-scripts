#!/bin/bash

#
# Name: backup-mysql.sh
# Description: Este script respalda todas sus bases de datos MySQL locales en archivos individuales
# Copiará solo las bases de datos modificadas.
# Uso:  JOB level -> Pre-Script


eval "$(ssh-agent)" > /dev/null
trap 'ssh-agent -k > /dev/null' EXIT

CERT_PASS=Zw8YbLZM7ZqFnNMUwY38pI42Tvs6mu3IQepJalMxqk3DorYJAt
export DISPLAY=1
echo $CERT_PASS | SSH_ASKPASS=/virtual/scripts/ap-helper.sh ssh-add ~/.ssh/id_rsa 

ELKARBACKUP_URL=root@192.168.1.202:/backup/databases 
ELKARBACKUP_LEVEL=JOB
ELKARBACKUP_EVENT=PRE

URL=`echo $ELKARBACKUP_URL | cut -d ":" -f1`
USER="${URL%@*}" 
HOST="${URL#*@}"
DIR=`echo $ELKARBACKUP_URL | cut -d ":" -f2`
MYSQL=/usr/bin/mysql
MYSQLDUMP=/usr/bin/mysqldump
TMP=/tmp/mysqldump

SSHPARAMS="-o StrictHostKeyChecking=no"



if [ -f "/etc/debian_version" ]
then
	MYSQLCNF=/etc/mysql/debian.cnf
else

	MYSQLCNF=/root/.my.cnf
fi

TEST=`ssh $SSHPARAMS $USER@$HOST "test -f $MYSQLCNF && echo $?"`

if [ ! ${TEST} ]; then
    echo "[ERROR] el archivo de configuracion de mysql no existe $MYSQLCNF"
    exit 1
fi


if [ "$ELKARBACKUP_LEVEL" != "JOB" ]
then
    echo "Solo permitido a nivel de trabajo" >&2
    exit 1
fi


if [ "$ELKARBACKUP_EVENT" == "PRE" ]
then
    # cargamos el certificado privado con la contraseña
	

	# si el directorio  de backup no exite lo creamos
    TEST=`ssh $SSHPARAMS $USER@$HOST "test -d $DIR && echo $?"`
    if [ ! ${TEST} ]; then
        echo "[INFO] El directorio Backup $DIR no existe. Creando..."
        ssh $USER@$HOST "mkdir -p $DIR"
    fi

    # si el directorio termporal no existe lo creamos
    TEST=`ssh $SSHPARAMS $USER@$HOST "test -d $TMP && echo $?"`
    if [ ! ${TEST} ]; then
        echo "[INFO] El directorio temporal $TMP no existe. Creando..."
        ssh $USER@$HOST "mkdir -p $TMP"
    fi

    # listamos las bases de datos
    databases=`ssh $SSHPARAMS $USER@$HOST "$MYSQL --defaults-file=$MYSQLCNF -e \"SHOW DATABASES;\"" | grep -Ev "(Database|information_schema)"`
    RESULT=$?
    if [ $RESULT -ne 0 ]; then
        echo "ERROR: $databases"
        exit 1
    else
        for db in $databases; do
            ssh $USER@$HOST "$MYSQLDUMP --defaults-file=$MYSQLCNF --force --opt --databases $db --single-transaction --quick --lock-tables=FALSE > \"$TMP/$db.sql\""
            # Si ya tenemos una versión antigua...
            TEST=`ssh $SSHPARAMS $USER@$HOST "test -f $DIR/$db.sql && echo $?"`
            if [ ${TEST} ]; then
                # Diff
                #echo "comparamos con el backup previo"
                TEST=`ssh $SSHPARAMS $USER@$HOST "diff -q <(cat $TMP/$db.sql|head -n -1) <(cat $DIR/$db.sql|head -n -1) > /dev/null && echo $?"`
                #echo "diff result: [$TEST]"
                # Si Diff = false, copia el archivo de volcado tmp.
                if [ ! ${TEST} ]; then
                    ssh $SSHPARAMS $USER@$HOST "cp $TMP/$db.sql $DIR/$db.sql"
                    echo "[$db.sql] Cambios detectados. Guardando volcado."
                else
                    echo "[$db.sql] Sin Cambios. Nada que Guardar."
                fi
            else
                echo "[$db.sql] Primer Volcado Creado!"
                ssh $SSHPARAMS $USER@$HOST "cp $TMP/$db.sql $DIR/$db.sql"
            fi
        done
    fi
fi
