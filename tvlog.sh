#!/bin/bash

# DEBUG=true

PROG=$(basename $0)
HOSTNAME=$(hostname)

[ "$DEBUG" ] && set -x

TVHEADEND=${TVHEADEND:-"$HOME/.hts/tvheadend"}
[ -d "${TVHEADEND}" ] || exit
[ -L "${TVHEADEND}/.recordings" ] && RECORDINGS=$(readlink -f "${TVHEADEND}/.recordings")
[ -L "${TVHEADEND}/.backup" ] && BACKUP=$(readlink -f "${TVHEADEND}/.backup")

LOG="${TVHEADEND}/dvr/log"
CSV="${TVHEADEND}/dvr/log.csv"


HEADER="start|stop|uuid|date|begin|end|duration|flags|status|channel|comment|title|subtitle|show|episode|season|number|filename|description"
#       1	  2	   3    4    5     6   7        8     9      10      11      12    13       14   15      16     17     18       19

function quoted () {

	echo "\"$(sed 's/"/\\"/g' <<<"$1")\""
}

function unquote () {

	sed 's/^"//
		 s/"$//
		 s/\\"/"/' <<<"$1"
}


function logfile () {

	local FILE=$1 FORMAT=$2

	[ -d "$FILE" ] && return 0
	[ -f "$FILE" ] || { echo "ERROR: File [$FILE] not found!" 1>&2; return 2; }
	UUID="$(basename $FILE)"
	set -- $(sed 's/\[\|\]\|,/ /g' <<<$(jq -rc '[.start, .stop, .flags, .status]' $FILE 2>/dev/null))
	[ $# -ne 4 ] && { echo "ERROR: File [$FILE] not a tvheadend log file!" 1>&2; return 3; }
	START="$1"; STOP="$2"; FLAGS="$3"; STATUS="${4//\"/}"
	[ "$FLAGS" == "null" ] && FLAGS=0
	[ "$STATUS" == "null" ] && STATUS="" 
	[ "$START" == "null" -o "$STOP" == "null" ] && { echo "ERROR: File [$FILE] not a tvheadend log file!" 1>&2; return 3; }
	DURATION=$((($STOP - $START)/60))

	echo -n "${START}|${STOP}|${UUID}|$(date -d @${START} '+%Y-%m-%d')|$(date -d @${START} '+%H:%M')|$(date -d @${STOP} '+%H:%M')|${DURATION}|${FLAGS}|${STATUS}|"

	case "$FORMAT" in

		short)		jq -rc '[.channelname, .comment, .title.ger, .subtitle.ger, .show, .episode, .season, .number,
							 .filename // .files[0].filename] | join("|")' $FILE | sed 's/^\[//
		 																				s/\]$//'
					;;

		full) 		jq -rc '[.channelname, .comment, .title.ger, .subtitle.ger, .show, .episode, .season, .number,
							 .filename // .files[0].filename, .description.ger] | join("|")' $FILE | sed 's/^\[//
		 					     															  			  s/\]$//'
					;;
	esac

	return 0
}


TAR="tar czf"
[ "$DEBUG" ] && TAR="tar cvzf"

STAMP="$(date '+%Y-%m-%d_%H%M%S')"


