# coding: utf8

import os
import shutil
import struct
import sys
import zipfile
from collections import namedtuple
import gc


try:
	from SARC.packet import Packet as SARCPacket
except ImportError: # in tools/ folder
	sys.path.append("../")
	from SARC.packet import Packet as SARCPacket
import utils

Data = namedtuple("Data",['time_stamp','packet_length','packet'])

datas = []
WorkingDirectory = '__RFETMP__/'
TimeUpdatePacketId = 78
ChangeGameStateId = 30

def read_int(f):
	data = f.read(4)
	if len(data) < 4:
		return None
	return struct.unpack('>i', data)[0]

def write_int(f, data):
	f.write(struct.pack('>i', data))

def read_tmcpr(file_name):
	global datas
	datas = []
	with open(file_name, 'rb') as f:
		while True:
			time_stamp = read_int(f)
			if time_stamp is None:
				break
			packet_length = read_int(f)
			datas.append(Data(time_stamp, packet_length, f.read(packet_length)))
	print('Packet count =', len(datas))

def set_day_time(day_time):
	global datas
	packet = SARCPacket()
	packet.write_varint(TimeUpdatePacketId)
	packet.write_long(0)
	packet.write_long(-day_time)  # If negative sun will stop moving at the Math.abs of the time
	bytes = packet.flush()
	time_data = Data(0, len(bytes), bytes)
	success = False
	for i in range(len(datas)):
		if datas[i].packet_length == 0:
			datas[i] = time_data
			success = True
			break
	print('Set daytime operation finished, success = {}'.format(success))

def clear_weather():
	global datas
	counter = 0
	new_datas = []
	for i in range(len(datas)):
		recorded = True
		packet = SARCPacket()
		packet.receive(datas[i].packet)
		packet_id = packet.read_varint()
		if packet_id == ChangeGameStateId:
			reason = packet.read_ubyte()
			if reason in [1, 2, 7, 8]:
				recorded = False
		if recorded:
			new_datas.append(datas[i])
		else:
			counter += 1
	del datas
	gc.collect()
	datas = new_datas
	print('Clear weather operation finished, deleted {} packets'.format(counter))

def save_file():
	global datas
	with open(WorkingDirectory + 'recording.tmcpr', 'wb') as f:
		for data in datas:
			write_int(f, data.time_stamp)
			write_int(f, data.packet_length)
			f.write(data.packet)
	print('Update recording.mcpr finished')
	with open(WorkingDirectory + 'recording.tmcpr.crc32', 'w') as f:
		f.write(str(utils.crc32f(WorkingDirectory + 'recording.tmcpr')))
	print('Update recording.tmcpr.crc32 finished')
	global input_file_name
	output_file_name = 'FIX_' + input_file_name
	counter = 2
	while os.path.isfile(output_file_name):
		output_file_name = 'FIX{}_{}'.format(counter, input_file_name)
		counter += 1
	print('Zipping new .mcpr file to {}'.format(output_file_name))
	zipf = zipfile.ZipFile(output_file_name, 'w', zipfile.ZIP_DEFLATED)
	for file in os.listdir(WorkingDirectory):
		zipf.write(WorkingDirectory + file, arcname=file)
	zipf.close()
	shutil.rmtree(WorkingDirectory)


print('A script to fix missing time update packet and delete remaining weather packet in PCRC 0.3-alpha and below')
print('It can be optimize a lot but I\'m too lazy xd. whatever it works')
input_file_name = None
if len(sys.argv) >= 2:
	input_file_name = sys.argv[1]
while True:
	if input_file_name is None:
		input_file_name = input('Input .mcpr file name: ')
	if os.path.isfile(input_file_name):
		break
	else:
		print('File "{}" not found'.format(input_file_name))
	input_file_name = None
print('File Name = {}'.format(input_file_name))
do_set_daytime = input('Set daytime? (0: no; 1: yes) = ') == '1'
if do_set_daytime:
	day_time = int(input('Daytime = '))
do_clear_weather = input('Clear weather? (0: no; 1: yes) = ') == '1'
print('Cleaning')
if os.path.isdir(WorkingDirectory):
	shutil.rmtree(WorkingDirectory)
os.mkdir(WorkingDirectory)
print('Extracting')
zipf = zipfile.ZipFile(input_file_name)
zipf.extractall(WorkingDirectory)
zipf.close()
print('Reading')
read_tmcpr(WorkingDirectory + 'recording.tmcpr')
print('Init finish')
if do_set_daytime:
	set_day_time(day_time)
if do_clear_weather:
	clear_weather()
print('Operation finished, saving file')
save_file()
input('Finish! press enter to exit')