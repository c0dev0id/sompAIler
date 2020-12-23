set -o nounset
T="${1}"
if [ ! -d "${T}" ]; then
       >&2 echo "${T} does not exist or is not a directory"
       exit 1
elif [ ! -f "${T}/running.pid" ]; then
       touch "${T}/running.pid" "${T}/.use_dir_as_cache" "${T}/score"
fi

IND="$(date +%s -r "${T}/score")"
if [ -f "${T}/OUT.log" ]; then
       OUTD="$(date +%s -r "${T}/OUT.log")"
fi
read STAGE PID < "${T}/running.pid"
  # STAGE: "s" sompyler | "l" convert wav to mp3

if [ "${IND-0}" -gt "${OUTD-0}" ]; then
	# kill running process if any
	while kill -0 "${PID}" 2> /dev/null; do
		kill "${PID}"
		sleep 1;
	done
	rm "${T}/OUT.wav" 2>/dev/null
	cd $SOMPYLER
        . .venv/bin/activate
        scripts/sompyle "${T}/score" "${T}/OUT.wav" > "${T}/OUT.log" -v --workers=0 2> "${T}/ERR.log" &
	PID=$! STAGE="s"
        printf "${STAGE} ${PID}" > "${T}/running.pid"
        while [ ! -f "${T}/OUT.wav" ]; do
		if kill -0 "${PID}"; then
			sleep 1;
		else
			>&2 printf "Initialization Failure"
			exit 1
		fi
	done

fi

awk '
BEGIN { CURR=0; ETA="(loading ...)" }
/New note/ {TOTAL+=1; print}
/Reuse note/ && !/former run/ { REUSE+=1; print}
/Synthesizing tones/ { CURR=$4; TOTAL=$6; ETA=$7 "~" $8; }
/Assembling/ {RES=$6; print}
END {
           print "---";
           print CURR, TOTAL, (REUSE+TOTAL)/(TOTAL or 1)*100, ETA, RES;
}' "${T}/OUT.log"

# read and parse progress information from OUT.log
if [ "${STAGE}" = "s" ]; then
       if [ -s "${T}/OUT.wav" ]; then
               while kill -0 $PID 2> /dev/null; do
                       sleep 1;
                done
               lame -S -V4 "${T}/OUT.wav" "${T}.mp3" 2>"${T}/ERR.log" &
               printf "l $!" > "${T}/running.pid"
               echo "LAME encoding wave file to MP3 ..."
elif [ "${STAGE}" = "l" ] && kill -0 $PID 2> /dev/null; then
       echo "LAME still encoding ..."
elif [ "$(date +%s -r "${T}.mp3")" -gt "$(date +%s -r ${T}/OUT.wav)" ];
   then echo "${T}.mp3 ready to deliver."
else
       >&2 echo "Unforeseen condition"
       exit 1;
fi        
echo ---
>&2 cat "${T}/ERR.log"

