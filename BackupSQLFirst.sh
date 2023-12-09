#!/bin/bash
EXIT_STATUS=1
SERVER=`echo $ELKARBACKUP_URL | cut -d ":" -f1`
echo Running rsync $SERVER::BackupSQLFirst
rsync $SERVER::BackupSQLFirst
exit $?
