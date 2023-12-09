#!/bin/bash

MYSQL_DB=elkarbackup
UPLOADS=/var/spool/elkarbackup/uploads

echo "Starting backup..."
echo "Date: " `date "+%Y-%m-%d (%H:%M)"`

echo Backing up mysql DB
mysqldump $MYSQL_DB > /backup/interno/repositorio/elkarbackup.sql
echo Backing up uploads
rsync -aH --delete $UPLOADS /backup/interno/repositorio
/virtual/scripts/main.py
