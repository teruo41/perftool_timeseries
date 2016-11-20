#!/bin/sh
# by teruo

## Readme ##
# usage: ./run_all.sh
# note:  This is a sample script.

SCRDIR=$(readlink -f `dirname $0`)
TMPDIR="${SCRDIR}/../tmp"

RECORD=${SCRDIR}/p_rec.sh
PERF2CSV=${SCRDIR}/perf2csv.sh
ANALYZE=${SCRDIR}/perf_analyze.py

[ -d ${TMPDIR} ] && rm ${TMPDIR}/*

#${RECORD} | tee record.log
${RECORD}
${PERF2CSV} -i `cat ${TMPDIR}/p_rec.tmp` > perf2csv.log

${ANALYZE} \
  `cat ${TMPDIR}/perf2csv.tmp` \
  `grep processor /proc/cpuinfo | wc -l` \
  ipc > perf_analyze.log
