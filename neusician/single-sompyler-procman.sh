set -o nounset
TMPDIR=$1
IND="$(date +%s score)"
OUTD="$(date +%s OUT.log)"
read STAGE PID < running.pid
  # STAGE: "s" sompyler | "l" convert wav to mp3

cd "$TEMPDIR"
if [ "${IND}" -gt "${OUTD}" ]; then
	# kill running process if any
	while kill -0 "${PID}"; do
		kill "${PID}"
		sleep 1;
	done
	rm OUT.wav 2>/dev/null
	$SOMPYLER score OUT.wav > OUT.log -v --workers=0 2> ERR.log &
	PID=$! STAGE="s"
	printf "${STAGE} ${PID}" > running.pid
	while [ ! -f OUT.wav ]; do
		if kill -0 "${PID}"; then
			sleep 1;
		else
			>&2 printf "Initialization Failure"
			exit 1
		fi
	done

fi

# read and parse progress information from OUT.log
if [ "${STAGE}" -eq "s" ]; then
	awk '
	BEGIN { CURR=0; ETA="(loading ...)" }
        /New note/ {TOTAL+=1; print}
        /Reuse note/ && !/former run/ { REUSE+=1; print}
        /Synthesizing tones/ { CURR=$4; TOTAL=$6; ETA=$7 "~" $8; }
        /Assembling/ {RES=$6; print}
        END {
            print "---";
            print CURR, TOTAL, (REUSE+TOTAL)/(TOTAL or 1)*100, ETA, RES;
        }
	' OUT.log
	if [ "${RES}" -gt 0 ]; then
		lame -S -V4 OUT.wav ../$(basename "$1").mp3 2>ERR.log &
		printf "l $!" > running.pid
		printf "LAME encoding wave file to MP3 ...\n"
	fi
elif [ "${STAGE}" -eq "l" ] && ; then
	printf "LAME still working ...\n"
fi        
echo ---
cat ERR.log

