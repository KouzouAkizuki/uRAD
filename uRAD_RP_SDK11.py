# uRAD_RP_SDK11.py - Library for controlling uRAD SHIELD
# Created by Victor Torres, Diego Gaston - uRAD 2018

import spidev
from time import sleep, time
from gpiozero import OutputDevice
import struct
import math

global configuration, NtarMax, get_distance, get_velocity, get_SNR, get_I, get_Q, get_movement, results_packetLen, results
global command_loadConfiguration, command_detection, command_turnON, command_turnOFF, command_ready, command_results, command_I, command_Q, ACK, read_timeout, tx_1byte

NtarMax = 5
get_distance = False
get_velocity = False
get_SNR = False
get_I = False
get_Q = False
get_movement = False
results_packetLen = NtarMax*3*4+2
results = [0] * (NtarMax*3*4+2)

command_loadConfiguration = [14]
command_detection = [15]
command_turnON = [16]
command_turnOFF = [17]
command_ready = [18]
command_results = [19]
command_I = [20]
command_Q = [21]
ACK = 170
read_timeout = 0.200
tx_1byte = [0]

PinTurnOn = OutputDevice(17)
SlaveSelect = OutputDevice(27)
PinTurnOn.off()
SlaveSelect.off()

spi = spidev.SpiDev() # Create spi object
spi_speed = 1000000

def loadConfiguration(mode, f0, BW, Ns, Ntar, Rmax, MTI, Mth, Alpha, distance_true, velocity_true, SNR_true, I_true, Q_true, movement_true):
	
	global configuration, get_distance, get_velocity, get_SNR, get_I, get_Q, get_movement
	configuration = [0] * 8
	
	f0Min = 5
	f0Max = 195
	f0Max_CW = 245
	BWMin = 50
	BWMax = 240
	NsMin = 50
	NsMax = 200
	RmaxMax = 100
	VmaxMax = 75
	AlphaMin = 3
	AlphaMax = 25

	# SPI configuration
	spi.open(0,0) # open spi port 0, device (CS) 0
	spi.max_speed_hz = spi_speed
	spi.mode = 0b01 # mode of operation 0b[CPOL][CPHA]
	SlaveSelect.on()

	# Check correct values
	if ((mode == 0) or (mode > 4)):
		mode = 3
	if ((f0 > f0Max) and (mode != 1)):
		f0 = f0Min
	elif ((f0 > f0Max_CW) and (mode == 1)):
		f0 = f0Min
	elif (f0 < f0Min):
		f0 = f0Min
	BW_available = BWMax - f0 + f0Min
	if ((BW < BWMin) or (BW > BW_available)):
		BW = BW_available
	if ((Ns < NsMin) or (Ns > NsMax)):
		Ns = NsMax
	if ((Ntar == 0) or (Ntar > NtarMax)):
		Ntar = 1
	if ((mode != 1) and ((Rmax < 1) or (Rmax > RmaxMax))):
		Rmax = RmaxMax
	elif ((mode == 1) and (Rmax > VmaxMax)):
		Rmax = VmaxMax
	if ((MTI > 1) or (MTI < 0)):
		MTI = 0
	if ((Mth < 1) or Mth > 4):
		Mth = 4
	if (Alpha < AlphaMin):
		Alpha = AlphaMin
	elif (Alpha > AlphaMax):
		Alpha = AlphaMax
	Mth-=1
	
	# Create configuration register
	configuration[0] = ((mode << 5) + (f0 >> 3)) & 0b11111111
	configuration[1] = ((f0 << 5) + (BW >> 3)) & 0b11111111
	configuration[2] = ((BW << 5) + (Ns >> 3)) & 0b11111111
	configuration[3] = ((Ns << 5) + (Ntar << 2) + (Rmax >> 6)) & 0b11111111
	configuration[4] = ((Rmax << 2) + MTI) & 0b11111111 
	configuration[5] = (((Mth << 6) + (Alpha << 1)) & 0b11111111) + 0b00000001
	configuration[6] = 0
	if (distance_true):
		configuration[6] += 0b10000000
		get_distance = True
	if (velocity_true):
		configuration[6] += 0b01000000
		get_velocity = True
	if (SNR_true):
		configuration[6] += 0b00100000
		get_SNR = True
	if (I_true):
		configuration[6] += 0b00010000
		get_I = True
	if (Q_true):
		configuration[6] += 0b00001000
		get_Q = True
	if (movement_true):
		configuration[6] += 0b00000100
		get_movement = True

	CRC = ((configuration[0] + configuration[1] + configuration[2] + configuration[3] + configuration[4] + configuration[5] + configuration[6])) & 0b11111111
	configuration[7] = CRC

	# Send configuration by SPI
	try:
		rx_ACK = [0]
		t0 = time()
		ti = time()
		while ((rx_ACK[0] != ACK) and ((ti-t0) < read_timeout)):
			SlaveSelect.off()
			sleep(0.0005)
			spi.xfer([command_loadConfiguration[0]])
			sleep(0.0005)
			spi.xfer([configuration[0], configuration[1], configuration[2], configuration[3], configuration[4], configuration[5], configuration[6], configuration[7]])
			sleep(0.0015)
			rx_ACK = spi.xfer(tx_1byte)
			SlaveSelect.on()
			sleep(0.0005)
			ti = time()
		if (rx_ACK[0] == ACK):
			spi.close()
			return 0
		else:
			spi.close()
			return -1
	except:
		spi.close()
		return -2
			
