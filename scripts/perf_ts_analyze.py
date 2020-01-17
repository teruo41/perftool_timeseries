#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by teruo

## Readme ##
# usage: ./perf_ts_analyze.py input cpu event offset length
# args:  input  := csv file (output of perf2csv.sh, without _p)
#        cpu    := logical CPU core count, like 32
#        event  := event name, like 'cpu-cycles'
#        offset := start offset[sec], like 10.0
#        length := length[sec], like 0.1
# note:  This script executes analysis from offset[sec] to offset + length[sec].
# note:  sqlite3 and numpy library is required (maybe optional)

import os
import sys
import math
import csv
import sqlite3
import numpy
import re
import multiprocessing

def gettime(db):
  con = sqlite3.connect(db)
  cur = con.cursor()

  min = float("inf")
  max = float("-inf")
  sql = u"select time from perf_event"
  for row in cur.execute(sql):
    if min > row[0]:
      min = row[0]
    if max < row[0]:
      max = row[0]
  con.close()
  return (min, max)

def reduce_gettime(list):
  min = float("inf")
  max = float("-inf")
  for i in range(len(list)):
    if min > list[i][0]:
      min = list[i][0]
    if max < list[i][1]:
      max = list[i][1]
  return (min, max)

def getfunclist(db):
  con = sqlite3.connect(db)
  cur = con.cursor()
  sql = u"select comm,sym,bin from perf_event"
  funcs = []
  for row in cur.execute(sql):
    funcs.append(";".join(row))
  con.close()
  return list(set(funcs))

def reduce_getfunclist(li):
  funcs = reduce(lambda a,b: a+b, li)
  return list(set(funcs))

def analyze_events(args):
  db    = args[0]
  event = args[1]
  cpu   = args[2]
  start = args[3]
  end   = args[4]

  con = sqlite3.connect(db)
  cur = con.cursor()

  dict = {}

  # sql  = u"select comm,sym,bin,event,cpu from perf_event"
  # cur.execute(sql)
  # for row in cur.execute(sql):
  #   print "event=%s, cpu=%s" % (row[3], row[4])
  #   break

  for cpuid in range(cpu):
    sql  = u"select comm,sym,bin from perf_event"
    sql += u" where event like \"%%%s%%\" and cpu=%d" % (event, cpuid)
    sql += u" and  time between %f and %f"   % (start, end)
    for row in cur.execute(sql):
      funcname = ";".join(row)
      if dict.has_key(funcname):
        value = dict[funcname]
        value[cpuid] += 1
        dict[funcname] = value
      else:
        value = [ 0 for i in range(cpu) ]
        value[cpuid] += 1
        dict[funcname] = value
  con.close()
  return dict

def reduce_analyze_events(li):
  summary = {}
  for dict in li:
    for key in dict.keys():
      if summary.has_key(key):
        summary[key] = summary[key] + numpy.array(dict[key])
      else:
        summary[key] = numpy.array(dict[key])
  return summary

def analyze_cstate(args):
  db    = args[0]
  start = args[1]
  end   = args[2]

  con = sqlite3.connect(db)
  cur = con.cursor()
  
  sql  = u"select time,event from perf_event"
  sql += u" where time between %f and %f" % (start, end)
  
  prev_time = start
  c0_time = 0.0
  last_event = ""
  for row in cur.execute(sql):
    if row[1] == 'power:power_start':
      c0_time += row[0] - prev_time
      last_event = row[1]
    elif row[1] == 'power:power_end':
      prev_time = row[0]
      last_event = row[1]
  else:
    if last_event == 'power:power_end':
      c0_time += end - prev_time
    if last_event == "":
      c0_time = end - start
  con.close()
  return c0_time / (end - start) * 100


### Parse Arguments
argvs = sys.argv
argc  = len(argvs)

print "ARGVS = (" + ", ".join(argvs) + ")"
# print "ARGC  = %d" % argc

ncpus  = multiprocessing.cpu_count()
scrdir = os.path.dirname(__file__)

cpu    = 32               # ARG2
event  = 'cpu-cycles'     # ARG3
offset = 10.0             # ARG4
length = 0.1              # ARG5

if argc >= 2:
  input = argvs[1]
if argc >= 3:
  cpu   = int(argvs[2])
if argc >= 4:
  event = argvs[3]
if argc >= 5:
  offset = float(argvs[4])
if argc == 6:
  length = float(argvs[5])
if argc >  6:
  print "Invalid Arguments"
  quit()

