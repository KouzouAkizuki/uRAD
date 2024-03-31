import uRAD_RP_SDK11
import multiprocessing
from multiprocessing import	Process, Manager, shared_memory, Condition

import numpy as np

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

if __name__ == '__main__':
    raw_data_size_IQ        =   np.dtype(np.float64).itemsize*2*Ns
    raw_data_size_normal    =   np.dtype(np.float64).itemsize*Ns

    Rx_Data_ready   =   Condition()
    
    Raw_Data_mem    =   shared_memory.SharedMemory(create=True, size=raw_data_size_IQ, name='RawData')
    Raw_Data        =   np.ndarray(shape=(2,Ns), dtype=np.float64, buffer=Raw_Data_mem.buf)

    Read=Process(target=Urad_Samples, args=(Rx_Data_ready,))

    Read.start()
    Read.join()


print("xd")
