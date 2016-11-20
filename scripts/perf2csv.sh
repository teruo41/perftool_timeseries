#!/bin/bash
# perf2csv.sh by Teruo Tanimoto

usage_exit() {
cat <<EOT
Usage: $0 -i /path/to/input (without either _p or _0).
EOT
exit
}

func1() {
  local INPUT=$1
  local OUTPUT=$2
  local IDX=$3
  
  [ -f ${OUTPUT}_${IDX} ] && rm ${OUTPUT}_${IDX}
  # if [[ "${EVENTS_A[$IDX]}" =~ /[^/]+/ ]]
  # then
  #   local PATTERN=`echo ${EVENTS_A[$IDX]} | sed "s:/\([^/]+\)/:\1:"`
  # else
  #   local PATTERN=${EVENTS_A[$IDX]}
  # fi
  local PATTERN=${EVENTS_A[$IDX]}
  grep $PATTERN $INPUT | \
    sed -e "/^#/d"     | \
    sed "s/^ \+//g"    | \
    sed "s/:\? \+/;/g" >> ${OUTPUT}_${IDX}.csv
}

func2() {
  local INPUT=$1
  local OUTPUT=$2
  [ -f ${OUTPUT}_p.csv ] && rm ${OUTPUT}_p.csv
  $PERF script -i ${INPUT}_p > $TMPDIR/$$_p
  sed -e "/^#/d" $TMPDIR/$$_p | \
    sed "s/^ \+//g"        | \
    sed "s/:\? \+/;/"      | \
    sed "s/:\? \+/;/"      | \
    sed "s/:\? \+/;/"      | \
    sed "s/:\? \+/;/"      | \
    sed "s/:\? \+/;/" > ${OUTPUT}_p.csv
  rm $TMPDIR/$$_p
}

EVENTS="cpu/cpu-cycles,period=10000000/"
EVENTS=$EVENTS",cpu/instructions,period=10000000/"
EVENTS=$EVENTS",cpu/cache-misses,period=1000/"
INPUT=""
PERF=`which perf`
while getopts i:h OPT
do
  case $OPT in
    i)
      INPUT=$OPTARG
      ;;
    e)
      EVENTS=$OPTARG
      ;;
    h)
      usage_exit
      ;;
    p)
      PERF=$OPTARG
      ;;
    \?)
      usage_exit
      ;;
  esac
done

[ -z "$INPUT" ] && usage_exit

SCRDIR=$(readlink -f `dirname $0`)
TMPDIR="${SCRDIR}/../tmp"

INDIR=$(readlink -f `dirname ${INPUT}`)
OUTDIR=${INDIR}/../perf.csv
[ ! -d ${OUTDIR} ] && mkdir ${OUTDIR}
OUTPUT=${OUTDIR}/`basename ${INPUT}`

EVENTS_A=(`echo $EVENTS | sed "s:/,:/ :g"`)

$PERF script -i ${INPUT}_0 > $TMPDIR/$$

for IDX in `seq 0 $((${#EVENTS_A[*]} - 1))`
do
  #echo ${EVENTS_A[$IDX]}
  func1 $TMPDIR/$$ ${OUTPUT} ${IDX} &
done


func2 ${INPUT} ${OUTPUT} &

wait
rm $TMPDIR/$$
echo ${OUTPUT} > ${TMPDIR}/perf2csv.tmp