print "cpu = %d, event = %s, offset = %f, length = %f" % (cpu, event, offset, length)

### Create DB
dbs  = [ scrdir+"/../perf.db/"+os.path.basename(input)+".%02d" % i for i in range(ncpus) ]

if not os.path.isdir(scrdir+"/../perf.db"):
    os.makedirs(scrdir+"/../perf.db")

if not os.path.isfile(dbs[0]):
  ### Create DB
  cons = [ sqlite3.connect(db) for db in dbs ]
  
  ### Create Table
  sql = u"""
  create table perf_event (
    comm  TEXT,
    pid   INTEGER,
    cpu   INTEGER,
    time  REAL,
    event TEXT,
    addr  TEXT,
    sym   TEXT,
    bin   TEXT
  )
  """
  
  for i in range(ncpus):
    cons[i].execute(sql)
  
  ### Insert Data
  for i in range(3):
    reader = csv.reader(open(input+"_"+str(i)+".csv", 'rb'), delimiter=';')
    sql = u"insert into perf_event values (?, ?, ?, ?, ?, ?, ?, ?)"
    for idx, row in enumerate(reader):
      row[2] = int(re.search('[0-9]+', row[2]).group(0))
      cons[idx%ncpus].execute(sql, row)

  ### Close DB
  for i in range(ncpus):
    cons[i].commit()
    cons[i].close()

pdbs  = [ scrdir+"/../perf.db/"+os.path.basename(input)+"_p.%02d" % i for i in range(cpu) ]
if not os.path.isfile(pdbs[0]):
  ### Create DB
  cons = [ sqlite3.connect(db) for db in pdbs ]
  
  ### Create Table
  sql = u"""
  create table perf_event (
    comm  TEXT,
    pid   INTEGER,
    cpu   INTEGER,
    time  REAL,
    event TEXT,
    info  TEXT
  )
  """
  
  for i in range(cpu):
    cons[i].execute(sql)
  
  ### Insert Data
  reader = csv.reader(open(input+"_p.csv", 'rb'), delimiter=';')
  sql = u"insert into perf_event values (?, ?, ?, ?, ?, ?)"
  for row in reader:
    row[2] = int(re.search('[0-9]+', row[2]).group(0))
    cons[row[2]%cpu].execute(sql, row)

  ### Close DB
  for i in range(cpu):
    cons[i].commit()
    cons[i].close()

# ### Create Cursor
# curs = []
# for i in range(ncpus):
#   curs.append(cons[i].cursor())

# ### Show Table
# for i in range(ncpus):
#   for row in curs[i].execute(u"select * from perf_event"):
#     # print ', '.join(row)
#     print row

