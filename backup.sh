#!/bin/bash
# Purpose = Backup of Important Data
# Created on 17-1-2012
# Author = Hafiz Haider
# Version 1.0
#
# Sample Cron
# 00 4 * * * /backup.sh
#

TIME=`date +%Y-%m-%d`               # This Command will add date in Backup File Name.
FILENAME=LightSTM.db-$TIME.tar.gz   # Here i define Backup file name format.
SRCDIR=~/stm-tracker/data           # Location of Important Data Directory (Source of backup).
DESDIR=~/backups                    # Destination of backup file.

mkdir -p $DESDIR
tar -cpzf $DESDIR/$FILENAME $SRCDIR
