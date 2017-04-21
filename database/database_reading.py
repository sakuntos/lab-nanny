import matplotlib.pyplot as plt
import sqlite3 as sql
import datetime
import time
from matplotlib import dates

def time_from_timestamps(timestamps):
    dts = map(datetime.datetime.fromtimestamp,timestamps)
    return dates.date2num(dts)

DBNAME = '../example.db'

# Import sql data

MAXTIME = time.time()-604800


conn = sql.connect(DBNAME)
cur = conn.cursor()

cur.execute('select x,ch2,ch3,ch4 from lab7 where error=? and x>?',(0,MAXTIME,))
myvals = cur.fetchall()

cur.execute("SELECT time FROM metadata_list where metadata LIKE '%closed%' and time>?",(MAXTIME,))
disconnect_vals = cur.fetchall()
cur.execute("SELECT time FROM metadata_list where metadata NOT LIKE '%closed%' and time>?",(MAXTIME,))
reconnect_vals = cur.fetchall()

timestamps = []
temperatures = []
trap_volt = []
repump_volt = []

for item in myvals:
    timestamps.append(item[0])
    temperatures.append(item[1])
    trap_volt.append(item[2])
    repump_volt.append(item[3])
disconnect_times = [val[0] for val in disconnect_vals]
reconnect_times = [val[0] for val in reconnect_vals]
fds = time_from_timestamps(timestamps)
d_times = time_from_timestamps(disconnect_times)
c_times = time_from_timestamps(reconnect_times)

fig = plt.figure()
ax = fig.add_subplot(111)
temp_line = ax.plot(fds,temperatures,'+', markersize = 3,color='dodgerblue')
for ii in c_times:
    plt.axvline(x=ii,ls='--',color='dimgray')
for ii in d_times:
    plt.axvline(x=ii,ls='--',color='lightcoral')
plt.ylabel('Temperature [Celsius]',color='dodgerblue')

#Format
hfmt = dates.DateFormatter('%d/%m %H:%M')
ax.xaxis.set_major_formatter(hfmt)
plt.xticks(rotation='vertical')
ax.xaxis.grid(True)
plt.subplots_adjust(bottom=.2   )


bx = ax.twinx()
trap_line = bx.plot(fds, trap_volt, 'o--', color='orange', markersize=3,
                    label='trap')
repumper_line = bx.plot(fds, repump_volt, '<--', color='indianred', markersize=3,
                        label='repumper')
plt.legend()
plt.ylabel('Voltage [V]', color='orange')


plt.show()