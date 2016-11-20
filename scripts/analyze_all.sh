#!/bin/sh

## Readme ##
# usage: ./analyze_all.sh $input $ncpus
# args:  $input := directory which contains csv files
#                  csv files can be created by perf2csv.sh
#        $ncpus := logical CPU core count to analyze
#

SCRDIR=$(readlink -f `dirname $0`)
ANALYZE=${SCRDIR}/perf_analyze.py

## Arguments ##
INPUT=$1  # like ./perf.csv/20141113102546
CPU=$2    # logical CPU core count

## Parameters ##
START="0" # [sec]
END="100" # [sec]
STEP="1"  # step[sec] used in timeseries analysis

## Run analysis script ##
# note: metrics implemented are ...
#       - instructions
#       - cpu-cycles
#       - cache-misses
#       - mpki (cache-misses / K instructions)
#       - ipc (instructions / cpu-cycles)
#
# note: each block below executes independent analysis,
#       so unnecessary block can be commented out.
#

# instructions
for i in `seq ${START} ${STEP} ${END}`
do
  ${ANALYZE}  ${INPUT} ${CPU} instructions ${i} ${STEP}
  NUM=`printf "%05.1f" ${i}`
  mv perf_analyze.csv instr_${NUM}.csv
done

# cpu-cycles
for i in `seq ${START} ${STEP} ${END}`
do
  ${ANALYZE} ${INPUT} ${CPU} cpu-cycles ${i} ${STEP}
  NUM=`printf "%05.1f" ${i}`
  mv perf_analyze.csv cycle_${NUM}.csv
done

# cache-misses
for i in `seq ${START} ${STEP} ${END}`
do
  ${ANALYZE} ${INPUT} ${CPU} cache-misses ${i} ${STEP}
  NUM=`printf "%05.1f" ${i}`
  mv perf_analyze.csv cache_${NUM}.csv
done

# mpki
for i in `seq ${START} ${STEP} ${END}`
do
  ${ANALYZE} ${INPUT} ${CPU} mpki ${i} ${STEP}
  NUM=`printf "%05.1f" ${i}`
  mv perf_analyze.csv mpki_${NUM}.csv
done

# ipc
for i in `seq ${START} ${STEP} ${END}`
do
  ${ANALYZE} ${INPUT} ${CPU} ipc ${i} ${STEP}
  NUM=`printf "%05.1f" ${i}`
  mv perf_analyze.csv ipc_${NUM}.csv
done