def detection():

	# SPI configuration
	spi.open(0,0) # open spi port 0, device (CS) 0
	spi.max_speed_hz = spi_speed
	spi.mode = 0b01 # mode of operation 0b[CPOL][CPHA]
	SlaveSelect.on()
	
	if (get_distance or get_velocity or get_SNR):
		NtarDetected = 0
		buff_temp = [0]*4
		distance = [0]*NtarMax
		velocity = [0]*NtarMax
		SNR = [0]*NtarMax
		movement = False
	else:
		NtarDetected = 0
		distance = []
		velocity = []
		SNR = []
		movement = False

	if (get_I or get_Q):
		mode = (configuration[0] & 0b11100000) >> 5
		Ns = ((configuration[2] & 0b00011111) << 3) + ((configuration[3] & 0b11100000) >> 5)
		Ns_temp = Ns
		if (mode == 3):
			Ns_temp *= 2
		elif (mode == 4):
			Ns_temp += Ns_temp + 2*math.ceil(0.75 * Ns_temp)
		if (get_I):
			I = [0]*Ns_temp
		else:
			I = []
		if (get_Q):
			Q = [0]*Ns_temp
		else:
			Q = []
	else:
		I = []
		Q = []
	
	try:
		rx_ACK = [0]
		t0 = time()
		ti = time()
		while ((rx_ACK[0] != ACK) and ((ti-t0) < read_timeout)):
			SlaveSelect.off()
			#sleep(0.0005)
			spi.xfer([command_detection[0]])
			sleep(0.0015)
			rx_ACK = spi.xfer(tx_1byte)
			SlaveSelect.on()
			#sleep(0.0005)
			ti = time()
		if ((ti-t0) >= read_timeout):
			spi.close()
			return -1, [], []

		# Results are ready?
		rx_ACK = [0]
		t0 = time()
		ti = time()
		while ((rx_ACK[0] != ACK) and ((ti-t0) < read_timeout)):
			SlaveSelect.off()
			#sleep(0.001)
			spi.xfer([command_ready[0]])
			sleep(0.0015)
			rx_ACK = spi.xfer(tx_1byte)
			SlaveSelect.on()
			ti = time()
			'''
			if (rx_ACK[0] != ACK):
				sleep(0.001)
			'''
		if ((ti-t0) >= read_timeout):
			spi.close()
			return -2, [], []

		# Receive results
		if (get_distance or get_velocity or get_SNR or get_movement):
			tx_results = [0] * (NtarMax*3*4+2)
			SlaveSelect.off()
			sleep(0.0005)
			spi.xfer([command_results[0]])
			sleep(0.0005)
			results = bytearray(spi.xfer(tx_results))
			SlaveSelect.on()
			if (len(results) == results_packetLen):
				if (get_distance or get_velocity or get_SNR):
					Ntar_temp = (configuration[3] & 0b00011100) >> 2
					if (get_distance):
						distance[0:Ntar_temp] = struct.unpack('<%df' % Ntar_temp, results[0:4*Ntar_temp])
					if (get_velocity):
						velocity[0:Ntar_temp] = struct.unpack('<%df' % Ntar_temp, results[NtarMax*4:NtarMax*4+4*Ntar_temp])
					SNR[0:Ntar_temp] = struct.unpack('<%df' % Ntar_temp, results[2*NtarMax*4:2*NtarMax*4+4*Ntar_temp])
					NtarDetected = len([i for i in SNR if i > 0])
					if (not get_SNR):
						SNR = [0]*NtarMax
				if (get_movement):
					if (results[NtarMax*12] == 255):
						movement = True
			else:
				spi.close()
				return -3, [], []

		# Receive I,Q
		if (get_I or get_Q):
			total_bytes = 0
			if (Ns % 2 == 0):
				total_bytes += Ns*1.5
				two_blocks_1 = math.floor(Ns*1.5/3)
			else:
				total_bytes += (Ns+1)*1.5
				two_blocks_1 = math.floor((Ns+1)*1.5/3)
			if (mode == 3 or mode == 4):
				two_blocks_2 = two_blocks_1
				total_bytes *= 2
			if (mode == 4):
				Ns_3 = math.ceil(0.75*Ns)
				if (Ns_3 % 2 == 0):
					total_bytes += 2*Ns_3*1.5
					two_blocks_3 = math.floor(Ns_3*1.5/3)
				else:
					total_bytes += 2*(Ns_3+1)*1.5
					two_blocks_3 = math.floor((Ns_3+1)*1.5/3)

			total_bytes = int(total_bytes)

		if (get_I):
			tx_I = [0] * total_bytes
			SlaveSelect.off()
			sleep(0.0005)
			spi.xfer([command_I[0]])
			sleep(0.0005)
			bufferIbytes = bytearray(spi.xfer(tx_I))
			SlaveSelect.on()
			if (len(bufferIbytes) == total_bytes):
				for i in range(two_blocks_1):
					I[i*2+0] = (bufferIbytes[i*3+0] << 4) + (bufferIbytes[i*3+1] >> 4)
					if (i*2+1 <= Ns-1):
						I[i*2+1] = ((bufferIbytes[i*3+1] & 15) << 8) + bufferIbytes[i*3+2]
				if (mode == 3 or mode == 4):
					for i in range(two_blocks_2):
						I[Ns+i*2+0] = (bufferIbytes[(two_blocks_1+i)*3+0] << 4) + (bufferIbytes[(two_blocks_1+i)*3+1] >> 4)
						if (Ns+i*2+1 <= 2*Ns-1):
							I[Ns+i*2+1] = ((bufferIbytes[(two_blocks_1+i)*3+1] & 15) << 8) + bufferIbytes[(two_blocks_1+i)*3+2]
					if (mode == 4):
						for i in range(two_blocks_3):
							I[2*Ns+i*2+0] = (bufferIbytes[(two_blocks_1+two_blocks_2+i)*3+0] << 4) + (bufferIbytes[(two_blocks_1+two_blocks_2+i)*3+1] >> 4)
							if (2*Ns+i*2+1 <= 2*Ns+Ns_3-1):
								I[2*Ns+i*2+1] = ((bufferIbytes[(two_blocks_1+two_blocks_2+i)*3+1] & 15) << 8) + bufferIbytes[(two_blocks_1+two_blocks_2+i)*3+2]
						for i in range(two_blocks_3):
							I[2*Ns+Ns_3+i*2+0] = (bufferIbytes[(two_blocks_1+two_blocks_2+two_blocks_3+i)*3+0] << 4) + (bufferIbytes[(two_blocks_1+two_blocks_2+two_blocks_3+i)*3+1] >> 4)
							if (2*Ns+Ns_3+i*2+1 <= 2*Ns+2*Ns_3-1):
								I[2*Ns+Ns_3+i*2+1] = ((bufferIbytes[(two_blocks_1+two_blocks_2+two_blocks_3+i)*3+1] & 15) << 8) + bufferIbytes[(two_blocks_1+two_blocks_2+two_blocks_3+i)*3+2]
			else:
				spi.close()
				return -4, [], []

		if (get_Q):
			tx_Q = [0] * total_bytes
			SlaveSelect.off()
			sleep(0.0005)
			spi.xfer([command_Q[0]])
			sleep(0.0005)
			bufferQbytes = bytearray(spi.xfer(tx_Q))
			SlaveSelect.on()
			if (len(bufferQbytes) == total_bytes):
				for i in range(two_blocks_1):
					Q[i*2+0] = (bufferQbytes[i*3+0] << 4) + (bufferQbytes[i*3+1] >> 4)
					if (i*2+1 <= Ns-1):
						Q[i*2+1] = ((bufferQbytes[i*3+1] & 15) << 8) + bufferQbytes[i*3+2]
				if (mode == 3 or mode == 4):
					for i in range(two_blocks_2):
						Q[Ns+i*2+0] = (bufferQbytes[(two_blocks_1+i)*3+0] << 4) + (bufferQbytes[(two_blocks_1+i)*3+1] >> 4)
						if (Ns+i*2+1 <= 2*Ns-1):
							Q[Ns+i*2+1] = ((bufferQbytes[(two_blocks_1+i)*3+1] & 15) << 8) + bufferQbytes[(two_blocks_1+i)*3+2]
					if (mode == 4):
						for i in range(two_blocks_3):
							Q[2*Ns+i*2+0] = (bufferQbytes[(two_blocks_1+two_blocks_2+i)*3+0] << 4) + (bufferQbytes[(two_blocks_1+two_blocks_2+i)*3+1] >> 4)
							if (2*Ns+i*2+1 <= 2*Ns+Ns_3-1):
								Q[2*Ns+i*2+1] = ((bufferQbytes[(two_blocks_1+two_blocks_2+i)*3+1] & 15) << 8) + bufferQbytes[(two_blocks_1+two_blocks_2+i)*3+2]
						for i in range(two_blocks_3):
							Q[2*Ns+Ns_3+i*2+0] = (bufferQbytes[(two_blocks_1+two_blocks_2+two_blocks_3+i)*3+0] << 4) + (bufferQbytes[(two_blocks_1+two_blocks_2+two_blocks_3+i)*3+1] >> 4)
							if (2*Ns+Ns_3+i*2+1 <= 2*Ns+2*Ns_3-1):
								Q[2*Ns+Ns_3+i*2+1] = ((bufferQbytes[(two_blocks_1+two_blocks_2+two_blocks_3+i)*3+1] & 15) << 8) + bufferQbytes[(two_blocks_1+two_blocks_2+two_blocks_3+i)*3+2]
			else:
				spi.close()
				return -5, [], []

		spi.close()
		return 0, [NtarDetected, distance, velocity, SNR, movement], [I, Q]
	
	except:
		spi.close()
		return -6, [], []

