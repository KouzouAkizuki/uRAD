import uRAD_RP_SDK11
import multiprocessing
from multiprocessing import	Process, Manager, shared_memory, Condition

import numpy as np

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

#### URAD Parameters
mode 	= 1 	# 1->Doppler, 2->Diente de sierra, 3-> Triangular, 4->Triangular con doble frecuencia
f0		= 5 	# Frecuencia inicial en MHz, ->25.xxxGHz, [5 - 245]MHz
BW		= 240	# Ancho de banda en MHZ, max 240MHz, Bwmax=245-f0
Ns		= 200	# Samples   [50 - 200]
Ntar	= 3		# Number of Target of interest [1 - 5]
Rmax	= 100	# Rango,    0m-75m for 1, 1m-100m for 2,3,4
MTI		= 0		# Moving Target Indicator (Elimina informacion de los objetivos estaticos), for 2,3,4
Mth		= 0		# Sensibilidad del uRAD [1 low - 4 high]
Alpha	= 10	# Algoritmo CA-CFAR, discriminacion de objetivos para menores a Alpha(dB)

distance_true 	= False
velocity_true 	= False
SNR_true		= False
I_true			= True
Q_true			= True
movement_true   = False

def CloseProgram():
    return_code = uRAD_RP_SDK11.turnOFF()
    if(return_code != 0):
        exit()

def Urad_Samples(Data_Condition):

    return_code = uRAD_RP_SDK11.turnON()
    if(return_code != 0):
        CloseProgram()

    return_code = uRAD_RP_SDK11.loadConfiguration(mode, f0, BW, Ns, Ntar, Rmax, MTI, Mth, Alpha, distance_true, velocity_true, SNR_true, I_true, Q_true, movement_true)
    if(return_code != 0):
        CloseProgram()

    while True:
        return_code, results, raw_results = uRAD_RP_SDK11.detection()
        if (return_code != 0):
            CloseProgram()
            
        with Data_Condition:
            
        
            Raw_Data_mem    =   shared_memory.SharedMemory(name='RawData')
            Raw_Data        =   np.ndarray((2,Ns), dtype=np.float64, buffer=Raw_Data_mem.buf)

            Raw_Data[0]=np.array(raw_results[0])/4095-1/2
            Raw_Data[1]=np.array(raw_results[1])/4095-1/2

            Raw_Data_mem.close()
            Data_Condition.notify()

def update_1(graph,data_y,num):
        
        Y_mem = shared_memory.SharedMemory(name=data_y)

        Y_data = np.ndarray((num), dtype=np.float64, buffer=Y_mem.buf)

        graph.setData(np.array(range(1,num,1)),np.array(Y_data))

        Y_mem.close()   

def update_2(graph,data_x,data_y,num):
        
        X_mem = shared_memory.SharedMemory(name=data_x)
        Y_mem = shared_memory.SharedMemory(name=data_y)

        X_data = np.ndarray((num), dtype=np.float64, buffer=X_mem.buf)
        Y_data = np.ndarray((num), dtype=np.float64, buffer=Y_mem.buf)

        graph.setData(np.array(X_data),np.array(Y_data))

        X_mem.close()    
        Y_mem.close()   

def Graph_Pyqtgraph_Core(Title_1):
    app = pg.mkQApp(Title_1)
    win = pg.GraphicsLayoutWidget(show=True, title=Title_1)
    win.resize(1000,600)
    win.setWindowTitle(Title_1)

    # Enable antialiasing for prettier plots
    pg.setConfigOptions(antialias=True)


    p1 = win.addPlot()
    curve_1 = p1.plot(pen='y')
    p1.setYRange(1, -1, padding=0)
    p1.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted
    
    
    timer_1 = QtCore.QTimer()
    timer_1.timeout.connect(lambda:   update_1(curve_1,'RawData',Ns))
    
    timer_1.start()


    pg.exec()



if __name__ == '__main__':
    raw_data_size_IQ        =   np.dtype(np.float64).itemsize*2*Ns
    raw_data_size_normal    =   np.dtype(np.float64).itemsize*Ns

    Rx_Data_ready   =   Condition()
    
    Raw_Data_mem    =   shared_memory.SharedMemory(create=True, size=raw_data_size_IQ, name='RawData')
    Raw_Data        =   np.ndarray(shape=(2,Ns), dtype=np.float64, buffer=Raw_Data_mem.buf)

    Read=Process(target=Urad_Samples, args=(Rx_Data_ready,))
    Graph=Process(target=Graph_Pyqtgraph_Core, args=('Samples'))


    Read.start()
    Read.join()


print("xd")
