__author__ = 'parryrm'
import matplotlib.pyplot as plt
from matplotlib.pyplot import pause, ion, ioff
from numpy.random import random
import sys
sys.ps1 = 'SOMETHING'

n = 10
S = random((n, n))


S = S * S.T
S = S > .5
print S

ion()
fig = plt.figure()
ax = fig.add_subplot(111)
ax.spy(S, origin='upper')
cursor, = ax.plot(0, 0, color='green', markersize=10, marker='s')

for i in range(n):
    print "cursor =", i
    cursor.set_xdata(i)
    cursor.set_ydata(i)
    fig.canvas.draw()
    pause(0.1)

ioff()

