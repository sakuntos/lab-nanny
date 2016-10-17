"""
Animate live:

Plotting utility for SerialCommManager.


The fast plotting is done by only updating the changing parts of the plot
(see bastibe.de/2013-05-30-speeding-up-matplotlib.html )
Author: David Paredes
2016
"""
import SerialCommManager as SCM
import matplotlib.pyplot as plt
import numpy as np
import time
from collections import deque
import matplotlib.animation as animation
from serial.serialutil import SerialException
plt.ion()

class AnimationPlot:
    """ adapted from http://electronut.in/plotting-real-time-data-from-arduino-using-python/
    """
    def __init__(self, maxLen=1000,number_of_queues=8):
        # open serial port
        self.plotter = SCM.SerialCommManager(0.01, verbose=False)
        self.number_of_queues = number_of_queues
        self.y_buffers = [deque([0.0]*maxLen) for element in range(self.number_of_queues)]
        self.ax = deque([0.0]*maxLen)

        self.maxLen = maxLen

    def addToBuf(self, buf, val):
        """ Adds a value to a buffer

        If the buffer is full (number of elements> self.maxLen) then we "pop" a value from the list,
        to keep the buffer size constant.

        :param buf:
        :param val:
        :return:
        """
        if len(buf) < self.maxLen:
            buf.append(val)
        else:
            buf.pop()
            buf.appendleft(val)

    def add(self, data):
        """ Adds data to the plotting object.

        The x-axis data is the first element, and the y-axis elements from different channels are the rest..


        :param data:
        :return:
        """
        #assert(len(data) == 9)
        self.addToBuf(self.ax, data[0])
        for ii in range(self.number_of_queues):
            self.addToBuf(self.y_buffers[ii],data[ii+1])


    def acquire_data(self):
        """ Acquires the data from the self.plotter SerialDataFetcher instance.

        The data is put into the buffers self.y_buffers using the self.add function

        :return:
        """
        try:
            #st = time.clock()
            t, (C0, C1,C2,C3,C4,C5,C6,C7) = self.plotter.poll_arduino()
            #print 'Time spent reading {}'.format(time.clock()-st)
            if(len([t,C0,C1,C2,C3,C4,C5,C6,C7]) == 9):
                self.add([0,C0*3.3/4095,C1*3.3/4095,C2*3.3/4095,C3*3.3/4095,
                          C4*3.3/4095,C5*3.3/4095,C6*3.3/4095,C7*3.3/4095])


            #print 'Time spent updating {}'.format(time.clock()-st)
        except KeyboardInterrupt:
            print('exiting?')
        return t

    def update_plot(self,lines,axes,fig):
        """ Method to update only the lines and the background patch of the plots.

        This code speeds up the plotting.

        :param lines:
        :param axes:
        :param fig:
        :return:
        """
        for ii,(line,ax) in enumerate(zip(lines, axes)):
            line.set_data(range(self.maxLen), self.y_buffers[ii])
            ax.draw_artist(ax.patch)
            ax.draw_artist(line)
        fig.canvas.update()
        fig.canvas.flush_events()

    def error_plot(self,lines,axes,fig,ON=True):
        """ When an error occurs, change the color of the lines to red.

        :param lines:
        :param axes:
        :param fig:
        :param ON: Entering the error changes the lines to red. When ON=False (exiting), changes them back to black
        :return:
        """
        if ON:
            color='r'
        else:
            color='k'

        for ii,(line,ax) in enumerate(zip(lines, axes)):
            line.set_data(range(self.maxLen), self.y_buffers[ii])
            line.set_color(color)
            ax.draw_artist(ax.patch)
            ax.draw_artist(line)
        fig.canvas.update()
        fig.canvas.flush_events()

    def update(self,frameNum,lines,axes,fig):
        self.acquire_data()
        self.update_plot(lines,axes,fig)


def initialise_plot(ax,style):
        return ax.plot([],[],style,animated=True)[0]

def main():
    """ Get data logger data and plot it. Convert raw 12-bit ADC data to voltage """
    st2 = time.clock()
    maxLen=100
    number_acquisitions=2
    animationPlot = AnimationPlot(maxLen)

    plt.show(block=False)

    fig, axes = plt.subplots(ncols=4,nrows=2,sharey=True, sharex=True,figsize=(15,6))
    axes = [item for sublist in axes for item in sublist]
    fig.show()
    fig.canvas.draw()

    styles = ['k','k','k','k','k','k','k','k']

    lines = [initialise_plot(ax,style) for ax,style in zip(axes,styles)]

    fig.canvas.draw()


    init_time = animationPlot.update(0,lines,axes,fig)

    #Calibrate axis
    plt.title('calibrating')

    plt.title('live')
    for number,ax in enumerate(axes):
        ax.set_ylim(0,3.3)
        ax.set_xlim(0,maxLen)
        label = 'A{0:d} (V)'.format(number)
        ax.set_ylabel(label)
    #myText=axes[7].text(maxLen/2,1,'Some')
    fig.canvas.draw()

    st = 0
    fps=0
    while True:
        try: #Maybe put this "try" in the update function? I don't know how it would deal with events.
            st = time.clock()
            animationPlot.update(0,lines,axes,fig)
            # myText.set_text('{}'.format(fps))
            fps = 1.0/(time.clock()-st)
            print 'fps {}'.format(fps)

        except SerialException:
            animationPlot.error_plot(lines,axes,fig,True)
            print 'Lost connection on {}, curr time {}'.format(st, time.clock())
            time.sleep(1)
            animationPlot.error_plot(lines,axes,fig,False)


    print('exiting.')


if __name__ == '__main__':
    main()