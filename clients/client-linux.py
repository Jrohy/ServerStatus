# -*- coding: utf-8 -*-
# Update by : https://github.com/tenyue/ServerStatus
# 支持Python版本：2.6 to 3.5
# 支持操作系统： Linux, OSX, FreeBSD, OpenBSD and NetBSD, both 32-bit and 64-bit architectures


SERVER = "127.0.0.1"
PORT = 35601
USER = "USER" 
PASSWORD = "USER_PASSWORD"
INTERVAL = 1 #更新间隔


import socket
import time
import string
import math
import re
import os
import json
import subprocess
import collections
import platform
import io

def get_uptime():
	f = open('/proc/uptime', 'r')
	uptime = f.readline()
	f.close()
	uptime = uptime.split('.', 2)
	time = int(uptime[0])
	return int(time)

def get_memory():
	re_parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB')
	result = dict()
	for line in open('/proc/meminfo'):
		match = re_parser.match(line)
		if not match:
			continue;
		key, value = match.groups(['key', 'value'])
		result[key] = int(value)

	MemTotal = float(result['MemTotal'])
	MemFree = float(result['MemFree'])
	Cached = float(result['Cached'])
	MemUsed = MemTotal - (Cached + MemFree)
	SwapTotal = float(result['SwapTotal'])
	SwapFree = float(result['SwapFree'])
	return int(MemTotal), int(MemUsed), int(SwapTotal), int(SwapFree)

def get_hdd():
	p = subprocess.check_output(['df', '-Tlm', '--total', '-t', 'ext4', '-t', 'ext3', '-t', 'ext2', '-t', 'reiserfs', '-t', 'jfs', '-t', 'ntfs', '-t', 'fat32', '-t', 'btrfs', '-t', 'fuseblk', '-t', 'zfs', '-t', 'simfs', '-t', 'xfs']).decode("Utf-8")
	total = p.splitlines()[-1]
	used = total.split()[3]
	size = total.split()[2]
	return int(size), int(used)

def get_load():
	return os.getloadavg()[0]

def get_custom_msg():
	file_path = "customMsg.txt"
	if not os.path.exists(file_path):
		open(file_path, 'w').close()                   #文件不存在则创建
	try:
		custom_file = io.open(file_path, "r", encoding="utf-8")   #用io.open设置encoding来兼容python2和python3
		custom_file.readlines()                        #读取一行测试能否成功，失败则以windows的gbk编码读取
		custom_file.seek(0, 0)                         #重新设置文件读取指针到开头
	except:
		custom_file = io.open(file_path, "r", encoding="gbk")

	result = ""  
	for line in custom_file.readlines():                #依次读取每行  
	    line = line.strip()                             #去掉每行头尾空白  
	    if not len(line):                               #判断是否是空行
	        continue                                    #是的话，跳过不处理  
	    result += (line + " ")                            
	custom_file.close()
	return result

def get_time():
	stat_file = file("/proc/stat", "r")
	time_list = stat_file.readline().split(' ')[2:6]
	stat_file.close()
	for i in range(len(time_list))  :
		time_list[i] = int(time_list[i])
	return time_list

def delta_time():
	x = get_time()
	time.sleep(INTERVAL)
	y = get_time()
	for i in range(len(x)):
		y[i]-=x[i]
	return y

def get_cpu():
	t = delta_time()
	st = sum(t)
	if st == 0:
		st = 1
	result = 100-(t[len(t)-1]*100.00/st)
	return round(result)

class Traffic:
	def __init__(self):
		self.rx = collections.deque(maxlen=10)
		self.tx = collections.deque(maxlen=10)
	def get(self):
		f = open('/proc/net/dev', 'r')
		net_dev = f.readlines()
		f.close()
		avgrx = 0; avgtx = 0

		for dev in net_dev[2:]:
			dev = dev.split(':')
			if dev[0].strip() == "lo" or dev[0].find("tun") > -1:
				continue
			dev = dev[1].split()
			avgrx += int(dev[0])
			avgtx += int(dev[8])

		self.rx.append(avgrx)
		self.tx.append(avgtx)
		avgrx = 0; avgtx = 0

		l = len(self.rx)
		for x in range(l - 1):
			avgrx += self.rx[x+1] - self.rx[x]
			avgtx += self.tx[x+1] - self.tx[x]

		avgrx = int(avgrx / l / INTERVAL)
		avgtx = int(avgtx / l / INTERVAL)

		return avgrx, avgtx

def liuliang():
    NET_IN = 0
    NET_OUT = 0
    with open('/proc/net/dev') as f:
        for line in f.readlines():
            netinfo = re.findall('([^\s]+):[\s]{0,}(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', line)
            if netinfo:
                if netinfo[0][0] == 'lo' or 'tun' in netinfo[0][0] or netinfo[0][1]=='0' or netinfo[0][9]=='0':
                    continue
                else:
                    NET_IN += int(netinfo[0][1])
                    NET_OUT += int(netinfo[0][9])
    return NET_IN, NET_OUT

def get_network(ip_version):
	if(ip_version == 4):
		HOST = "ipv4.google.com"
	elif(ip_version == 6):
		HOST = "ipv6.google.com"
	try:
		s = socket.create_connection((HOST, 80), 2)
		return True
	except:
		pass
	return False

if __name__ == '__main__':
	socket.setdefaulttimeout(30)
	while 1:
		try:
			print("Connecting...")
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((SERVER, PORT))
			data = s.recv(1024)
			if data.find("Authentication required") > -1:
				s.send(USER + ':' + PASSWORD + '\n')
				data = s.recv(1024)
				if data.find("Authentication successful") < 0:
					print(data)
					raise socket.error
			else:
				print(data)
				raise socket.error

			print(data)
			data = s.recv(1024)
			print(data)

			timer = 0
			check_ip = 0
			if data.find("IPv4") > -1:
				check_ip = 6
			elif data.find("IPv6") > -1:
				check_ip = 4
			else:
				print(data)
				raise socket.error

			traffic = Traffic()
			traffic.get()
			while 1:
				CPU = get_cpu()
				NetRx, NetTx = traffic.get()
				NET_IN, NET_OUT = liuliang()
				Uptime = get_uptime()
				Load = get_load()
				CustomMsg = get_custom_msg()
				MemoryTotal, MemoryUsed, SwapTotal, SwapFree = get_memory()
				HDDTotal, HDDUsed = get_hdd()

				array = {}
				if not timer:
					array['online' + str(check_ip)] = get_network(check_ip)
					timer = 10
				else:
					timer -= 1*INTERVAL

				array['custom'] = CustomMsg
				array['uptime'] = Uptime
				array['load'] = Load
				array['memory_total'] = MemoryTotal
				array['memory_used'] = MemoryUsed
				array['swap_total'] = SwapTotal
				array['swap_used'] = SwapTotal - SwapFree
				array['hdd_total'] = HDDTotal
				array['hdd_used'] = HDDUsed
				array['cpu'] = CPU
				array['network_rx'] = NetRx
				array['network_tx'] = NetTx
				array['network_in'] = NET_IN
				array['network_out'] = NET_OUT

				s.send("update " + json.dumps(array) + "\n")
		except KeyboardInterrupt:
			raise
		except socket.error:
			print("Disconnected...")
			# keep on trying after a disconnect
			s.close()
			time.sleep(3)
		except Exception as e:
			print("Caught Exception:", e)
			s.close()
			time.sleep(3)
