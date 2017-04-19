import matplotlib.pyplot as plt
import sqlite3 as sql
import datetime
from matplotlib import dates


DBNAME = '../example.db'

# Import sql data

conn = sql.connect(DBNAME)
cur = conn.cursor()

cur.execute('select x,ch2,ch4 from lab7 where error=? and x>?',(0,1489622400.0,))
myvals = cur.fetchall()

cur.execute('select x,ch2,ch4 from lab7 where error=? and x>?',(0,1489622400.0,))
myvals = cur.fetchall()

timestamps = []
temperatures = []
laser_volt = []
for item in myvals:
    timestamps.append(item[0])
    temperatures.append(item[1])
    laser_volt.append(item[2])

dts = map(datetime.datetime.fromtimestamp,timestamps)
fds = dates.date2num(dts)

fig = plt.figure()
ax = fig.add_subplot(211)
temp_line = ax.plot(fds,temperatures,'+--', markersize = 3)
plt.ylabel('Temperature [Celsius]')

#Format
hfmt = dates.DateFormatter('%d/%m %H:%M')
ax.xaxis.set_major_formatter(hfmt)
plt.xticks(rotation='vertical')
ax.xaxis.grid(True)
plt.subplots_adjust(bottom=.2   )

bx = ax.twinx()
laser_line = bx.plot(fds,laser_volt,'o--',color='orange',markersize=3)
plt.ylabel('Voltage [V]')

cx = fig.add_subplot(212)

plt.show()