case "$1" in

	--upcoming)	tvlog.py --tvheadend $TVHEADEND
				;;	

	--mirror)	shift
				cd "$RECORDINGS" || exit
				target=/tmp/recordings.$$
				mkdir $target || exit

				find * -type d -print0 | xargs -0 -I {} mkdir -p $target/{}
				find * -type f -a \( -name "*.mkv" -o -name "*.mp4" -o -name "*.ts" \) -print0 | xargs -0 -I {} touch -r {} $target/{}

				[ -d "${BACKUP}/recordings" ] || mkdir -p "${BACKUP}/recordings" || exit
				cd $target || exit				
				$TAR "${BACKUP}/recordings/recordings_$STAMP.tgz" *
				cd "${BACKUP}" && ln -sf "recordings/recordings_$STAMP.tgz" ./recordings.tgz
				[ "$target" ] && [ -d "$target" ] && [ "$(dirname $target)" == "/tmp" ] && rm -r $target
				echo "Mirrorfile [${BACKUP}/recordings/recordings_$STAMP.tgz] created."
				;;

	--backup)	# snapshot of recordings (filenames only), log and csv
				[ -d "${BACKUP}/log" ] || mkdir -p "${BACKUP}/log" || exit
				cd "$(dirname $LOG)" || exit
				$TAR "${BACKUP}/log/log_$STAMP.tgz" log/ $(basename $CSV)
				cd "${BACKUP}" && ln -sf "log/log_$STAMP.tgz" ./log.tgz
				echo "Backup file [${BACKUP}/log/log_$STAMP.tgz] created."
				;;

	--ckcsv)	# check for missing recordings and video files
				shift
				[ "$1" == "--clear" ] && shift && CLEAR=true
				[ "$1" ] && CSV="$1"
				NOW=$(date '+%s')
		 
				while IFS='' read -r line || [[ -n "$line" ]]
				do
					IFS="|"

					set -- $line ; [ "$1" == "start" ] && continue

					start="$1"
					stop="$2"
					uuid="${3}"
					title=$(quoted "${12}")
					subtitle=$(quoted "${13}")
					filename="${18}"

					[ $stop -lt $NOW ] && {

						if [ "$filename" ]
						then
							[ -f "$filename" ] || echo "[$uuid] file [$filename] not found!"
							[ "$CLEAR" ] && [ -f "$LOG/$uuid" ] && rm "$LOG/$uuid"								
						else
							echo "[$uuid] recording for [$title/$subtitle] not found!"
							[ "$CLEAR" ] && [ -f "$LOG/$uuid" ] && rm "$LOG/$uuid"								
						fi
					}
				done < "$CSV"
				;;

	--cklog)	# check logfiles for missing files
				shift
				[ "$1" == "--clear" ] && shift && CLEAR=true
				
				if [ "$1" ]
				then
					files=$@
				else
					cd "$LOG" || exit
					files="*"
				fi
				NOW=$(date '+%s')

				for uuid in $files
				do
					stop=$(jq -r '.stop' $uuid)
				
					[ $stop -lt $NOW ] && {
					
						file=$(jq -r '.filename // .files[0].filename' $uuid)
						title=$(jq -rc '[.title.ger, .subtitle.ger]' $uuid)

						if [ "$file" == "null" ]
						then
							echo "[$uuid] missing filename for $title"
							[ "$CLEAR" ] && rm $uuid																
						else
							[ -f "$file" ] || {
								echo "[$uuid] missing file [$file]"
								[ "$CLEAR" ] && rm $uuid																
							}
						fi
					}
				done
				;;

	--ckrec)	# check for recordings not referenced in log file
				
				shift
				[ "$1" == "--clear" ] && shift && CLEAR=true

				cd "$LOG" || exit
				jq -r '.filename // .files[0].filename' * | grep -v "^null"	> /tmp/loglist.$$
				find $RECORDINGS -maxdepth 1 -type f -print > /tmp/reclist.$$
				while IFS='' read -r line || [[ -n "$line" ]]
				do
					grep -q "$line" /tmp/loglist.$$ || {

						ls -lh "$line"
						[ "$CLEAR" ] && rm "$line"																																
					}
	
				done < /tmp/reclist.$$
				rm /tmp/{reclist,loglist}.$$
				;;

	--update)	# update tvlog files from csv
				shift
									
				[ "$1" ] && CSV="$1"
				NOW=$(date '+%s')

				UPCOMING=0
				NEW=0
				FINISHED=0
				MISSING=0
				FAILED=0
				DELETED=0
		 
				while IFS='' read -r line || [[ -n "$line" ]]
				do
			
					IFS="|"	
					set -- $line

					[ "$1" == "start" ] && continue
			
					start="$1"
					stop="$2"

					UUID="$3"
					uuid=$(quoted "${3}")

					date=$(quoted "${4}")
					begin=$(quoted "${5}")
					end=$(quoted "${6}")
					duration=${7}
					flags=${8}
					status=${9}

					channelname=$(quoted "${10}")
					comment=$(quoted "${11}")
					title=$(quoted "${12}")
					subtitle=$(quoted "${13}")
					show=$(quoted "${14}")
					episode=$(quoted "${15}")
					season=${16:-0}
					number=${17:-0}

					filename="${18}"	
					description=$(quoted "${19}")
					IFS=''
	
					LFNAME="$LOG/$UUID"
					MSG="${12} - ${13}"

					if [ -f "$LFNAME" ]
					then
						EPOCH=$(stat -c%Y $LFNAME)
						if [ $NOW -gt $stop ]
						then
							if [ "$filename" ] 
							then
								MSG="${filename/${RECORDINGS}\//}"
								if [ -f $filename ]
								then
									if [ "$(dirname $filename)" == "$RECORDINGS" ]
									then
										# new recording: 
										status="new" ; NEW=$(( $NEW + 1 ))
										file=$(basename $filename)
										MSG="$file"
										base=${file%.*}
										ext=${file##*.}

										#IFS="|" && set -- $(sed 's/^\(.*\) - \(.*\) (2015-[0-9][0-9]-[0-9][0-9] [0-9][0-9]-[0-9][0-9] .*)$/\1|\2/' <<<"$base")
										#[ $# -ne 2 ] && IFS="=" && set -- $(eval echo ${title}=${subtitle})
										#[ "$show" == "\"\"" ] && show=$(quoted "$1")
										#[ "$episode" == "\"\"" ] && episode=$(quoted "$2")

										[ "$show" == "\"\"" ] && show="${title}"
										[ "$episode" == "\"\"" ] && episode="${subtitle}"

										[ $season -gt 0 ] && [ $number -gt 0 ] && [ "$show" != "\"\"" ] && [ "$episode" != "\"\"" ] && {
			
											epi="$(printf "S%02dE%02d" $season $number)"
											dir="$(dirname $filename)/$(unquote $show)"
											new="$dir/$(unquote $show) - $epi - $(unquote $episode).$ext"

											if [ "$DEBUG" ]
											then
												echo  "$filename -> $new" && filename="$new" && status="finished"
											else									
												[ -d "$dir" ]  || mkdir "$dir"
												[ -d "$dir"  ] && {
								
													mv "$filename" "$new" && filename="$new" && status="finished"
												}
											fi
										}
									else
										# update from show directory
										status="finished" ; FINISHED=$(( $FINISHED + 1 ))
										file=$(basename $filename)
										MSG="$file"
										base=${file%.*}
										dir=$(basename $(dirname $filename))

										IFS="|" && set -- $(sed 's/^\(.*\) - S\([0-9]*\)E\([0-9]*\) - \(.*\)$/\1|\2|\3|\4/' <<<"$base")
										[ "$show" == "\"\"" ] && show=$(quoted "$1")
										[ "$season" ] || season=$(sed 's/^0*//' <<<"${2}")
										[ "$number" ] || number=$(sed 's/^0*//' <<<"${3}")
										[ "$episode" == "\"\"" ] && episode=$(quoted $(sed 's/ (2015-[0-9][0-9]-[0-9][0-9] [0-9][0-9]-[0-9][0-9] .*)$//' <<<"$4"))

										#[ "$season" ] || season=${2##+(0)}
										#[ "$number" ] || number=${3##+(0)}
									fi
								else
									# file not found
									status="missing" ; MISSING=$(( $MISSING + 1 ))
								fi
							else
								# no filename
								status="failed" ; FAILED=$(( $FAILED + 1 ))
							fi
						else
							if [ $NOW -lt $start ]
							then
								status="upcoming" ; UPCOMING=$(( $UPCOMING + 1 )) 
							else
								status="running"
							fi
						fi

						status=$(quoted "$status")
						filename=$(quoted "$filename")
						[ "$season" ] || season=0
						[ "$number" ] || number=0
						season=$(quoted $season)
						number=$(quoted $number)

						jq ". + {
							\"channelname\": $channelname,
							\"comment\": $comment,
							\"title\": { \"ger\": $title },
							\"subtitle\": { \"ger\": $subtitle },
							\"show\": $show,
							\"episode\": $episode,
							\"season\": $season,
							\"number\": $number,
							\"status\": $status,
							\"flags\": $flags,
							\"description\": { \"ger\": $description }
						}" $LFNAME > /tmp/csv2tvlog.$$

						if [ "$DEBUG" ]
						then
							cat /tmp/csv2tvlog.$$
							rm /tmp/csv2tvlog.$$
						else				
							if [ "$filename" == "\"\"" ]
							then
								mv /tmp/csv2tvlog.$$ $LFNAME
							else
								jq "if .filename then . + { \"filename\": $filename } else . + { \"files\": [ { \"filename\": $filename } ] } end" /tmp/csv2tvlog.$$ > $LFNAME
								rm /tmp/csv2tvlog.$$
							fi
							TOUCH="$(date -d @${EPOCH} '+%Y%m%d%H%M.%S')"
							touch    -t  $TOUCH $LFNAME
							touch -h -t  $TOUCH $LFNAME
						fi
					else
						status="deleted" ; DELETED=$(( $DELETED + 1 ))
						MSG="logfile [$LFNAME] not found!"
					fi
					printf "[%s] %-8s %s %s %s\n" $UUID $(unquote $status) $(unquote $date) $(unquote $begin) $MSG
	
				done < "$CSV"
				echo
				echo "upcoming=$UPCOMING, new=$NEW, finished=$FINISHED, missing=$MISSING, failed=$FAILED, deleted=$DELETED"
				echo
				;;

	--csv)		# write logs to csv

				shift
				if [ "$1" ]
				then
					files=$@								
				else
					cd "$LOG" && files=$(ls -tr *)
				fi

				# redirect to default file	
				[ -t 1 ] && exec > "$CSV"
				echo "$HEADER"					
				for file in $files
				do
					echo "[$(basename $file)] $(jq -rc '[.title.ger, .subtitle.ger] | join(" - ")' $file)" 1>&2
					logfile "$file" "full" || exit $?
				done

				#cd "$(dirname $CSV)" || exit
				#touch "$(basename $CSV .csv)_$STAMP.csv"
				#ln -sf "$(basename $CSV .csv)_$STAMP.csv" "$(basename $CSV)"
				# [ -f "$CSV" ] && cp "$CSV" "$(dirname $CSV)/$(basename $CSV .csv)_$(date '+%Y-%m-%d_%H%M%S').csv"
				#echo "$HEADER" >$CSV
				;;


	-*)			echo "Unknown option $1" 1>&2 && exit 1
				;;
				
	*)			# compact listing of logfiles
				if [ "$1" ]
				then
					files=$@								
				else
					cd "$LOG" && files=$( ls -tr *)
				fi
				for file in $files
				do
					logfile "$file" "short" || exit $?
				done
				;;

esac

[ "$DEBUG" ] && set +x

