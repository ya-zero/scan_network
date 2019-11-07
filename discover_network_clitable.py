# -*- coding: utf-8 -*-
# опросить устройства в 192.168.0.0/24
# опросить устройство и сохранить информацию о оборудовании
#"Device Type","Mac","IP Address","Vlan","Boot ver","firmware ver"
#"SNR-S2965-24T","f8:f0:82:75:07:7c","7.0.3.5(R0241.0124)","7.2.25","192.168.0.195"
# заполнить таблицу device.db  sqlite  --> mysql
# сделать многозадачность 
import logging
import telnetlib
import ipaddress
import subprocess
import yaml
import sys
import clitable
import netmiko
from pprint import pprint
from netmiko.ssh_exception import NetMikoTimeoutException
from paramiko.ssh_exception import SSHException

# список ip уже изученных устройств
def all_ready_scanned (scanned_files):
 scanned_device=[]
 for list_vendor in scanned_files:
   yml_device= yaml.load(open(list_vendor))
   for device in yml_device:
      for key,items in device.items():
          if key == 'Ip':
           scanned_device.append(items)
 return scanned_device

#проверка доступности хоста
def check_device (host):
      result=subprocess.run(['ping',str(host),'-c','1','-W','1'],stdout=subprocess.DEVNULL).returncode
      # если returncode == 0  значит узел доступен.
      return result
#подключение к устройству
def connection_to_dev(device,command):
    try:
      with netmiko.ConnectHandler(**device,verbose=True) as ssh:
          print ('>>>try connect to host',device['ip'])
          #print ('prompt:',ssh.find_prompt())
          ssh.send_command('disable clipaging')
          result=ssh.send_command(command)
          ssh.send_command('enable clipaging')
          if 'Incomplete' in result:
              print ('Error in command')
      return result
    except:
      print ('>>>netmiko_return_error',device['ip'])

# парсим по шаблону и команде
def parse_output(output,vendor,command):#TextFsm parse output from switch
    try: 
      cli_table = clitable.CliTable('index','templates')
    except:
      print ('Warning TextFsm !!! >>>templates index error')
    # если комманда соотвествует только одному вендору то можно
    # не указывать  его
    attributes = {'Vendor':vendor,'Command':command}
    try:
      cli_table.ParseCmd(output,attributes)
    except:
      print('Warning TextFsm !!! >>> attribute parse error')
    return  cli_table

# как узнать вендора. сканируем сеть два раза.  н
# либо запуск по параметрам из коммандой строки. если ввели argv не то, но выводим хелп,
# также хелп доступен  по -h /? --help.
# включаем debug для netmiko
#logging.basicConfig(filename='test.log',level=logging.DEBUG)
#logger=logging.getLogger("netmiko")

################################################################
try:
  vendor=sys.argv[1]
  ipaddr=sys.argv[2]
  command=' '.join(sys.argv[3:])
  print ('Vendor:',vendor,'\nIpaddr',ipaddress.ip_network(ipaddr),'\nCommand:',command)
except:
 print('''неверные аргументы
- первый аргумент Vendor : cisco_like
- второй аргумент  диапазон адресов, если нужен один адрес , то указываем /32 маску
- третий аргумент 'show version' / 'show switch'
''')

################################################################
#подсеть для изучения
subnet=ipaddress.ip_network(ipaddr)
#default_param={'device_type':'cisco_ios_telnet','username':'mgmt','password':'1valera2'}#параметры для подключения к оборудованию
default_param={'device_type':'cisco_ios_telnet','username':'admin','password':'reinfokom'}#параметры для подключения к оборудованию
scanned_files=['device_dlink.yml','device_snr.yml']
# одно изученно устройство
devices_dict={}
#список отсканированных устройств из диапазаона подсети
devices_list=[]

scanned_device = all_ready_scanned(scanned_files)

for host in subnet:
#  if str(host) not in scanned_device: # если хост есть среди уже изученных то пропускаем
    if check_device(host)==0:
      default_param.update({'ip':str(host)})
      result_command=connection_to_dev(default_param,command)
      devices_dict={}
      if result_command:
        result_parse=parse_output(result_command,vendor,command)
        if result_parse.size >= 1 :
         for key,param in zip(list(result_parse.header),list(result_parse.row)):
                  devices_dict[key]=param
         devices_dict.update({'Ip':str(host)})
         devices_list.append(devices_dict)
    else: print ('no icmp to host',host)
# записть результата в файл
with open('device_sw.yml','a') as f:
 yaml.dump(devices_list,f,default_flow_style=False)

