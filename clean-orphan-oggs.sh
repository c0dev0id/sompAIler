#!/usr/bin/env bash
#
# Cron this script for every half an hour or so, to get rid of
# generated ogg files by users who wouldn't be able to log in anyway.
#
# Call: ./clean-orphan-oggs.sh /var/tmp/sompyler/data/OUT
#                              ^ or wherever the files are stored

set -eu

cd "$1"

QUERY="SELECT CASE WHEN '%s' IN (SELECT name FROM user) THEN NULL ELSE '%s' END;\n"
MYDIR="$(cd $(dirname $(readlink -f "$0")); pwd)"


{ ls *.ogg | while read file
  do
    if [ -s "$file" ]; then
        user="${file%.*}"
        printf "$QUERY" "$user" "$user"
    else
        rm -- "$file"
        fi
  done
} | sqlite3 "$MYDIR/instance/neusician.db" | while read user
do
    if [ -n "$user" ]; then
        rm -- "$user.ogg"
    fi
done

