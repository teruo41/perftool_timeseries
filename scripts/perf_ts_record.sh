#!/bin/bash
#
# Created by Teruo Tanimoto
# http://teruo41.github.io/
#

usage_exit() {
cat <<EOT
Usage: $0 [-e event[,event2,...]] [-d DIR] [-p /path/to/perf] [-u] -- command
       $0 [-h]
       Note:  Root privilege is needed to sample C-state info. (default)
       Events can be configured with sampling period or freq like:
         -e cpu/cpu-cycles,period=1000000/
         -e cpu/cpu-cycles,freq=100000/
       Default command is "openssl speed rsa512 (-multi #cpus)."
EOT
exit
}

get_perf_ver() {
  $PERF --version | \
    awk '{print $3}' | \
    cut -f1 -d- | \
    sed "s:\.: :g"
}

check_perf_ver() {
  local REQUIRED=(`echo $1 | sed "s:\.: :g"`)
  local INSTALLED=(`get_perf_ver`)

  [ ${#REQUIRED[*]} -lt ${#INSTALLED[*]} ] \
    && NUM=${#REQUIRED[*]} \
    || NUM=${#INSTALLED[*]}

  for IDX in `seq 0 $((NUM - 1))`
  do
    if [ ${INSTALLED[$IDX]} -lt ${REQUIRED[$IDX]} ]
    then
      echo 0
      return
    elif [ ${INSTALLED[$IDX]} -gt ${REQUIRED[$IDX]} ]
    then
      echo 1
      return
    fi
  done
  echo 1
}

SCRDIR=$(readlink -f `dirname $0`)

OUTDIR=${SCRDIR}/../perf.data.dir
EVENTS="cpu/cpu-cycles,period=10000000/"
EVENTS=$EVENTS",cpu/instructions,period=10000000/"
EVENTS=$EVENTS",cpu/cache-misses,period=1000/"
PRIV=TRUE
PERF=`which perf`
while getopts d:hp:u OPT
do
  case $OPT in
    d) OUTDIR=$OPTARG ;;
    e) EVENT=$OPTARG ;;
    h) usage_exit ;;
    p) PERF=$OPTARG ;;
    u) PRIV=FALSE ;;
    \?) usage_exit ;;
  esac
done

shift $((OPTIND - 1))

[ ! -x "$PERF" ] && echo "perf command not found!" >&2 && exit
[ `check_perf_ver 3.16.7`  == 0 ] && \
  echo -n "perf is older than 3.16.7. " && \
  echo "Please update it to use this script." && exit

[ ! -d ${OUTDIR} ] && mkdir ${OUTDIR}
OUTPUT=${OUTDIR}/`date +%Y%m%d%H%M%S`

TMPDIR=${SCRDIR}/../tmp
[ ! -d $TMPDIR ] && mkdir ${TMPDIR}
echo ${OUTPUT} > ${TMPDIR}/p_rec.tmp

ARGS="-e $EVENTS -o ${OUTPUT}_0"

if [ -z "$@" ]
then
  NUMCPUS=`grep processor /proc/cpuinfo | wc -l`
  if [ $NUMCPUS -gt 1 ]
  then
    CMD="openssl speed rsa512 -multi $NUMCPUS"
  else
    CMD="openssl speed rsa512"
  fi
else
  CMD="$@"
fi

if [ $PRIV = "TRUE" ]
then
  sudo ${PERF} timechart record \
    ${PERF} record -a $ARGS -- $CMD
  
  sudo mv perf.data ${OUTPUT}_p
  
  sudo chown ${USER}. ${OUTPUT}_0
  sudo chown ${USER}. ${OUTPUT}_p
else
  ${PERF} record $ARGS -- $CMD
fi