### Main
if __name__ == '__main__':

  ### Create Process Pool
  p = multiprocessing.Pool()

  ### Get Time Range
  result0 = p.map(gettime, dbs)
  time_range = reduce_gettime(result0)
  print "TIME Range = ", time_range

  # ### Get Function List
  # result1 = p.map(getfunclist, dbs)
  # funclist = reduce_getfunclist(result1)
  # print "Num of Functions = %d" % len(funclist)

  ### Search for Certain Range
  start = time_range[0] + offset
  end   = start + length

  ### Count CPU events
  if event in [ "cpu-cycles", "instructions", "cache-misses" ]:
    args = []
    for i in range(ncpus):
      args.append((dbs[i], event, cpu, start, end))

    result2 = p.map(analyze_events, args)
    summary = reduce_analyze_events(result2)

    cpu_events = numpy.array([ 0 for i in range(cpu) ])

    for key in summary.keys():
      cpu_events += summary[key]
      summary[key] = numpy.append(summary[key], numpy.sum(summary[key]))

    cpu_events_ratio = cpu_events/float(sum(cpu_events))*100

  elif event in [ "mpki", "ipc" ]:
    if event == "mpki":
      event1 = "cache-misses"
      event2 = "instructions"
    elif event == "ipc":
      event1 = "instructions"
      event2 = "cpu-cycles"

    args = []
    for i in range(ncpus):
      args.append((dbs[i], event1, cpu, start, end))
    for i in range(ncpus):
      args.append((dbs[i], event2, cpu, start, end))

    result2 = p.map(analyze_events, args)

    summary  = {}
    summary1 = reduce_analyze_events(result2[0:ncpus-1])
    summary2 = reduce_analyze_events(result2[ncpus:ncpus*2-1])

    cpu_events  = numpy.array([ 0 for i in range(cpu) ])
    cpu_events1 = numpy.array([ 0 for i in range(cpu) ])
    cpu_events2 = numpy.array([ 0 for i in range(cpu) ])

    for key in summary1.keys():
      tmp = numpy.array([], dtype=numpy.float64)
      if summary2.has_key(key):
        cpu_events1 += summary1[key]
        cpu_events2 += summary2[key]
        for idx, num in enumerate(summary2[key]):
          if num == 0:
            tmp = numpy.append(tmp, 0.0)
          else:
            tmp = numpy.append(tmp, summary1[key][idx] / float(num))
        else:
          tmp = numpy.append(tmp, numpy.sum(summary1[key]) / float(numpy.sum(summary2[key])))
        summary[key] = tmp
    cpu_events_ratio = numpy.array([], dtype=numpy.float64)
    for idx, num in enumerate(cpu_events2):
      if num == 0:
        cpu_events_ratio = numpy.append(cpu_events_ratio, 0)
      else:
        cpu_events_ratio = numpy.append(cpu_events_ratio, cpu_events1[idx]/float(cpu_events2[idx]))
    else:
      cpu_events_ratio = numpy.append(cpu_events_ratio, sum(cpu_events1) / float(sum(cpu_events2)))
  else:
    quit()
    

  ### CPU running ratio
  args = []
  for cpuid in range(cpu):
    args.append((pdbs[cpuid], start, end))
  cpurunning = p.map(analyze_cstate, args)
  for cpuid in range(cpu):
    if cpurunning[cpuid] == 100.0 and cpu_events[cpuid] == 0:
      cpurunning[cpuid] = 0.0

  ### Create CPU list for output
  cpulist = []
  for cpuid in range(cpu):
    if cpurunning[cpuid] >= 0.01 or cpu_events_ratio[cpuid] >= 0.01:
      cpulist.append(cpuid)

  ### Display result
  for cpuid in cpulist:
    print "CPU%03d" % cpuid,
  else:
    print " TOTAL"

  for cpuid in cpulist:
    print "%6.2f" % cpurunning[cpuid],
  else:
    print "      ", "CPU C0-State Ratio[%]"

  for cpuid in cpulist:
    print "%6.2f" % cpu_events_ratio[cpuid],
  else:
    if event in [ "cpu-cycles", "instructions", "cache-misses" ]:
      print "%6.2f" % 100, "%s[%%]" % event
    elif event in [ "mpki", "ipc" ]:
      print "%6.2f" % cpu_events_ratio[cpu], "%s" % event

  for cpuid in cpulist:
    print "======",
  else:
    print "======"

  #print summary.items()
  #print cpu_events1
  #print cpu_events2


  for key, value in sorted(summary.items(), key=lambda x:x[1][cpu], reverse=True):
    if event in [ "cpu-cycles", "instructions", "cache-misses" ]:
      for cpuid in cpulist:
        if cpu_events[cpuid]:
          tmp = value[cpuid]/float(cpu_events[cpuid])*100
          print "%6.2f" % tmp,
        else:
          print "%6.2f" % 0,
      else:
        tmp = value[cpu]/float(sum(cpu_events))*100
        print "%6.2f" % tmp,
    elif event in [ "mpki", "ipc" ]:
      for cpuid in cpulist:
        print "%6.2f" % value[cpuid],
      else:
        print "%6.2f" % value[cpu],
    print "%10s;" % key

  ### Save Result
  writer = csv.writer(open('perf_analyze.csv', 'wb'), delimiter='\t')

  writer.writerow(["NAME"] + [ "CPU%03d" % i for i in range(cpu) ] + ["TOTAL"])
  writer.writerow(["C0-State Ratio[%]"] + cpurunning + ["nan"])
  writer.writerow(["%s" % event] + cpu_events_ratio.tolist() + ["100.0"])
  
  for key, value in sorted(summary.items(), key=lambda x:x[1][cpu], reverse=True):
    row = [key]
    if event in [ "cpu-cycles", "instructions", "cache-misses" ]:
      for cpuid in range(cpu):
        if cpu_events[cpuid]:
          row.append(value[cpuid]/float(cpu_events[cpuid])*100)
        else:
          row.append(0.0)
      else:
        row.append(value[cpu]/float(sum(cpu_events))*100)
    elif event in [ "mpki", "ipc" ]:
      for cpuid in range(cpu):
        row.append(value[cpuid])
      else:
        row.append(value[cpu])
    writer.writerow(row)