def turnON():

	# SPI configuration
	spi.open(0,0) # open spi port 0, device (CS) 0
	spi.max_speed_hz = spi_speed
	spi.mode = 0b01 # mode of operation 0b[CPOL][CPHA]
	SlaveSelect.on()

	try:	
		PinTurnOn.on()
		sleep(0.05)
		rx_ACK = [0]
		t0 = time()
		ti = time()
		while ((rx_ACK[0] != ACK) and ((ti-t0) < read_timeout)):
			SlaveSelect.off()
			sleep(0.0005)
			spi.xfer([command_turnON[0]])
			sleep(0.0015)
			rx_ACK = spi.xfer(tx_1byte)
			SlaveSelect.on()
			sleep(0.0005)
			ti = time()
		if (rx_ACK[0] == ACK):
			spi.close()
			return 0
		else:
			spi.close()
			return -1
	except:
		spi.close()
		return -2

def turnOFF():

	# SPI configuration
	spi.open(0,0) # open spi port 0, device (CS) 0
	spi.max_speed_hz = spi_speed
	spi.mode = 0b01 # mode of operation 0b[CPOL][CPHA]
	SlaveSelect.on()

	try:
		rx_ACK = [0]
		t0 = time()
		ti = time()
		while ((rx_ACK[0] != ACK) and ((ti-t0) < read_timeout)):
			SlaveSelect.off()
			sleep(0.0005)
			spi.xfer([command_turnOFF[0]])
			sleep(0.0015)
			rx_ACK = spi.xfer(tx_1byte)
			SlaveSelect.on()
			sleep(0.0005)
			ti = time()
		if (rx_ACK[0] == ACK):
			PinTurnOn.off()
			spi.close()
			return 0
		else:
			spi.close()
			return -1
	except:
		spi.close()
		return -2
