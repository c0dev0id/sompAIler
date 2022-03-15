#!/usr/bin/env bash
set -o nounset
T="${1}"
U="${2}"

if ! [[ "$U" =~ ^[a-zA-Z0-9_]+$ ]]; then
	>&2 printf "username $U not accepted\n"
	exit 1;
fi

if [ ! -d "${T}" ]; then
       >&2 printf "${T} does not exist or is not a directory"
       exit 1
elif [ ! -f "${T}/worker.pid" ]; then
       touch "${T}/worker.pid" "${T}/.use_dir_as_cache" "${T}/score"
fi

date_of() {
    date +%s -r "$1" 2> /dev/null || printf 0;
}

IND="$(date_of "${T}/score")"
if [ -f "${T}/OUT.log" ]; then
       OUTD="$(date_of "${T}/OUT.log")"
fi
read USER PID LASTRUN < "${T}/worker.pid"
: ${LASTRUN:=1}


if [ "${USER}" != "${U}" ]; then
        rm "${T}"/*.{npy,instr} "${T}/registry" 2> /dev/null
fi

OUTFILE="${T}/../OUT/$U.ogg"

if [ "${IND-0}" -gt "${OUTD-0}" ]; then
	# kill running process if any
	while kill -0 "${PID}" 2> /dev/null; do
		kill "${PID}"
		sleep 1;
	done
	cd $SOMPYLER
        . venv/bin/activate
	LASTRUN=1
        ./scripts/sompyle -v --workers="${WORKERS_COUNT-1}" "${T}/score" "$OUTFILE" > "${T}/OUT.log" 2> "${T}/ERR.log" &
	PID=$!
        printf "%s %d" "${U}" "$PID" > "${T}/worker.pid"
        while [ ! -f "$OUTFILE" ] || [ -s "$OUTFILE" ]; do
		if kill -0 "${PID}" 2> /dev/null; then
			sleep 1;
		elif [ "$(date_of "$OUTFILE")" -ge "$(date_of "${T}/score")" ]; then
			break
		else
			>&2 printf "Initialization Failure"
			exit 1
		fi
	done

fi

export LASTRUN
# read and parse progress information from OUT.log
awk '
BEGIN { REUSE=0; TOTAL=0; RES=0; CURR=0; ETA="(loading...)" }
/New note/ {TOTAL+=1; print }
/Reuse note/ { REUSE+=1; print }
/Synthesizing tones/ { CURR=$4; TOTAL=$6; ETA=$7 "~" $8; }
ENVIRON["LASTRUN"]==1 && /Assembling/ {RES=$6; print }
/[Mm]easure/ {print}
END {
           print "---";
           print CURR, REUSE, REUSE+TOTAL, ETA, RES;
}' "${T}/OUT.log"

if kill -0 $PID 2> /dev/null; then
       if [ -s "$OUTFILE" ]; then
               while kill -0 $PID 2> /dev/null; do
                       sleep 1;
               done
       fi
elif [ -s "$OUTFILE" -a "$(date_of "$OUTFILE")" -ge "$(date_of "${T}/score")" ]; then
       printf "%s %d %d" "${U}" "$PID" 0 > "${T}/worker.pid"
       echo "$OUTFILE ready to deliver."
else
       echo "FAILED. Process ID no longer exists."
fi        
echo ---
cat "${T}/ERR.log"
exit
