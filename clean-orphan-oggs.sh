#!/bin/sh
#
# Cron this script for every half an hour or so, to get rid of
# generated ogg files by users who would not be able any more
# to log in.
#
# Call: ./clean-orphan-oggs.sh /var/tmp/sompyler/data/OUT
#                              ^ or wherever the files are stored

set -eu

cd "$1"

QUERY="SELECT CASE WHEN '%s' IN (SELECT name FROM user) THEN NULL ELSE '%s' END;\n"
MYDIR="$(cd $(dirname $(readlink -f "$0")); pwd)"


ls *.ogg | while read file
do
    if [ -s "$file" ]; then
        user="${file%.*}"
        printf "$QUERY" "$user" "$user"
    fi
done | sqlite3 "$MYDIR/instance/neusician.db" | while read user
do
    if [ -n "$user" ]; then
        rm -- "$user.ogg"
    fi
done

# Get also rid of files that have been empty for 24h at least.
# A sompyle procedure should never run that long, but if indeed,
# the output files will not be accessible.
# Such files are likely to have been created in runs that
# raised an error later on and the user who issued them probably has
# lost interest since.
find -empty -mtime +0 -delete
