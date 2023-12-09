#!/bin/bash

if [ "$ELKARBACKUP_LEVEL" != "JOB" ]
then
    echo "Solo permitido a nivel de trabajo" >&2
    exit 1
fi


if [ "$ELKARBACKUP_EVENT" == "POST" ]
then
    python3 /virtual/scripts/main.py -a
fi