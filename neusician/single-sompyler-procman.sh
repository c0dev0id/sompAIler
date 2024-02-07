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
read USER PID < "${T}/worker.pid"

if [ "${USER}" != "${U}" ]; then
        rm "${T}"/*.{npy,instr} "${T}/registry" 2> /dev/null
fi

OUTFILE="${T}/../OUT/$U.mp3"

if [ "${IND-0}" -gt "${OUTD-0}" ]; then
	# kill running process if any
	while kill -0 "${PID}" 2> /dev/null; do
		kill "${PID}"
		sleep 1;
	done
	cd $SOMPYLER
	case "$W0MODE" in
		check-only)
		   W0MODE='--workers 0'
		   WORKERS_CNT=0
		   ;;
		reverb)
		   W0MODE='--room' ;;
		reverb:*)
		   W0MODE=${W0MODE:7}
		   W0MODE=${W0MODE//[^a-zA-Z0-9_-]/}
		   W0MODE='--room '$W0MODE
		   ;;
		midi)
		   W0MODE='--emit-premidi-notes-to='"${T}/premidi.txt"
		   ;;
		*)
		   W0MODE="" ;;
	esac
	: > "${T}/status"
        . venv/bin/activate
	./scripts/sompyle -v "--workers=${WORKERS_CNT-1}" "${T}/score" "$OUTFILE" $W0MODE > "${T}/OUT.log" 2> "${T}/ERR.log" &
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

# read and parse progress information from OUT.log
if [ -f "${T}/status" ]; then
    read skip reuse total curr eta res < "${T}/status"
fi
if [ -n "$SKIP_KNOWN_LINES" ]; then
    unset SKIP_KNOWN_LINES
else skip=0 reuse=0 total=0 curr=0
fi

awk -v skip=${skip:-0} -v REUSE=${reuse:-0} -v TOTAL=${total:-0} -v CURR=${curr:-0} -v ETA=${eta:-(loading...)} -v RES=${res:--1} '
NR<=skip { next }
/New note/ {TOTAL+=1; print }
/Reuse note/ { REUSE+=1; print }
/ \.\.\. / { CURR=$4; TOTAL=$6; ETA=$7 "~" $8; }
/ Assembling/ { REUSE=0 }
RES<0 && /^Assembling/ {RES=$10; print }
/[Mm]easure/ {print}
/unused notes/ && $1>0 {print}
END {
    print "---";
    print CURR, REUSE, REUSE+TOTAL, ETA, (RES<0 ? 0 : RES);
    print NR, REUSE, TOTAL, CURR, ETA, (RES>0 ? 0 : RES) > "/dev/fd/3";
}' "${T}/OUT.log" 3> "${T}/status"
if kill -0 $PID 2> /dev/null; then
       if [ -s "$OUTFILE" ]; then
               while kill -0 $PID 2> /dev/null; do
                       sleep 1;
               done
       fi
elif [ -s "$OUTFILE" -a "$(date_of "$OUTFILE")" -ge "$(date_of "${T}/score")" ]; then
       printf "%s %d" "${U}" "$PID" > "${T}/worker.pid"
       echo "$OUTFILE ready to deliver."
else
       echo "FAILED. Process ID no longer exists."
fi        
echo ---
cat "${T}/ERR.log"
exit
