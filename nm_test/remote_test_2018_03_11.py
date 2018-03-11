import pyipmi
import pyipmi.interfaces
import os
import re
import datetime
import os.path
import time
import math
import numpy
import mmap
import array
import getopt
import sys
from os_parameters_define import *
from utility_function import *
from nm_ipmi_raw_to_str import *
from error_messages_define import *

## Global Test Item Switch form NM_000- NM_014, PECI_000-PECI_014 : Enable = 0 , Disable = 1
NM_TEST_EN = [ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, \
              # below are PECI_000 ~ PECI_014 (NM_TEST_STS[15~29])
              ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, \
              # below are SMART_CLST_001 (NM_TEST_EN[30])
              ENABLE, \
              # below are PM_002~PM_006 (NM_TEST_EN[31~35])
              ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, \
              # below are DC_CYCLE, RESET_CYCLE (NM_TEST_EN[36~37])
              ENABLE, ENABLE, \
              # below is MCTP_001~MCTP_008 (NM_TEST_EN[38~45])
              ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, \
              # below is PTU_001~PTU_004 (NM_TEST_EN[46~49])
              ENABLE, ENABLE, ENABLE, ENABLE, \
              # below is NM_WS_001~NM_WS_010 (NM_TEST_EN[50~59])
              ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, \
              # below is PTT_003~PTT_004 (NM_TEST_EN[60~61])
              ENABLE, ENABLE, \
              # below is BTG_003 (NM_TEST_EN[62])
              ENABLE]
## Global Test Status
NM_TEST_STS = [NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, \
               # below are PECI_000 ~ PECI_014 test status (NM_TEST_STS[15~29])
               NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, \
               # below are SMART_CLST_001 (NM_TEST_STS[30])
               NONE, \
              # below are PM_002~PM_006(NM_TEST_EN[31~35])
               NONE, NONE, NONE, NONE, NONE, \
              # below are DC_CYCLE, RESET_CYCLE (NM_TEST_EN[36~37])
               NONE, NONE, \
              # below is MCTP_001~MCTP_008 (NM_TEST_EN[38~45])
               NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, \
              # below is PTU_001~PTU_004 (NM_TEST_EN[46~49])
               NONE, NONE, NONE, NONE, \
              # below is NM_WS_001~NM_WS_010 (NM_TEST_EN[50~59])
               NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, \
              # below is PTT_003~PTT_004 (NM_TEST_EN[60~61])
               NONE, NONE, \
              # below is BTG_003 (NM_TEST_EN[62])
               NONE]

##Function :  Send IPMB cmd via aardvark and return response data 
def send_ipmb_aardvark(ipmi , netfn, raw):
     print('Send IPMB raw cmd via Aardvark : raw 0x%x %s' % (netfn , raw))
     raw_bytes = array.array('B', [int(d, 0) for d in raw[0:]])
     rsp = ipmi.raw_command(lun, netfn, raw_bytes.tostring())
     print('Response Data: ' + ' '.join('%02x' % ord(d) for d in rsp))
     return rsp

##Function : SSH CMD SWITCH FOR WIN AND LINUX OS
def ssh_send_cmd_switch( background_run,  PROGRAM_PATH , STRESS_CMD , LOG_SAVE ):
     if(DEBUG_OS_TYPE == os_linux):
          if(background_run == background_run_enable):
               os.system( LINUX_BACKGROUND_RUN + 'ssh ' + os_user + '@' + os_ip_addr +' -t sudo ' + PROGRAM_PATH + ' ' + STRESS_CMD + ' &')
          elif(background_run == background_run_disable):
               if(LOG_SAVE == 1):
                    os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + PROGRAM_PATH + ' ' + STRESS_CMD + ' > ' + SSH_LOG_PATH_LINUX)
               else:
                    os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + PROGRAM_PATH + ' ' + STRESS_CMD)
          else:
               DEBUG('ssh_send_cmd_switch : ERROR!!  Incorrect type of background_run !!')
               return ERROR               
     elif(DEBUG_OS_TYPE == os_win):
          if(background_run == background_run_enable):
               os.system( WIN_BACKGROUND_RUN + WIN_SSH_PATH + os_user + '@' + os_ip_addr +' -t sudo ' + PROGRAM_PATH + ' ' + STRESS_CMD + ' &')
          elif(background_run == background_run_disable):
               if(LOG_SAVE == 1):
                    os.system(WIN_SSH_PATH + os_user + '@'+ os_ip_addr + ' -t sudo ' + PROGRAM_PATH + ' ' + STRESS_CMD + ' > ' + SSH_LOG_PATH_WIN)                 
               else:
                    os.system(WIN_SSH_PATH + os_user + '@'+ os_ip_addr + ' -t sudo ' + PROGRAM_PATH + ' ' + STRESS_CMD)         
          else:
               DEBUG('ssh_send_cmd_switch : ERROR!!  Incorrect type of background_run !!')
               return ERROR            
     else:
          return ERROR
          
     return SUCCESSFUL

## Function : Detect if System boot into OS
  # Return : OS_STS = 0 = OS NOT Ready, OS_STS = 1 = OS READY
def check_os_available():
     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     #TEST_CMD  = 'ls /home/howard/follow_me_project/get_position.py'
     OS_STS = 0
     # Check PTU floder data is ready
     ssh_send_cmd_switch(background_run_disable,  SSH_CMD_PATH_EMPTY , PTUGEN_PATH, LOG_SAVE_EN )
     # Check Test List file :
     NM_TEST_LIST, NM_TEST_FILE, SSH_LOG = get_test_list_path()
     # Read Test Item from file
     if os.path.isfile(SSH_LOG) :
          DEBUG('file exist')
          file = open(SSH_LOG, 'r')
          with open(SSH_LOG, "r") as ins:
              test_list = []
              for line in ins:
                  test_list.append(line.rstrip('\n'))
          file.close()
          DEBUG(test_list)
          if(len(test_list) == 0):
              DEBUG('SSH get file not exist') 
              return OS_STS 
     else:
         DEBUG('file not exist')        
         return OS_STS
     #Check Key word  "PTU File name"
     sts = search_keyword_file(SSH_LOG, PTUGEN_PATH)         
     if(sts != SUCCESSFUL ):
         DEBUG('file key word check error!!!')
         return OS_STS
     #Check Key word  "cannot access"
     sts = search_keyword_file(SSH_LOG, 'cannot access')
     if(sts == SUCCESSFUL ):
         DEBUG('Erro ! OS file NOT ready to use !!!')
         return OS_STS         
         
     # OS Tool exist and Ready to use
     OS_STS = 1
     return OS_STS


##Function :  GET NM TEST LIST
def get_test_list_path():
     ## DEBUG_OS_TYPE is hard code define in os_parameters_define.py 
     if(DEBUG_OS_TYPE == os_linux):
          NM_TEST_LIST = NM_TEST_LIST_LINUX
          NM_TEST_FILE = NM_TEST_FILE_LINUX
          SSH_LOG      = SSH_LOG_PATH_LINUX
     elif(DEBUG_OS_TYPE == os_win):
          NM_TEST_LIST = NM_TEST_LIST_WIN
          NM_TEST_FILE = NM_TEST_FILE_WIN
          SSH_LOG      = SSH_LOG_PATH_WIN
     else:
          DEBUG('NO This OS')
          return ERROR, ERROR, ERROR

     DEBUG('NM_TEST_LIST :'+ NM_TEST_LIST)
     DEBUG('NM_TEST_FILE :'+ NM_TEST_FILE)
     DEBUG('SSH_LOG :'+ SSH_LOG)
     
     return NM_TEST_LIST, NM_TEST_FILE, SSH_LOG

##Function :  Globla PTU parameters detect:
def ptu_parameters_detect():
     # Detect Platform via Get DID
     sps_version, platform, dcmi, nm, image  = get_device_id_py(ipmi)
     if(platform == 9):
          # Change OS PTU location for Greenlow
          DEBUG('SPS FW is run in Greenlow E3 Platform, change PTU parameters')
          return ERROR
     elif(platform == 10):
          DEBUG('SPS FW is run in Purley E5 Platform, change PTU parameters')
          # Change OS PTU location for Purley
          PTUGEN_P100_30SECS = '-p 100 -t 30'
          PTUMON_3SECS = '-t 3'
          PTUMON_PATH  = PURLEY_PTUMON_PATH
          PTUGEN_PATH  = PURLEY_PTUGEN_PATH
     elif(platform == 16):
          DEBUG('SPS FW is run in Mehlow E3 Platform, change PTU parameters')
          # Change OS PTU location for Mehlow
          PTUGEN_P100_30SECS = '-P100 -D80'
          PTUMON_3SECS = '-D3'
          PTUMON_PATH  = MEHLOW_PTUMON_PATH
          PTUGEN_PATH  = MEHLOW_PTUGEN_PATH
     else:
          DEBUG('NO This platform')
          return ERROR, ERROR, ERROR, ERROR

     return PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH

## Function : Netfun : 0x0 , cmd = 0x01 IPMI Chassis Power status, Get current system power status  
def get_chassis_status_py(ipmi ):
     netfn, get_chassis_status_raw = get_chassis_power_status_raw_to_str_py( )
     rsp = send_ipmb_aardvark(ipmi , netfn , get_chassis_status_raw )
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     power_status    = get_bits_data_py( ord(rsp[1]) , 0 , 1)
     if(power_status == 1):
         DEBUG('Power is ON, power status bit = %d' %power_status)
     elif(power_status ==0):
         DEBUG('Power is OFF, power status bit = %d' %power_status)
     else:
         DEBUG('ERROR!')
         return ERROR
     
     return ipmi, power_status

## Function : Netfun : 0x0 , cmd = 0x02 IPMI Chassis Power control cmd : OFF= 0 /ON = 1/ CYCLE =2 / Reset = 3
def chassis_control_py(ipmi, control ):
     netfn, chassis_control_raw = chassis_control_raw_to_str_py( control)
     rsp = send_ipmb_aardvark(ipmi , netfn , chassis_control_raw )
     sts = ipmi_resp_analyst_py( ord(rsp[0]), Chassis )
     if(sts != SUCCESSFUL ):
         return ERROR
     
     return ipmi, rsp

## Function : 0xD9H, Send RAW PMbus Cmd
def send_raw_pmbus_cmd_extend_py(ipmi, msg_type , pec_report, pec_en, sensor_bus, target_addr, mux_addr, mux_ch, mux_config, trans_protocol, write_len, read_len, command):
     netfn, d9h_raw = d9h_raw_to_str_py(msg_type , pec_report, pec_en, sensor_bus, target_addr, mux_addr, mux_ch, mux_config, trans_protocol, write_len, read_len, command)
     # Send 0xDFh with command option
     rsp = send_ipmb_aardvark(ipmi , netfn , d9h_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return rsp

## Function : 0xD9H, Send RAW PMbus Cmd
def send_raw_pmbus_write_cmd_extend_py(ipmi, msg_type , pec_report, pec_en, sensor_bus, target_addr, mux_addr, mux_ch, mux_config, trans_protocol, write_len, read_len, command):
     netfn, d9h_raw = d9h_set_raw_to_str_py(msg_type , pec_report, pec_en, sensor_bus, target_addr, mux_addr, mux_ch, mux_config, trans_protocol, write_len, read_len, command)
     # Send 0xDFh with command option
     rsp = send_ipmb_aardvark(ipmi , netfn , d9h_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return rsp

## Function : 0xD7H, Set PSU configuation Cmd
def set_psu_configuation_py(ipmi, domain, psu1_addr, psu2_addr, psu3_addr, psu4_addr, psu5_addr, psu6_addr, psu7_addr, psu8_addr ):
     netfn, d7h_raw = d7h_set_raw_to_str_py(domain, psu1_addr, psu2_addr, psu3_addr, psu4_addr, psu5_addr, psu6_addr, psu7_addr, psu8_addr)
     # Send 0xDFh with command option
     rsp = send_ipmb_aardvark(ipmi , netfn , d7h_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return rsp

## Function : PMBus Proxy : Get PMbus Version
def get_pmbus_version_py(ipmi , bus , target_addr ):
     write_len = 1
     read_len = PMBUS_GET_VERSION_READ_LEN
     pmbus_get_version_cmd = PMBUS_GET_VERSION
     rsp = send_raw_pmbus_cmd_extend_py(ipmi, d9h_trans_type_read_byte, d9h_pec_report, d9h_pec_en, bus , target_addr , 0 , 0 , 0 , d9h_trans_potocol_pmbus , write_len , read_len , pmbus_get_version_cmd)
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     pmbus_version = ord(rsp[4])
     return pmbus_version

## Function : PMBus Proxy : Read_EIN
def get_pmbus_read_ein_py(ipmi , bus , target_addr ):
     write_len = 1
     read_len = PMBUS_READ_EIN_READ_LEN
     pmbus_get_version_cmd = PMBUS_READ_EIN
     rsp = send_raw_pmbus_cmd_extend_py(ipmi, d9h_trans_type_block_read, d9h_pec_report, d9h_pec_en, bus , target_addr , 0 , 0 , 0 , d9h_trans_potocol_pmbus , write_len , read_len , pmbus_get_version_cmd)
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
         
     return rsp

## Function : PMBus Proxy : Read_EOUT
def get_pmbus_read_eout_py(ipmi , bus , target_addr ):
     write_len = 1
     read_len = PMBUS_READ_EOUT_READ_LEN
     pmbus_get_version_cmd = PMBUS_READ_EOUT
     rsp = send_raw_pmbus_cmd_extend_py(ipmi, d9h_trans_type_block_read, d9h_pec_report, d9h_pec_en, bus , target_addr , 0 , 0 , 0 , d9h_trans_potocol_pmbus , write_len , read_len , pmbus_get_version_cmd)
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
         
     return rsp

## Function : PMBus Proxy : Read_PIN
def get_pmbus_read_pin_py(ipmi , bus , target_addr ):
     write_len = 1
     read_len = PMBUS_READ_PIN_READ_LEN
     pmbus_get_version_cmd = PMBUS_READ_PIN
     rsp = send_raw_pmbus_cmd_extend_py(ipmi, d9h_trans_type_read_word, d9h_pec_report, d9h_pec_en, bus , target_addr , 0 , 0 , 0 , d9h_trans_potocol_pmbus , write_len , read_len , pmbus_get_version_cmd)
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     # Read_PIN is linear data format , X = Y*2^N
     # Calculate N : High Byte bit[7:3]
     N  = get_bits_data_py( ord(rsp[5]) , 3 , 5)
     # Transfer N data to 2's complement value
     N_2complement = two_complement(N , 5)
     # Calculate Y : High Byte bit[2:0]
     Y1  = get_bits_data_py( ord(rsp[5]) , 0 , 3)
     Y1  = Y1 * 256
     Y2  = ord(rsp[4])
     Y   = Y1 + Y2   
	 # Calculate pin from rsp Byte[6:5] value, total 2 bytes
     psu_pin = Y*math.pow(2,N_2complement)
     DEBUG('PSU pin = %6d' %psu_pin)     
     return psu_pin

## Function : PMBus Proxy : Read_POUT
def get_pmbus_read_pout_py(ipmi , bus , target_addr ):
     write_len = 1
     read_len = PMBUS_READ_POUT_READ_LEN
     pmbus_get_version_cmd = PMBUS_READ_POUT
     rsp = send_raw_pmbus_cmd_extend_py(ipmi, d9h_trans_type_read_word, d9h_pec_report, d9h_pec_en, bus , target_addr , 0 , 0 , 0 , d9h_trans_potocol_pmbus , write_len , read_len , pmbus_get_version_cmd)
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     # Read_POUT is linear data format , X = Y*2^N
     # Calculate N : High Byte bit[7:3]
     N  = get_bits_data_py( ord(rsp[5]) , 3 , 5)
     # Transfer N data to 2's complement value
     N_2complement = two_complement(N , 5)
     # Calculate Y : High Byte bit[2:0]
     Y1  = get_bits_data_py( ord(rsp[5]) , 0 , 3)
     Y1  = Y1 * 256
     Y2  = ord(rsp[4])
     Y   = Y1 + Y2   
	 # Calculate pin from rsp Byte[6:5] value, total 2 bytes
     psu_pout = Y*math.pow(2,N_2complement)
     DEBUG('PSU pout = %6d' %psu_pout)     
     return psu_pout

## Function : Netfun: 0x30 , CMD :0x26H, MESDC Get Version cmd
def mesdc_get_version_py(ipmi):
     netfn, mesdc_26h_raw = mesdc_26h_raw_to_str_py()
     # Send MESDC 0x26h with command option
     rsp = send_ipmb_aardvark(ipmi , netfn , mesdc_26h_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), Controller_OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     print('mesdc_get_version_py : fwsts1 HFS = 0x%x%x%x%x' %(ord(rsp[15]),ord(rsp[14]) ,ord(rsp[13]) ,ord(rsp[12])))
     print('mesdc_get_version_py : fwsts2 = 0x%x%x%x%x' %(ord(rsp[19]),ord(rsp[18]) ,ord(rsp[17]) ,ord(rsp[16])))
     # Response byte 0
     current_status    = get_bits_data_py( ord(rsp[12]) , 0 , 4)
     DEBUG('mesdc_get_version_py : current_status = %d' %current_status)
     manufacture_mode    = get_bits_data_py( ord(rsp[12]) , 4 , 1)
     DEBUG('mesdc_get_version_py : manufacture_mode = %d' %manufacture_mode)
     fpt_bad    = get_bits_data_py( ord(rsp[12]) , 5 , 1)
     DEBUG('mesdc_get_version_py : fpt_bad = %d' %fpt_bad)
     operation_state1    = get_bits_data_py( ord(rsp[12]) , 6 , 2)
     # Response byte 1
     operation_state2    = get_bits_data_py( ord(rsp[13]) , 0 , 1)
     operation_state     = operation_state2*4 + operation_state1
     DEBUG('mesdc_get_version_py : operation_state = %d' %operation_state)
     init_complete       = get_bits_data_py( ord(rsp[13]) , 1 , 1)
     DEBUG('mesdc_get_version_py : init_complete = %d' %init_complete)
     recv_fault       = get_bits_data_py( ord(rsp[13]) , 2 , 1)
     DEBUG('mesdc_get_version_py : recv_fault = %d' %recv_fault)
     update_in_process       = get_bits_data_py( ord(rsp[13]) , 3 , 1)
     DEBUG('mesdc_get_version_py : update_in_process = %d' %update_in_process)
     error_code       = get_bits_data_py( ord(rsp[13]) , 4 , 4)
     DEBUG('mesdc_get_version_py : error_code = %d' %error_code)
     # Response byte 2
     operating_mode       = get_bits_data_py( ord(rsp[14]) , 0 , 4)
     DEBUG('mesdc_get_version_py : operating_mode = %d' %operating_mode)
     me_reset_count       = get_bits_data_py( ord(rsp[14]) , 4 , 4)
     DEBUG('mesdc_get_version_py : me_reset_count = %d' %me_reset_count)
     # Response byte 3
     fd0v_status       = get_bits_data_py( ord(rsp[15]) , 0 , 1)
     DEBUG('mesdc_get_version_py : fd0v_status = %d' %fd0v_status)
     cpu_dbg_policy       = get_bits_data_py( ord(rsp[15]) , 1 , 1)
     DEBUG('mesdc_get_version_py : cpu_dbg_policy = %d' %cpu_dbg_policy)
     sku_vio_status       = get_bits_data_py( ord(rsp[15]) , 2 , 1)
     DEBUG('mesdc_get_version_py : sku_vio_status = %d' %sku_vio_status)
     current_bios_region       = get_bits_data_py( ord(rsp[15]) , 3 , 1)
     DEBUG('mesdc_get_version_py : current_bios_region = %d' %current_bios_region)
     d0i3       = get_bits_data_py( ord(rsp[15]) , 7 , 1)
     DEBUG('mesdc_get_version_py : d0i3 = %d' %d0i3)
     # Response byte 5     
     eop        = get_bits_data_py( ord(rsp[17]) , 3 , 1)
     DEBUG('mesdc_get_version_py : EOP = %d' %eop)
     
     return rsp, current_status, operation_state , eop

## Function : Netfun: 0x30 , CMD :0x26H, MESDC Get MCTP statistic cmd
def mesdc_get_mctp_statistic_py(ipmi):
     netfn, mesdc_26h_mctp_statistic_raw = mesdc_26h_mctp_statistic_raw_to_str_py()
     # Send MESDC 0x26h MCTP statistic with command option
     rsp = send_ipmb_aardvark(ipmi , netfn , mesdc_26h_mctp_statistic_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), Controller_OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     print('mesdc_get_mctp_statistic_py : number of mctp end_point discoverd = %d' %ord(rsp[10]))
     number_of_mctp_discoverd = ord(rsp[19])

     return number_of_mctp_discoverd

## Function : Netfun: 0x30 , CMD :0x26H, MESDC Get NM PTU Launch state cmd
def mesdc_get_nm_ptu_launch_state_py(ipmi):
     netfn, mesdc_26h_nm_ptu_launch_state_raw = mesdc_26h_nm_ptu_launch_state_raw_to_str_py()
     # Send MESDC 0x26h MCTP statistic with command option
     rsp = send_ipmb_aardvark(ipmi , netfn , mesdc_26h_nm_ptu_launch_state_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), Controller_OEM )
     if(sts != SUCCESSFUL ):
         return ERROR         
     manufacture_optin    = get_bits_data_py( ord(rsp[10]) , 0 , 1)
     DEBUG('mesdc_get_mctp_statistic_py : manufacture_optin = %d' %manufacture_optin)
     bios_optin    = get_bits_data_py( ord(rsp[10]) , 1 , 1)
     DEBUG('mesdc_get_mctp_statistic_py : bios_optin = %d' %bios_optin)
     bmc_activate    = get_bits_data_py( ord(rsp[10]) , 2 , 1)
     DEBUG('mesdc_get_mctp_statistic_py : bmc_activate = %d' %bmc_activate)     
     bios_activate    = get_bits_data_py( ord(rsp[10]) , 3 , 1)
     DEBUG('mesdc_get_mctp_statistic_py : bmc_activate = %d' %bmc_activate) 
     oem_empty_run    = get_bits_data_py( ord(rsp[10]) , 4 , 1)
     DEBUG('mesdc_get_mctp_statistic_py : oem_empty_run = %d' %oem_empty_run)
     rom_launch    = get_bits_data_py( ord(rsp[10]) , 5 , 1)
     DEBUG('mesdc_get_mctp_statistic_py : rom_launch = %d' %rom_launch)
     bmc_phase_only    = get_bits_data_py( ord(rsp[10]) , 7 , 1)
     DEBUG('mesdc_get_mctp_statistic_py : bmc_phase_only = %d' %bmc_phase_only)
     
     return manufacture_optin, bios_optin, bmc_activate, bios_activate, oem_empty_run, rom_launch, bmc_phase_only     

## Function : 0xDFH, Force SPS FW Recovery to default
def force_me_recovery_py(ipmi, command):
     netfn, dfh_raw = dfh_raw_to_str_py(command)
     # Send 0xDFh with command option
     rsp = send_ipmb_aardvark(ipmi , netfn , dfh_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return SUCCESSFUL

## Function : 0xC8H, Get Platform Power Read
def platform_power( mode, domain, power_domain, policy_id):
     # Read Platform power 5 times
     read_count = 1
     power_average = 0
     energy_acc = 0
     for read_count in range(1, 5):
         #IPMI command 0xC8 read currect power status
         c8h_raw = c8h_raw_to_str( mode, domain, power_domain, policy_id)
         ipmisend1 = ipmi_network_bridge_raw_cmd_header + c8h_raw
         DEBUG(ipmisend1)
         resp = os.popen(ipmisend1).read()
         DEBUG(resp)
         sts = ipmi_resp_analyst( resp, OEM )
         # Check if rsp data correct
         if(sts != SUCCESSFUL ):
              return ERROR
         # Calculate Byte5 value, low byte
         val_high = int('0x'+resp[10],0)*16
         val_low  = int('0x'+resp[11],0)
         power = val_high + val_low
         # Calculate Byte6 value high byte
         val_high = int('0x'+resp[13],0)*16*16*16
         val_low  = int('0x'+resp[14],0)*16*16
         power = power + val_high + val_low
         # Calculate average power
         energy_acc = energy_acc + power
         power_average = energy_acc / read_count
         DEBUG(power_average)
         read_count = read_count + 1

     return power_average

## Function : 0x82H, Get BTG Health cmd
def get_boot_guard_health_py( ipmi ):
     netfn, btg_82h_raw = btg_82h_raw_to_str_py()
     # Send 0x82h with command option
     rsp = send_ipmb_aardvark(ipmi , netfn , btg_82h_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     #Analyst and Decode  BTG Health response data
     force_btg_acm_boot_profile    = get_bits_data_py( ord(rsp[7]) , 5 , 1)
     DEBUG('get_boot_guard_health_py : force_btg_acm_boot_profile = %d' %force_btg_acm_boot_profile)
     pbe_sts    = get_bits_data_py( ord(rsp[8]) , 5 , 1)
     DEBUG('get_boot_guard_health_py : pbe_sts = %d' %pbe_sts)
     enf_sts    = get_bits_data_py( ord(rsp[8]) , 6 , 2)
     DEBUG('get_boot_guard_health_py : enf_sts = %d' %enf_sts)     
     measure_boot    = get_bits_data_py( ord(rsp[9]) , 0 , 1)
     DEBUG('get_boot_guard_health_py : measure_boot = %d' %measure_boot)  
     verify_boot    = get_bits_data_py( ord(rsp[9]) , 1 , 1)
     DEBUG('get_boot_guard_health_py : verify_boot = %d' %verify_boot) 
     btg_disable_in_fpf    = get_bits_data_py( ord(rsp[11]) , 6 , 1)
     DEBUG('get_boot_guard_health_py : btg_disable_in_fpf = %d' %btg_disable_in_fpf) 
     
     return rsp, force_btg_acm_boot_profile, pbe_sts, enf_sts, measure_boot, verify_boot, btg_disable_in_fpf

## Function : 0x70H, Get PTT Capabilty cmd
def get_ptt_version_py( ipmi ):
     netfn, ptt_70h_raw = ptt_70h_raw_to_str_py()
     # Send 0x70h with command option
     rsp = send_ipmb_aardvark(ipmi , netfn , ptt_70h_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     #Analyst PTT version response data
     ptt_version    = ord(rsp[4])
     DEBUG('get_ptt_version_py : ptt_version = %d' %ptt_version)
     ptt_interface_version    = ord(rsp[5])
     DEBUG('get_ptt_version_py : ptt_interface_version = %d' %ptt_interface_version)
     security_version    = ord(rsp[6])
     DEBUG('get_ptt_version_py : security_version = %d' %security_version)
     patch_version    = ord(rsp[7])
     DEBUG('get_ptt_version_py : patch_version = %d' %patch_version)    
     major_version    = ord(rsp[8])
     DEBUG('get_ptt_version_py : major_version = %d' %major_version)
     minor_version    = ord(rsp[9])
     DEBUG('get_ptt_version_py : minor_version = %d' %minor_version)
     
     return ptt_version, ptt_interface_version, security_version, patch_version, major_version, minor_version

## Function : 0x71H, Get PTT Capabilty cmd
def get_ptt_capabilties_py( ipmi ):
     netfn, ptt_71h_raw = ptt_71h_raw_to_str_py()
     # Send 0x71h with command option
     rsp = send_ipmb_aardvark(ipmi , netfn , ptt_71h_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     #Analyst PTT capability
     ptt_support    = get_bits_data_py( ord(rsp[4]) , 6 , 2)
     DEBUG('get_ptt_capabilties_py : ptt_support = %d' %ptt_support)

     return ptt_support

## Function : 0xC8H, Get Platform Power Read 5 times and provide average reading feedback
def read_power_py( ipmi, mode, domain, power_domain, policy_id):
     # Read Platform power 5 times
     read_count = 1
     power_average = 0
     energy_acc = 0
     #lun = 0
     for read_count in range(1, 6):
        netfn, c8h_raw = c8h_raw_to_str_py( mode, domain, power_domain, policy_id)
        rsp = send_ipmb_aardvark(ipmi , netfn , c8h_raw )
        # Calculate current power from rsp Byte[6:5] value, total 2 bytes
        current_power = calculate_byte_value_py(rsp, 5, 2)
        DEBUG('current_power = %6d' %current_power)
	    #energy_acc = energy_acc + ord(rsp[4])
        energy_acc = energy_acc + current_power
	    
     power_average = energy_acc/5
     return power_average

## Function : 0xC0H, Enable/Disable NM Policy Control cmd
def enable_disable_nm_policy_control_py( ipmi, flags, domain, policy_id):
	 netfn, c0h_raw = c0h_raw_to_str_py( flags, domain , policy_id)
	 rsp = send_ipmb_aardvark(ipmi , netfn , c0h_raw )
	 
	 return rsp

## Function : 0xD4H, Get Number of P/T states 
def get_number_of_pt_states(ipmi, control_knob ):
     netfn, d4h_raw = d4h_raw_to_str_py( control_knob )
     rsp = send_ipmb_aardvark(ipmi , netfn , d4h_raw )
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR, ERROR
     if( control_knob == 0):
         p_states = ord(rsp[4])
         t_states = ord(rsp[5])
         return p_states, t_states
     elif(control_knob == 1):
         logical_processor_number =  ord(rsp[4])
         return logical_processor_number
     else:
         DEBUG('control_knob = %d settings error!! ' %control_knob)
         return ERROR, ERROR
     return ERROR, ERROR

## Function : 0xD3H, Get Maximum allowed  P/T states 
def get_max_allowed_pt_states(ipmi, control_knob ):
     netfn, d3h_raw = d3h_raw_to_str_py( control_knob )
     rsp = send_ipmb_aardvark(ipmi , netfn , d3h_raw )
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR, ERROR
     if( control_knob == 0):
         max_allowed_p_states = ord(rsp[4])
         max_allowed_t_states = ord(rsp[5])
         return max_allowed_p_states, max_allowed_t_states
     elif(control_knob == 1):
         max_allowed_logical_processor_number =  ord(rsp[4])
         return max_allowed_logical_processor_number
     else:
         DEBUG('control_knob = %d settings error!! ' %control_knob)
         return ERROR, ERROR
     return ERROR, ERROR
     
## Function : 0xD2H, Set Maximum allowed  P/T states 
def set_max_pt_states_py(ipmi, control_knob , max_p_states, max_t_states ):
     netfn, d2h_raw = d2h_raw_to_str_py( control_knob, max_p_states, max_t_states)
     rsp = send_ipmb_aardvark(ipmi , netfn , d2h_raw )
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     return rsp
     
## Function : 0xD0H, Set Total Power Budget
def set_total_power_budget_py(ipmi, domain , control , power_budget , component_id ):
     netfn, d0h_raw = d0h_raw_to_str_py( domain , control , power_budget , component_id )
     rsp = send_ipmb_aardvark(ipmi , netfn , d0h_raw )
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return rsp

## Function : 0x60H, Set PTU Launch Request 
def set_ptu_launch_request_py(ipmi, request ):
     netfn, ptu_launch_60h_raw = ptu_launch_60h_raw_to_str_py( request )
     rsp = send_ipmb_aardvark(ipmi , netfn , ptu_launch_60h_raw )
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     return rsp

## Function : 0x61H, Set PTU Launch Request 
def get_ptu_launch_result_py(ipmi, domain ):
     netfn, ptu_result_61h_raw = ptu_result_61h_raw_to_str_py( domain )
     rsp = send_ipmb_aardvark(ipmi , netfn , ptu_result_61h_raw )
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     # Calculate max power from rsp Byte[10:9] value, total 2 bytes
     max_power = calculate_byte_value_py(rsp, 9, 2)
     DEBUG('max_power = %6d' %max_power)
     min_power = calculate_byte_value_py(rsp, 11, 2)
     DEBUG('min_power = %6d' %min_power)
     eff_power = calculate_byte_value_py(rsp, 13, 2)
     DEBUG('eff_power = %6d' %eff_power)
     
     return max_power, min_power, eff_power
     
## Function : 0xCBH, Set NM Power Draw Range
def set_nm_power_draw_range_py(ipmi, domain, min_power_draw_range, max_power_draw_range):
     # Coverter minimum power draw range  int value to hex value for byte[6:5]
     min_pwr_range_str = int_to_hex( min_power_draw_range, 2 )
     # Coverter maximum power draw range  int value to hex value for byte[8:7]
     max_pwr_range_str = int_to_hex( max_power_draw_range, 2 )
     # Send 0xCBh cmd
     netfn, cbh_raw =  cbh_raw_to_str_py(domain, min_pwr_range_str, max_pwr_range_str )
     rsp = send_ipmb_aardvark(ipmi , netfn , cbh_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return SUCCESSFUL

## Function : 0xC9H, Get NM capability and platform power Draw Range
def get_platform_power_draw_range_py(ipmi, c9h_domain, c9h_policy_trigger_type, c9h_policy_type, c9h_power_domain):
     netfn, c9h_raw = c9h_raw_to_str_py( c9h_domain, c9h_policy_trigger_type, c9h_policy_type, c9h_power_domain)
     # Send 0xC9h to know Power Draw Rnage
     rsp = send_ipmb_aardvark(ipmi , netfn , c9h_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR, ERROR, ERROR, ERROR
     # Calculate Max power draw range Byte[7:6] value, total 2 bytes
     max_draw_range = calculate_byte_value_py(rsp, 6, 2)
     DEBUG('max_draw_range = %6d' %max_draw_range)
     # Calculate Min power draw range Byte[9:8] value, total 2 bytes
     min_draw_range = calculate_byte_value_py(rsp, 8, 2)
     DEBUG('min_draw_range = %6d' %min_draw_range)
     if(max_draw_range > 0):
         DEBUG('Get Power Draw Range OK')
     else:
         DEBUG('!!! Get Power Draw Range Fail !!!')
         return ERROR, ERROR, ERROR, ERROR
     # Calculate Min correcction time Byte[13:10] value, total 4 bytes
     min_correction_time = calculate_byte_value_py(rsp, 10, 4)
     DEBUG('minimun correction time = %6d' %min_correction_time)
     # Calculate Max correcction time Byte[17:14] value, total 4 bytes
     max_correction_time = calculate_byte_value_py(rsp, 14, 4)
     DEBUG('maxmun correction time = %6d' %max_correction_time)
     if(min_correction_time > 0):
         DEBUG('Get correction time value OK')
     else:
         DEBUG('!!! Get correction time Fail !!!')
         return ERROR, ERROR, ERROR, ERROR


     return  max_draw_range, min_draw_range, min_correction_time, max_correction_time

## Function : 0xC1H, Set NM Policy
def set_nm_power_policy_py(ipmi, domain, policy_enable, policy_id, policy_trigger_type, policy_add, aggressive, storage_mode, alert, shutdown, power_domain, limit_value, min_correction_time, trigger_limit, report_period ):
     # Coverter Limit int value to hex value for byte[9:8]- Policy Target Limit
     limit = int_to_hex( limit_value, 2 )
     # Coverter Correction time Setting from int to hex for byte[13:10]- Correction Time Limit
     correction = int_to_hex( min_correction_time, 4 )
     # Trigger limit Byte[15:14]
     trigger_point = int_to_hex( trigger_limit, 2 )
     if(policy_trigger_type == 0 or policy_trigger_type == 4 or policy_trigger_type == 6 ):
         #trigger_limit = c1h_trigger_limit_null
         trigger_limit = c1h_trigger_limit_null
         DEBUG('set_nm_power_policy note: This policy trigger type %2d is no need to input trigger limit point , so force use default settings = 0' %policy_trigger_type)
         tirgger_point = int_to_hex( trigger_limit, 2 )
     elif(policy_trigger_type == 2 or policy_trigger_type == 3):
         DEBUG('set_nm_power_policy: This trigger type %2d will use 0.1sec be single unit for policy trigger point, so policy trigger point =%2d secs ' %(policy_trigger_type, trigger_limit/10))
         trigger_point = int_to_hex( trigger_limit, 2 )
     elif(policy_trigger_type == 1):
         DEBUG('set_nm_power_policy: This trigger type %2d will use 1 Celsiu be single unit for policy trigger point, so policy trigger point =%2d secs ' %(policy_trigger_type, trigger_limit))
         trigger_point = int_to_hex( trigger_limit, 2 )
     else:
         DEBUG('set_nm_power_policy: ERROR !!! No support this policy trigger type %d' %policy_trigger_type)
         return ERROR
     # Byte[17:16] = Statistics Reporting Period in second = 1sec
     if(report_period > 65535):
         DEBUG('set_nm_power_policy: ERROR!!! report_period settings value %6d to hurge !!' %report_period)
         return ERROR
     statistic_period = int_to_hex( report_period, 2 )
     # Send 0xC1h cmd
     netfn, c1h_raw =  c1h_raw_to_str_py(domain, policy_enable, policy_id, policy_trigger_type, policy_add, aggressive, storage_mode, alert, shutdown, power_domain, limit, correction, trigger_point, statistic_period )
     rsp = send_ipmb_aardvark(ipmi , netfn , c1h_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return SUCCESSFUL

## Function : 0xF2H, Get Limiting Policy ID 
def get_limiting_policy_id(ipmi, domain ):
     netfn, f2h_raw = f2h_raw_to_str_py( domain )
     rsp = send_ipmb_aardvark(ipmi , netfn , f2h_raw )
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     limit_policy_id = ord(rsp[4])
     
     return limit_policy_id
     
## Fucntion : Send IPMI GET Device ID
def get_device_id_py(ipmi):
     netfn, get_did_raw = get_did_raw_to_str_py()
     # Send Get DID to ME
     rsp = send_ipmb_aardvark(ipmi , netfn , get_did_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), App )
     if(sts != SUCCESSFUL ):
         return ERROR
     # Analyst get did resp data format
     # Get Major Version = resp byte4 bits[6:0]
     DEBUG('Get Major Version:')
     marjor_version    = get_bits_data_py( ord(rsp[3]) , 0 , 7)
     DEBUG('get_me_device_id : Marjor_version = %d' %marjor_version)
     # Get Device Available bit : byte4 bit[7] = 1 = device in boot loader mode. = 0 = normal operation mode.
     available_bit     = get_bits_data_py( ord(rsp[3]) , 7 , 1)
     DEBUG('get_me_device_id : Available Bit = %d' % available_bit)
     # Get Minor version (byte5 bit[7:4]) and Milestone version (byte5 bits[3:0])number
     milestone_version     = get_bits_data_py( ord(rsp[4]) , 0 , 4)
     DEBUG('get_me_device_id : milestone_version = %d' %milestone_version)
     minor_version         = get_bits_data_py( ord(rsp[4]) , 3 , 4)
     DEBUG('get_me_device_id : minor_version = %d' %minor_version)
     # Get Build version number byte14=A.B and byte15 bit[7:4] =C, build version = 100A+10B+C
     build_version_AB  = get_bits_data_py( ord(rsp[13]) , 0 , 8)
     DEBUG('get_me_device_id : build_version_AB = %d' %build_version_AB)
     build_version_C   = get_bits_data_py( ord(rsp[14]) , 4 , 4)
     DEBUG('get_me_device_id : build_version_C Bit = %d' %build_version_C)
     sps_version = format(marjor_version, '02x') + '.' + format(minor_version, '02x') + '.' + format(milestone_version, '02x') + '.' + format(build_version_AB,'02x')+format(build_version_C, 'x')
     DEBUG('Current SPS FW version = ' + sps_version )
     # Get byte11 bit[7:0] platform SKU
     platform = get_bits_data_py( ord(rsp[10]) , 0 , 8)
     DEBUG('get_me_device_id : platform = %d' %platform)
     # Get byte13 bit[3:0] DCMI version, bytes13 bit[7:4] = NM version
     nm = get_bits_data_py( ord(rsp[12]) , 0 , 4)
     DEBUG('get_me_device_id : nm = %d' %nm)
     dcmi   = get_bits_data_py( ord(rsp[12]) , 4 , 4)
     DEBUG('get_me_device_id : dcmi = %d' %dcmi)
     # Get byte16 bit[1:0] image flag
     image = get_bits_data_py( ord(rsp[15]) , 0 , 2)
     DEBUG('get_me_device_id : image_sts = %d' %image)
     return sps_version, platform , dcmi , nm , image

## Fucntion : Send IPMI Cold reset
def cold_reset_py(ipmi):
     netfn, cold_reset_raw = cold_reset_raw_to_str_py()
     # Send cold reset
     rsp = send_ipmb_aardvark(ipmi , netfn , cold_reset_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), App )
     if(sts != SUCCESSFUL ):
         return ERROR
         
     return SUCCESSFUL

## Function : Restore SPS FW to manufacture default
def facture_default_py(ipmi, command):
     # Send 0xDFh with command to ME
     sts = force_me_recovery_py(ipmi, command)
     if(sts != SUCCESSFUL ):
         return ERROR
     if(command == 1):
         # Add delay time 5 secs to make sure me go back to stable mode
         time.sleep(10)
         # Check if SPS FW boot into recovery mode.
         # Send Get DID cmd to ME
         sps_version, platform, dcmi, nm, image = get_device_id_py(ipmi)
         # Check resp byte16 - image flag to see if SPS FW run in recover mode
         if(image == get_did_recovery):
              DEBUG('!! SPS FW already running in recovery mode')
              return SUCCESSFUL
         elif(image == get_did_op1):
              DEBUG('SPS FW go back to operation mode and restore to default successfully')
              return ERROR
         elif(image == get_did_op2):
              DEBUG('SPS FW go back to operation mode but OP1 seems borken !!!')
              return ERROR
         elif(image == get_did_flash_err):
              DEBUG('SPI flash seems borken !!!')
              return ERROR
         else:
              DEBUG('COMMAND FAIL !!!')
              return ERROR              
     elif(command == 2):
         # Add delay time 5 secs to make sure me go back to stable mode
         time.sleep(10)
         # Check if SPS FW back to operation mode.
         # Send Get DID cmd to ME
         sps_version, platform, dcmi, nm, image  = get_device_id_py(ipmi)
         DEBUG('facture_default : sps run in status = %d ' %image)
         # Check resp byte16 - image flag to see if SPS FW back to operation mode
         if(image == get_did_recovery):
              DEBUG('!! SPS FW still running in recovery mode after restore to default!!')
              return ERROR
         elif(image == get_did_op1):
              DEBUG('SPS FW go back to operation mode and restore to default successfully')
              return SUCCESSFUL
         elif(image == get_did_op2):
              DEBUG('SPS FW go back to operation mode but OP1 seems borken !!!')
              return ERROR
         elif(image == get_did_flash_err):
              DEBUG('SPI flash seems borken !!!')
              return ERROR
         else:
              DEBUG('COMMAND FAIL !!!')
              return ERROR
     elif(command == 3):
         # Check if PTT status is operational.
         return ERROR
     else:
         DEBUG('The byte4: command parameter is not in support list')
         return ERROR

     return ERROR

## Function : STANDARD IPMI GET SEL TIME CMD
def get_sel_time_py(ipmi):
     netfn, get_sel_time_raw = get_sel_time_raw_to_str_py()
     # Send Get SEL TIME to ME
     rsp = send_ipmb_aardvark(ipmi , netfn , get_sel_time_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), App )
     if(sts != SUCCESSFUL ):
         return ERROR
     # Calculate RTC TIME value Byte[5:2] value, total 4 bytes
     rtc_time = calculate_byte_value_py(rsp, 2, 4)
     DEBUG('rtc_time = %6d' %rtc_time)
     if(rtc_time > 4294967294):
          print('ERROR !!! ME CANNOT get Valid time from system RTC')
          print('!!! Check SYSTEM BIOS RTC TIME RANGE MUST between 1/Jan/2010 to 31/Dec/2079')
          return ERROR
     return rtc_time

## Function : PECI cmd : GetTemp() configure
def peci_raw_get_temp():
     peci_raw_data = []
     peci_raw_data.append('0x'+ format(GET_TEMP,'02x'))
     DEBUG('peci_raw_data =')
     DEBUG(peci_raw_data)

     return peci_raw_data

## Function : PECI cmd : RdPkgConfig() configure
def peci_raw_rdpkgconfig(device_info, index, parameter1, parameter2 ):
     peci_raw_data = []
     # Setup Byte3 = Cmd_Code = 0xA1
     peci_raw_data.append('0x'+ format(RdPkgConfig,'02x'))
     # Setup Byte4 = Device Info
     peci_raw_data.append('0x'+ format(device_info,'02x'))
     # Setup Byte5 = Index
     peci_raw_data.append('0x'+ format(index,'02x'))
     # Setup Byte6 = parameter1 , low byte
     peci_raw_data.append('0x'+ format(parameter1,'02x'))
     # Setup Byte7 = parameter2, high byte
     peci_raw_data.append('0x'+ format(parameter2,'02x'))
     DEBUG('peci_raw_data =')
     DEBUG(peci_raw_data)

     return peci_raw_data

## Function :NM cmd = 0x40h - Send RAW PECI CMD  , PECI PROXY cmd by interface select
def send_raw_peci_py(ipmi, client_addr, interface, write_length, read_length, peci_cmd ):
     netfn, peci_40h_raw = peci_40h_raw_to_str_py( client_addr, interface, write_length, read_length, peci_cmd)
     # Send PECI PROXY to ME
     rsp = send_ipmb_aardvark(ipmi , netfn , peci_40h_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return rsp

## Function : Calculate current CPU Die Temperature value via GetTemp() PECI proxy cmd
def get_cpu_temp_py(ipmi, cpu_id, peci_interface):
     if(cpu_id == CPU0):
         PECI_CLIENT_ADDR = peci_40h_client_addr_cpu0
     elif(cpu_id == CPU1):
         PECI_CLIENT_ADDR = peci_40h_client_addr_cpu1
     elif(cpu_id == CPU2):
         PECI_CLIENT_ADDR = peci_40h_client_addr_cpu2
     elif(cpu_id == CPU3):
         PECI_CLIENT_ADDR = peci_40h_client_addr_cpu3
     else:
         DEBUG('ERROR!!!! cpu_id out of range')
         return ERROR
     # Prepare GetTemp PECI raw data aray
     raw_peci = peci_raw_get_temp()
     # Send GetTemp via ME RAW PECI proxy: Write length = 1 byte , Read_Length = 2 bytes
     resp = send_raw_peci_py(ipmi , PECI_CLIENT_ADDR, peci_interface, 1, 2, raw_peci )
     if(resp == ERROR):
         DEBUG('ERROR!!! send_raw_peci(): respond data error')
         return ERROR
     # Ananlyst GetTemp Real value: GET PECI RESP DATA Byte[N:5] value, total 2 bytes = Read_Length
     get_temp_resp = calculate_byte_value_py(resp, 5, 2)
     # Transfer data to 2's complement value 4 bytes = 16 bits
     Tmargin = two_complement(get_temp_resp , 16)
     #  Tmargin is the DTS offset value to Tprohot.The resulotion is 1/64 degress C
     Tmargin = abs(( Tmargin / 64))
     DEBUG('PECI GetTemp() = Tmargin = %6d' %Tmargin)
     # Get Tprochot value
     # Prepare RdpkgConfig , index 16 , Thermal Target for Tjmax value
     raw_peci = peci_raw_rdpkgconfig(0, 16, 0, 0 )
     # Send GetTemp via ME RAW PECI proxy: Write length = 5 byte , Read_Length = 5 bytes
     resp = send_raw_peci_py(ipmi, PECI_CLIENT_ADDR, peci_interface, 5, 5, raw_peci )
     if(resp == ERROR):
         DEBUG('ERROR!!! send_raw_peci(): respond data error')
         return ERROR
     # Calculate Tjmax value Byte8 of PECI resp data , total 1 byte
     Tjmax = calculate_byte_value_py(resp, 8, 1)
     DEBUG('CPU0 Tjmax = %6d' %Tjmax)
     # Calculate current CPU Die Temperature = Tjmax - Tmargin
     CPU_Temperature = Tjmax - Tmargin
     DEBUG('Current CPU Die Temperature = %6d' %CPU_Temperature )

     return CPU_Temperature

## Function : IPMI Get Sensor Reading Cmd
def get_sensor_reading_py(ipmi, sensor_number):
     sn_number = int_to_hex( sensor_number, 1 )
     netfn, get_sensor_reading_raw = get_sensor_reading_raw_to_str_py(sn_number)
     # Send PECI PROXY to ME
     rsp = send_ipmb_aardvark(ipmi , netfn , get_sensor_reading_raw )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), Sensor )
     if(sts != SUCCESSFUL ):
         return ERROR
     # Check if sensor available : byte3 bit[5] = 1 means sensor unabailable. = 0 means sensor abailable
     available_bit = get_bits_data_py( ord(rsp[2]) , 5, 1)
     DEBUG('get_sensor_reading : Available Bit = %d' %available_bit)
     # Check sensor scan settings : byte3 bit[6] = 0 means sensor scan disable. = 1 means sensor scan enable.
     scan_bit = get_bits_data_py( ord(rsp[2]), 6, 1)
     DEBUG('get_sensor_reading : Scan Bit = %d' %scan_bit)
     # Check event message settings : byte3 bit[7] = 0 means sensor event message disable. = 1 means sensor event message enable.
     event_message_bit = get_bits_data_py( ord(rsp[2]), 7 ,1)
     DEBUG('get_sensor_reading : Event Message Bit = %d' %event_message_bit)
     # Check if sensor abailable
     if(available_bit == 1):
         DEBUG('get_sensor_reading : Sensor number %2x not abailable' %sensor_number )
         return ERROR
     # Calculate sensor reading value Byte2 of respond message , total 1 byte
     sensor_reading = calculate_byte_value_py(rsp, 2, 1)

     return sensor_reading

## Function : Detect current system configuation : CPU number , power source , DIMM numbers,
def system_config_detect_py(ipmi):
     # Get SPS FW version
     sps_version, platform, dcmi, nm, image  = get_device_id_py(ipmi)
     # Detect SiEn/NM configuation FW via 0xDEh
     if(dcmi == 0 and nm == 0):
          print('SPS FW is SiEn Configuation. NM Test Items will be disabled')
          # Disable all NM related test items
          loop = 0
          for loop in range(0 , 14):
               DEBUG('system_config_detect(): DISABLE NM %d test' %loop)
               NM_TEST_EN[loop] = DISABLE
     # Detect Platform via Get DID
     if(platform == 9):
          print('SPS FW is run in Greenlow E3 Platform, NM segment test items will be disabled')
          # Disable non-support functions : CPU number , DIMM temperature, DIMM power capping , Inbend PECI, CUPS, PTAS in E3 system.  CUPS, PTAS , PECI_003, NM_011
          NM_TEST_EN[11] = DISABLE
          NM_TEST_EN[18] = DISABLE
     elif(platform == 16):
          print('SPS FW is run in Mehlow E3 Platform, NM segment test items will be disabled')
          # Disable non-support functions : CPU number , DIMM temperature, DIMM power capping , Inbend PECI, CUPS, PTAS in E3 system.  CUPS, PTAS , PECI_003, NM_011
          NM_TEST_EN[11] = DISABLE
          NM_TEST_EN[18] = DISABLE
     # Detect PCH temperature sensor
     pch_tem = get_sensor_reading_py(ipmi, pch_temp)
     if(pch_tem == ERROR):
          print(system_config_detect.__name__ + ':Sensor number: %2x not exist' %pch_tem)
          # No PCH temperature reading data : Disable related test items.
     else:
          print('PCH Temperature = %2d' %pch_tem)
     # Detect CUPS sensor#
     cups_core_workload = get_sensor_reading_py(ipmi, cups_core)
     if(cups_core_workload == ERROR):
          print(system_config_detect.__name__ + ': CUPS core Workload Sensor number: %2s not exist' %cups_core_workload)
         # No CUPS Core Workload reading data : Disable related test items. Disable CUPS_001~CUPS_005
     else:
          print('CPU CORE CUPS Workload Reading = %2d' %cups_core_workload)
     # Detect Platfrom power source via Get PSU configuation, BMC E2 OEM cmd and HSC sensor #
     # Detect SMART/CLST function via Sensor# and Get PSU configuation
     # Detect HPIO source via sensor#0xAE and 0xDEh
     hpio_pwr_reading = get_sensor_reading_py(ipmi, hpio_domain_pwr)
     # Disable All HPIO related test by default // MIC_001~MIC_004 all disabled
    # NM_TEST_EN[ 5]  = DISABLE
    # NM_TEST_EN[12]  = DISABLE
    # NM_TEST_EN[ 9]  = DISABLE
     # Check if Sensor ready
     if(hpio_pwr_reading == ERROR):
          print(system_config_detect.__name__ + ': HPIO Domain PWR Sensor number: %2s not exist' %hpio_domain_pwr)
          # No HPIOs domain reading data : Disable related test items. Do nothings.
     else:
          print('HPIO Domain PWR Reading = %2d' %hpio_pwr_reading)
          # Discover all HPIO dedicated sensors # 0xb3 = 179 ~ 0xba = 186
          loop = 179
          for loop in range(179, 187):
               hpio_pwr_reading = get_sensor_reading_py(ipmi, loop)
               if(hpio_pwr_reading != ERROR):
                    print(system_config_detect.__name__ + ': HPIO PWR dedicated sensor number: %2x exist' %loop)
                    print(system_config_detect.__name__ + ': HPIO snnsor number : 0x%2x reading = %2d' %(loop, hpio_pwr_reading))
                     # Enable HPIO related test items
                    NM_TEST_EN[ 5] = ENABLE
                    NM_TEST_EN[12] = ENABLE

     return SUCCESSFUL

## Function : Get Currently SPS FW Configuration and Status
def sps_sts_py(ipmi):
     # Send Get DID to ME
     sps_version, platform, dcmi, nm, image  = get_device_id_py(ipmi)
     print('SPS FW version =' + sps_version)
     if(platform == 10):
          print('SPS FW is run in Purley Platform')
     elif(platform == 16):
          print('SPS FW is run in Mehlow Platform')
     if(dcmi == 0 and nm == 0):
          print('SPS FW is SiEn Configuation')
     elif(dcmi ==0 and nm == 4):
          print('SPS FW is NM 4.0 Configuation')
     elif(dcmi ==0 and nm == 5):
          print('SPS FW is NM 5.0 Configuation')
     else:
          print('Other Configuation')
     # Check resp byte16 - image flag to see if SPS FW back to operation mode
     if(image == get_did_recovery):
          print('!! SPS FW still running in recovery mode after restore to default!!')
          return ERROR
     elif(image == get_did_op1):
          print('SPS FW in OP1 operation mode')
          return SUCCESSFUL
     elif(image == get_did_op2):
          DEBUG('SPS FW in OP2 operation mode,  seems OP1 borken !!!')
          return ERROR
     elif(image == get_did_flash_err):
          DEBUG('SPI flash seems borken !!!')
          return ERROR
     else:
          DEBUG('COMMAND FAIL !!!')
          return ERROR

     return ERROR

## Fucntion : Test Schedule and List Settings
def test_schedule():
     # Check Test List file :
     NM_TEST_LIST, NM_TEST_FILE, SSH_LOG = get_test_list_path()
     # Read Test Item from file
     ## Below is inital AC ON/OFF status
     if os.path.isfile(NM_TEST_LIST) :
          DEBUG('file exist')
          file = open(NM_TEST_FILE, 'r')
          with open(NM_TEST_FILE, "r") as ins:
              test_list = []
              for line in ins:
                  test_list.append(line.rstrip('\n'))
          file.close()
          DEBUG(test_list)
     else:
          DEBUG('file not exist, create file')
          file = open(NM_TEST_FILE, 'w')
          file.write('NM_009')
          file.close()
          return ERROR
     # Record test schedule in file
     test_schedule = []
     for test_item in test_list:
          count = 0
          for enable_item in NM_TEST_ITEM:
              if(test_item == enable_item):
                  test_schedule.append(count)
                  DEBUG('Enable :' + test_item)
              count = count + 1

     return test_schedule
     
## Fucntion : Run Test Item in test schedule
def run_schedule_py(ipmi, test_schedule):
     # Base on system configuation to disable Non-Support test items in test_schedule
     system_config_detect_py(ipmi)
     count = 0
     for test_item in test_schedule:
          # Restore to SPS FW to default for next test Item
          sts_restore = facture_default_py(ipmi, dfh_command_restore_default)
          if(sts_restore == SUCCESSFUL):
               print('SPS FW back to facture default settings for next text item ready')
          else:
               print('SPS FW restore Fail!!')
               return ERROR
          # Delay 15 secs for next test item
          print('Wait 15 secs for SPS FW re-initialization....')
          time.sleep(15)
          DEBUG(test_item)
          # Run all test item which be enabled in test_schedule
          if(test_item == 9):
               print('Start to run NM_009 test....')
               if(NM_TEST_EN[9] == DISABLE):
                    print('NM_009 test will be disabled due to System Not support this feature')
               else:
                    sts = NM_009_WIN(ipmi)
                    NM_TEST_STS[test_item] = sts
          elif(test_item == 10):
               print('Start to run NM_010 test....')
               if(NM_TEST_EN[10] == DISABLE):
                    print('NM_010 test will be disabled due to System Not support this feature')
               else:
                    sts = NM_010_WIN(ipmi)
                    NM_TEST_STS[test_item] = sts
          elif(test_item == 11):
               print('Start to run NM_011 test....')
               if(NM_TEST_EN[11] == DISABLE):
                    print('NM_011 test will be disabled due to System Not support this feature')
               else:
                    sts = NM_011()
                    NM_TEST_STS[test_item] = sts
          elif(test_item == 3):
               print('Start to run NM_003_WIN test....')
               sts = NM_003_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 4):
               print('Start to run NM_004 test....')
               sts = NM_004_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 6):
               print('Start to run NM_006 test....')
               sts = NM_006_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 7):
               print('Start to run NM_007 test....')
               sts = NM_007_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 14):
               print('Start to run NM_014 test....')
               sts = NM_014_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 19):
               print('Start to run PECI_004 test....')
               sts = PECI_004_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 30):
               print('Start to run SMART_001 test....')
               sts = SMART_001_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 31):
               print('Start to run PM_002 test....')
               sts = PM_002_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 32):
               print('Start to run PM_003 test....')
               sts = PM_003_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 33):
               print('Start to run PM_004 test....')
               sts = PM_004_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 34):
               print('Start to run PM_005 test....')
               sts = PM_005_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 35):
               print('Start to run PM_006 test....')
               sts = PM_006_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 36):
               print('Start to run DC_CYCLE test total 300 loop....')
               sts = DC_CYCLE_LOOP_WIN(ipmi, 300)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 37):
               print('Start to run RESET_CYCLE test total 300 loop....')
               sts = RESET_CYCLE_LOOP_WIN(ipmi, 300)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 41):
               print('Start to run MCTP_004 test , Default MCTP device numbe is 1....')
               sts = MCTP_004_WIN(ipmi, 1)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 48):
               print('Start to run PTU_003 test ....')
               sts = PTU_003_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 53):
               print('Start to run NM_WS_004 test ....')
               sts = NM_WS_004_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 60):
               print('Start to run PTT_003 test ....')
               sts = PTT_003_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 61):
               print('Start to run PTT_004 test ....')
               sts = PTT_004_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          elif(test_item == 62):
               print('Start to run BTG_003 test ....')
               sts = BTG_003_WIN(ipmi)
               NM_TEST_STS[test_item] = sts
          else:
               print('test item not in list .....')
               return ERROR

     return SUCCESSFUL

## Fucntion : Read PTU Monitor log file to get data
def read_ptumon(domain):
     f = open(PTU_MON_LOG, 'r+b')
     mf = mmap.mmap(f.fileno(), 0)
     mf.seek(0) # reset file cursor
     # Detect CPU Number
     m = re.search('CPUs', mf)
     # print data location
     #print m.start(), m.end()
     mf.seek((int(m.end()) + 7))
     str = mf.readline()
     cpus = int(str[0:2], 0)
     print('CPU number = %2d' %cpus)
     loop = 0
     total_power = 0
     if(domain == cpu_domain):
          for loop in range(0 , cpus):
               # Get PTU CPU Package Power
               m = re.search('POWER', mf)
               # print data location
               #print  m.start() , m.end()
               mf.seek((int(m.start()) + 100 + loop*101))
               str = mf.readline()
               # print cpu power via str
               DEBUG(str[0:3])
               int_power = int(str[0:3], 0)
               total_power = total_power + int_power
          DEBUG('read_ptumon(): total_cpu_power = %2d' %total_power)
          return_value = total_power
     elif(domain == memory_domain):
          for loop in range(0 , cpus):
               # Get PTU MEM POWER
               m = re.search('MEM', mf)
               mf.seek((int(m.start()) + 28 + 44 + loop*50))
               str = mf.readline()
               # print mem power via str
               DEBUG(str[0:5])
               int_power = float(str[0:5])
               print(int_power)
               total_power = total_power + int_power
          print('read_ptumon(): total_mem_power = %2f' %total_power)
          return_value = total_power
     else:
          mf.close()
          f.close()
          return ERROR
     # Close files
     mf.close()
     f.close()

     return return_value
## Define IPMI raw	 
def cmd_raw(ipmi, args):
    lun = 0
    if len(args) > 1 and args[0] == 'lun':
        lun = int(args[1], 0)
        args = args[2:]

    if len(args) < 2:
        usage()
        return

    netfn = int(args[0], 0)
    raw_bytes = array.array('B', [int(d, 0) for d in args[1:]])
	#print(raw_bytes.tostring())
    rsp = ipmi.raw_command(lun, netfn, raw_bytes.tostring())
    print(' '.join('%02x' % ord(d) for d in rsp))
	 
## Define initialization of aardvark ipmi	 
def aardvark_ipmi_init(target_addr, channel):
    ## Test pyIPMI
    opts, args = getopt.getopt(sys.argv[1:], 't:hvVI:H:U:P:o:b:')
    interface_name = 'aardvark'
    name = 'pullups'
    value = 'off'
    aardvark_pullups = False
    aardvark_serial = None
    aardvark_target_power = False
    target_address = target_addr
    target_routing = [(target_addr ,channel)]
    ###
    interface = pyipmi.interfaces.create_interface(interface_name, serial_number=aardvark_serial)
    ipmi = pyipmi.create_connection(interface)
    ipmi.target = pyipmi.Target(target_address)
    ipmi.target.set_routing(target_routing)
    
    return ipmi

## Function : NM_003 Test Process: Verify CPU domain power reading is accuracy.
def NM_003_WIN(ipmi):
     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 30secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS , LOG_SAVE_OFF)
     time.sleep(30)     
     # Read CPU Power via 0xC8h cmd
     power_cpu_average_stress = read_power_py(ipmi , global_power_mode, cpu_domain,AC_power_side, 0 )
     if(power_cpu_average_stress == ERROR):
         print(NM_003_WIN.__name__ + ':CPU power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_003_WIN.__name__ + ':CPU Power Reading OK')
     print(NM_003_WIN.__name__ + ':Currently Full Stress Average CPU Power Reading = %6d watts' %power_cpu_average_stress)

     # Read Platform Power via 0xC8h cmd
     power_platform_average_stress = read_power_py(ipmi , global_power_mode, platform_domain,AC_power_side, 0 )
     if(power_platform_average_stress == ERROR):
         print(NM_003_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Read Platform Power Reading OK
     print(NM_003_WIN.__name__ + ':Platform Power Reading OK')
     print(NM_003_WIN.__name__ + ':Currently Full Stress Average Platform Power Reading = %6d watts' %power_platform_average_stress)
     #Check if Platform Power > CPU Power
     if((power_platform_average_stress > power_cpu_average_stress) and (power_cpu_average_stress > 0) ):
         print(NM_003_WIN.__name__ + ':CPU power reading OK')
         return SUCCESSFUL
     else:
         print(NM_003_WIN.__name__ + ':CPU power reading Fail')
         return ERROR
         
## Function : NM_004 Test Process: Verify Memory domain power reading is accuracy.
def NM_004_WIN(ipmi):
     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 30secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS, LOG_SAVE_OFF )
     time.sleep(30)     
     # Read CPU Power via 0xC8h cmd
     power_memory_average_stress = read_power_py(ipmi , global_power_mode, memory_domain,AC_power_side, 0 )
     if(power_memory_average_stress == ERROR):
         print(NM_004_WIN.__name__ + ':Memory power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_004_WIN.__name__ + ':Memory Power Reading OK')
     print(NM_004_WIN.__name__ + ':Currently Full Stress Average Memory Power Reading = %6d watts' %power_memory_average_stress)

     # Read Platform Power via 0xC8h cmd
     power_platform_average_stress = read_power_py(ipmi , global_power_mode, platform_domain,AC_power_side, 0 )
     if(power_platform_average_stress == ERROR):
         print(NM_004_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Read Platform Power Reading OK
     print(NM_004_WIN.__name__ + ':Platform Power Reading OK')
     print(NM_004_WIN.__name__ + ':Currently Full Stress Average Platform Power Reading = %6d watts' %power_platform_average_stress)
     #Check if Platform Power > CPU Power
     if((power_platform_average_stress > power_memory_average_stress) and (power_memory_average_stress > 0) ):
         print(NM_004_WIN.__name__ + ':Memory power reading OK')
         return SUCCESSFUL
     else:
         print(NM_004_WIN.__name__ + ':Memory power reading Fail')
         return ERROR
    
#Define NM_009 test process in Mehlow Windows
def NM_009_WIN(ipmi):

     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 80secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS, LOG_SAVE_OFF )
     time.sleep(30)
     # Read Platform Power via 0xC8h cmd
     power_average_stress = read_power_py(ipmi , global_power_mode, platform_domain,AC_power_side, 0 )
     if(power_average_stress == ERROR):
         print(NM_009.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_009.__name__ + ':Platform Power Reading OK')
     print(NM_009.__name__ + ':Currently Full Stress Average Platform Power Reading = %6d watts' %power_average_stress)
     # Read Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, platform_domain, 0, 1, 0)
     # Check if Power Draw Range data are correct
     if(max_draw_range > (0.8*power_average_stress) and (0.8*power_average_stress) > min_draw_range):
         # Power Draw Range OK
         print(NM_009.__name__ + ':Platform Power Draw Range Setting OK')
         print(NM_009.__name__ + ":Power Capping value = %6d watt" % (power_average_stress*4/5))
     else:
         print(NM_009.__name__ + ':Error ! Platform Power Draw Rnage Setting Error!!!')
         return ERROR
     # Check if Correction time data are correct
     if(min_correction_time == ERROR):
         print(NM_009.__name__ + ':Error! Correction Time value not correct !!!')
         return ERROR
     # Correction Time OK
     print(NM_009.__name__ + ':Correction Time Value OK')
     print(NM_009.__name__ + ":Set correction time value = %6d msec" % (min_correction_time))
     # Set Power Capping via 0xC1h cmd in police id #3, target limit = 80% of full stress value, correction time = minimum support correction time
     sts = set_nm_power_policy_py( ipmi, c1h_platform_domain, c1h_policy_enable, 3, c1h_no_policy_trigger, c1h_add_policy, c1h_auto_aggressive, c1h_presistent, c1h_alert_enable, c1h_shutdown_disable, AC_power_side, (power_average_stress*4/5), min_correction_time, c1h_trigger_limit_null, c1h_minimum_report_period )
     if(sts == ERROR):
         print(NM_009.__name__ + ':set_nm_power_policy fail !!!')
         return ERROR
     # Read Platform Power via 0xC8h cmd again to make sure power drop
     time.sleep(3) # Wait for power drop after capping time longer than correction time settings
     power_average_cap = read_power_py(ipmi, global_power_mode , platform_domain, AC_power_side, 0)
     if(power_average_cap == ERROR):
         print(NM_009.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Below is check the power reading value to make sure if power capping really work. Make sure power drop to capping value.
     elif(power_average_cap > power_average_stress*85/100):
         print(NM_009.__name__ + ':Power limit error!!! Platfrom power reading still higher than capping value !!!')
         print(NM_009.__name__ + ':Expected limit value = %6d , But currecnt platfrom power reading %6d' %((power_average_stress*4/5) , power_average_cap))
         return ERROR
     # Power Reading OK
     print(NM_009.__name__  + ':Platform Power Reading OK')
     print(NM_009.__name__  + ':After NM Capping average platform power reading = %6d watts' %power_average_cap)

     return SUCCESSFUL

## Function : NM_010 Test Process: Verify that power limiting is working correctly in CPU power domain.
def NM_010_WIN(ipmi):

     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 20secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS, LOG_SAVE_OFF )
     time.sleep(5)
     # Read CPU Power via 0xC8h cmd
     power_average_stress = read_power_py(ipmi, global_power_mode , cpu_domain, AC_power_side, 0)
     if(power_average_stress == ERROR):
         print(NM_010.__name__ + ':CPU power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_010.__name__ + ':CPU Power Reading OK')
     print(NM_010.__name__ + ':Currently Full Stress Average CPU Power Reading = %6d watts' %power_average_stress)
     # Read Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, cpu_domain, 0, 1, 0)
     # Check if Power Draw Range data are correct
     if(max_draw_range > (0.8*power_average_stress) and (0.8*power_average_stress) > min_draw_range):
         # Power Draw Range OK
         print(NM_010.__name__ + ':CPU Power Draw Range Setting OK')
         print(NM_010.__name__ + ":Power Capping value = %6d watt" % (power_average_stress*4/5))
     else:
         print(NM_010.__name__ + ':Error ! CPU Power Draw Rnage Setting Error!!!')
         return ERROR
     # Check if Correction time data are correct
     if(min_correction_time == ERROR):
         print(NM_010.__name__ + ':Error! Correction Time value not correct !!!')
         return ERROR
     # Correction Time OK
     print(NM_010.__name__ + ':Correction Time Value OK')
     print(NM_010.__name__ + ":Set correction time value = %6d msec" % (min_correction_time))
     # Set Power Capping via 0xC1h cmd in police id #3, target limit = 80% of full stress value, correction time = minimum support correction time
     sts = set_nm_power_policy_py(ipmi, c1h_cpu_domain, c1h_policy_enable, 3, c1h_no_policy_trigger, c1h_add_policy, c1h_auto_aggressive, c1h_presistent, c1h_alert_enable, c1h_shutdown_disable, AC_power_side, (power_average_stress*4/5), min_correction_time, c1h_trigger_limit_null, c1h_minimum_report_period )
     if(sts == ERROR):
         print(NM_010.__name__ + ':set_nm_power_policy fail !!!')
         return ERROR
     # Read CPU Power via 0xC8h cmd again to make sure power drop
     time.sleep(3) # Wait for power drop after capping time longer than correction time settings
     power_average_cap = read_power_py(ipmi, global_power_mode , cpu_domain, AC_power_side, 0)
     if(power_average_cap == ERROR):
         print(NM_010.__name__ + ':CPU power reading error!!!')
         return ERROR
     # Below is check the power reading value to make sure if power capping really work. Make sure power drop to capping value.
     elif(power_average_cap > power_average_stress*85/100):
         print(NM_010.__name__ + ':Power limit error!!! CPU power reading still higher than capping value !!!')
         print(NM_010.__name__ + ':Expected limit value = %6d , But currecnt CPU power reading %6d' %((power_average_stress*4/5) , power_average_cap))
         return ERROR
     # Power Reading OK
     print(NM_010.__name__  + ':CPU Power Reading OK')
     print(NM_010.__name__  + ':After NM Capping average platform power reading = %6d watts' %power_average_cap)

     return SUCCESSFUL

## Function : NM_006 Test Process: Verify ME RTC TIME is accuracy.
def NM_006_WIN(ipmi):
     # Check Test List file :
     NM_TEST_LIST, NM_TEST_FILE, SSH_LOG = get_test_list_path()
     # Get ME RTC TIME via 0x48 cmd
     print(NM_006_WIN.__name__ + ':Start checking if ME RTC cunter is normal...')
     loop = 0
     temp_time = 0
     for loop in range(0, 10):
         rtc_me = get_sel_time_py(ipmi)
         if(rtc_me == ERROR):
              DEBUG(NM_006_WIN.__name__ + ':ERROR!!! Get ME SEL TIME IPMI Resp data error!!!')
              return ERROR
         elif(rtc_me <= temp_time):
              DEBUG(NM_006_WIN.__name__ + ':ERROR !!! ME RTC count not move.')
              return ERROR
         # Get RTC data OK
         DEBUG(NM_006_WIN.__name__ + ':Get ME RTC OK')
         DEBUG(NM_006_WIN.__name__ + ':ME SEL RTC TIME Reading = %12d secs' %rtc_me)
         temp_time = rtc_me
         # Add delay time 1 sec for next reading
         time.sleep(1)
     # Calculate years
     rtc_me_year = RTC_DEFAULT_YEAR + ( rtc_me / 365 / 24 / 60 / 60 )
     # Calculate Mohths and Dates
     # The leap years have 366 days, other years are 365 days
     rtc_me_leap_year = rtc_me / 365 / 24 / 60 / 60 / 4
     rtc_me_month =  rtc_me % ( 365 * 24 *60 * 60 ) /  (30 * 24 * 60 * 60) + 1
     rtc_me_date  =  rtc_me % ( 365 * 24 *60 * 60 ) %  (30 * 24 * 60 * 60) / (24 * 60 * 60) + 1 - rtc_me_leap_year
     if(rtc_me_date < 0):
         rtc_me_month = rtc_me_month - 1
         if(rtc_me_month < 0 ):
              rtc_me_year = rtc_me_year - 1
              rtc_me_month = 12
         rtc_me_date = 30 - abs(rtc_me_date)
     # January
     if( (rtc_me_month - 1) == 0 ):
         rtc_me_date  =  rtc_me_date
     # Feburary
     elif((rtc_me_month - 1) == 1):
         # Subtract 1 because January is 31 days
         rtc_me_date  =  rtc_me_date - 1
     # March
     elif((rtc_me_month - 1) == 2):
         rtc_me_date  = rtc_me_date + 1
     # April
     elif((rtc_me_month - 1) == 3):
         rtc_me_date  = rtc_me_date
     # May
     elif((rtc_me_month - 1) == 4):
         rtc_me_date  = rtc_me_date
     # June
     elif((rtc_me_month - 1) == 5):
         rtc_me_date  = rtc_me_date - 1
     # July
     elif((rtc_me_month - 1) == 6):
         rtc_me_date  = rtc_me_date - 1
     # August
     elif((rtc_me_month - 1) == 7):
         rtc_me_date  = rtc_me_date - 2
     # September
     elif((rtc_me_month - 1) == 8):
         rtc_me_date  = rtc_me_date - 3
     # October
     elif((rtc_me_month - 1) == 9):
         rtc_me_date  = rtc_me_date - 3
     # November
     elif((rtc_me_month - 1) == 10):
         rtc_me_date  = rtc_me_date - 4
     # December
     elif((rtc_me_month - 1) == 11):
         rtc_me_date  = rtc_me_date - 4
     if(rtc_me_date < 0):
         rtc_me_month = rtc_me_month - 1
         if(rtc_me_month < 0 ):
              rtc_me_year = rtc_me_year - 1
              rtc_me_month = 12
         rtc_me_date = 30 - abs(rtc_me_date)
     rtc_me_hour  =  rtc_me % ( 365 * 24 *60 * 60 ) %  (30 * 24 * 60 * 60) % (24 * 60 * 60) / (60 * 60)
     rtc_me_min  =  rtc_me % ( 365 * 24 *60 * 60 ) %  (30 * 24 * 60 * 60) % (24 * 60 * 60) % (60 * 60) / 60
     rtc_me_sec  =  rtc_me % ( 365 * 24 *60 * 60 ) %  (30 * 24 * 60 * 60) % (24 * 60 * 60) % (60 * 60) % 60
     print('Year of ME RTC TIME = %4d' % rtc_me_year)
     print('Moth of ME RTC TIME = %4d' % rtc_me_month)
     print('Date of ME RTC TIME = %4d' % rtc_me_date)
     print ('Hour of ME RTC TIME = %4d' % rtc_me_hour)
     print ('Min of ME RTC TIME = %4d' % rtc_me_min)
     print ('Sec of ME RTC TIME = %4d' % rtc_me_sec)
     # Get current host system RTC TIME
     print(NM_006_WIN.__name__ + ':Get OS RTC TIME...')
     ssh_send_cmd_switch(background_run_enable,  SSH_CMD_PATH_EMPTY , OSRTC, LOG_SAVE_EN )
     # Compare OS RTC TIME with ME RTC TIME
     print(NM_006_WIN.__name__ + ':Start compare ME RTC and OS RTC time...')
     rtc_os = read_keyword_file(SSH_LOG, 'RTC' , 14 , 0 , 0)
     print('OS RTC Year = ' + rtc_os[0:4])
     print('OS RTC Month = ' + rtc_os[5:7])
     print('OS RTC Data = ' + rtc_os[8:10])
     print('OS RTC Hour = ' + rtc_os[11:13])
     print('OS RTC Min = ' + rtc_os[14:16])
     print('OS RTC Sec = ' + rtc_os[17:19])
     # Check if hour and min values are accuracy
     #if((abs(rtc_me_hour - int(rtc_os[11:13],0)) > 1) or (abs(rtc_me_min - int(rtc_os[14:16],0)) > 1 ) ):
     #    print('ERROR !!! ME RTC hour or min values not accuracy')
     #    return ERROR
     # Check if ME RTC sec value accuracy. By default ME syncronize with Host RTC every 5 secs. So suppose sec difference value between ME RTC and Host msut small than 5 secs
     if(abs(rtc_me_sec - int(rtc_os[17:19],0)) > 5 ):
         print('ERROR !!! ME RTC hour or min values not accuracy')
         return ERROR

     return SUCCESSFUL

#Define NM_WS_004 : Boot time power limiting test process in Mehlow Windows
def NM_WS_004_WIN(ipmi):
     print(' NM_WS_004_WIN: NM_WS_004 Boot Time Power capping test start')
     # Prepare Package Thermal Status MSR0x1B1  : RdpkgConfig , index 0x14 
     raw_peci = peci_raw_rdpkgconfig(0, 20 , 0, 0 )
     # Send Package Thermal Status via ME RAW PECI proxy: Write length = 5 byte , Read_Length = 5 bytes
     resp = send_raw_peci_py(ipmi, peci_40h_client_addr_cpu0, peci_40h_interface_fall_back, 5, 5, raw_peci )
     if(resp == ERROR):
         print('ERROR!!! send_raw_peci(): respond data error')
         return ERROR
     #Check Thermal Status before SMART testing
     if(ord(resp[4]) != 0x40):
         print('ERROR!!! send_raw_peci(): PCU respond data error')
         return ERROR
     elif((ord(resp[5])!= 0) or (ord(resp[6])!= 0)):
         print(' NM_WS_004_WIN: CPU Thermal status incorrect , probabaly already have thermal event happen before test.')
     # Read Platform Power via 0xC8h cmd
     power_average_stress = read_power_py(ipmi , global_power_mode, platform_domain,AC_power_side, 0 )
     if(power_average_stress == ERROR):
         print(NM_WS_004_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_WS_004_WIN.__name__ + ':Platform Power Reading OK')
     print(NM_WS_004_WIN.__name__ + ':Currently Full Stress Average Platform Power Reading = %6d watts' %power_average_stress)
     # Read Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, platform_domain, 0, 1, 0)
     # Check if Power Draw Range data are correct
     if(max_draw_range > (0.1*power_average_stress) and (0.1*power_average_stress) > min_draw_range):
         # Power Draw Range OK
         print(NM_WS_004_WIN.__name__ + ':Platform Power Draw Range Setting OK')
         print(NM_WS_004_WIN.__name__ + ":Power Capping value = %6d watt" % (power_average_stress*1/10))
     else:
         print(NM_WS_004_WIN.__name__ + ':Error ! Platform Power Draw Rnage Setting Error!!!')
         return ERROR
     # Check if Correction time data are correct
     if(min_correction_time == ERROR):
         print(NM_WS_004_WIN.__name__ + ':Error! Correction Time value not correct !!!')
         return ERROR
     # Correction Time OK
     print(NM_WS_004_WIN.__name__ + ':Correction Time Value OK')
     print(NM_WS_004_WIN.__name__ + ":Set correction time value = %6d msec" % (min_correction_time))
     # Set Power Capping via 0xC1h cmd in police id #3, target limit = 10% of  current power  value, correction time = minimum support correction time
     sts = set_nm_power_policy_py( ipmi, c1h_platform_domain, c1h_policy_enable, 3, c1h_no_policy_trigger, c1h_add_policy, c1h_auto_aggressive, c1h_presistent, c1h_alert_enable, c1h_shutdown_disable, AC_power_side, (power_average_stress*1/10), min_correction_time, c1h_trigger_limit_null, c1h_minimum_report_period )
     if(sts == ERROR):
         print(NM_WS_004_WIN.__name__ + ':set_nm_power_policy fail !!!')
         return ERROR
     # Reset OS and DC power via ACPI process
     ssh_send_cmd_switch(background_run_enable,  SSH_CMD_PATH_EMPTY , centos_reset , LOG_SAVE_OFF )
     # Waiting System Reboot.
     print(NM_WS_004_WIN.__name__ + ':Wait 20 secs for system reboot Test')
     time.sleep(20)
     # Check if system reboot and before BIOS EOP
     eop = 1
     time_count = 0
     while(eop == 1):
         rsp, current_status, operation_state , eop= mesdc_get_version_py(ipmi)
         if(rsp == ERROR):
             print(NM_WS_004_WIN.__name__ + ':NM_WS_004_WIN TEST FAIL !!!')
             return ERROR
         if(time_count > 30): # Make sure program will not go to dead loop due to system error status
             print(NM_WS_004_WIN.__name__ + ':NM_WS_004_WIN TEST FAIL !!!')
             return ERROR
             
         time_count = time_count + 1
         time.sleep(1)
     print(NM_WS_004_WIN.__name__ + ':System already reboot and before EOP state, start to check Boot Time power capping function...')
     # Check if Limiting Policy ID =  3 via 0xF2 cmd
     limiting_policy_id = get_limiting_policy_id(ipmi , f2h_platform_domain )
     print(NM_WS_004_WIN.__name__  + ': Current Limiting Policy ID = %d' %limiting_policy_id)
     if(limiting_policy_id != 3):
          print(NM_WS_004_WIN.__name__ + ': Boot Time Power limit error!!! Limiting Policy ID not correct !!! Should Be ID 0 to limit power')
          return ERROR          
     # Check if NM_Throttle assert via CPU PROCHOT status
     # Send Package Thermal Status again via ME RAW PECI proxy. Check event happen
     resp = send_raw_peci_py(ipmi, peci_40h_client_addr_cpu0, peci_40h_interface_fall_back, 5, 5, raw_peci )
     if(resp == ERROR):
         print('ERROR!!! send_raw_peci(): respond data error')
         return ERROR
     #Check Thermal Status to make sure CPU prohot event happen
     if(ord(resp[4]) != 0x40):
         print('ERROR!!! send_raw_peci(): PCU respond data error')
         return ERROR
     prochot_sts        = get_bits_data_py( ord(resp[5]) , 2 , 1)
     prochot_sts_log    = get_bits_data_py( ord(resp[5]) , 3 , 1)
     print('NM_WS_004_WIN : prochot_sts = %d , prochot_sts_log =%d ' %(prochot_sts, prochot_sts_log))
     if( (prochot_sts == 0) and (prochot_sts_log==0)):
         print('NM_WS_004_WIN Fail! No PROCHOT event happen after event triggered ')
         return ERROR
         
     #Waiting for 50 secs to make sure system already boot into OS again.
     print('Waiting for 50 secs to make sure system already boot into OS again... ')   
     time.sleep(50)
     return SUCCESSFUL

## Function : PECI_004 Test Process: Verify PECI proxy function.
def PECI_004_WIN(ipmi):
     # Send Get DID to ME to make sure the platform PECI configuation
     sps_version, platform, dcmi, nm, image  = get_device_id_py(ipmi)
     print('SPS FW version =' + sps_version)
     if(platform == 10):
          print('SPS FW is run in Purley Platform, Test will include Inbend PECI and PECI wire')
          # Detect CPU Number
          
          # Start test PECI proxy function via GetTemp raw PECI cmd
          loop = 0
          interface = 0
          # Test CPU0-CPU1
          for lopp in range(0, 2):
               # Test Fallback =0, Inbend PECI = 1, PECI wire = 2
               for interface in range(0, 3):
                    cpu_temp = get_cpu_temp_py(ipmi, loop, interface )
                    if(cpu_temp == ERROR):
                         print('ERROR !!! CPU%d GetTemp PECI cmd via interface= %d fail!!!' %(loop, interface))
                         return ERROR
                    print('CPU%d Temp = %2d via interface= %d' %(loop, cpu_temp, interface))
          return SUCCESSFUL
     elif(platform == 9 or platform == 16):
          print('SPS FW is run in E3 Greenlow/Mehlow Platfrom, no Inbend PECI function support. Only test PECI wire.')
          cpu_temp = get_cpu_temp_py(ipmi, 0 , 0 )
          if(cpu_temp == ERROR):
               print('ERROR !!! CPU%d GetTemp PECI cmd via interface= %d fail!!!' %(loop, interface))
               return ERROR
          return SUCCESSFUL
     else:
          print('unknown platform , test will include Inbend PECI and peci wire')
     print('ERROR !!! Exception Error in PECI_004 test')

     return ERROR

#Define NM_007 test: Set Maximum allowed  P/T  control process in Mehlow Windows
def NM_007_WIN(ipmi):

     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 30secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS, LOG_SAVE_OFF )
     time.sleep(30)
     # Read Platform Power via 0xC8h cmd
     power_average_stress = read_power_py(ipmi , global_power_mode, platform_domain,AC_power_side, 0 )
     if(power_average_stress == ERROR):
         print(NM_007.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_007_WIN.__name__ + ':Platform Power Reading OK')
     print(NM_007_WIN.__name__ + ':Currently Full Stress Average Platform Power Reading = %6d watts' %power_average_stress)
     # Send C0h Disable NM policy control
     print(NM_007_WIN.__name__ + ':Disable NM Policy Control before test Set Maximum allowed P/T state function')
     rsp = enable_disable_nm_policy_control_py(ipmi , c0h_global_disable , c0h_platform_domain , 1 )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     # Send D4h Get Number of P/T states support in this platform
     p_states, t_states = get_number_of_pt_states(ipmi, d4h_ctl_knob_max_pt )
     print(NM_007_WIN.__name__ + ':Current Default Number of P states = %d , T states = %d ' %(p_states, t_states))
     # Check if Default P/T state numbers are correct 
     if(p_states < 2):
         print('This system support P states numbers are too small or incorrect , please check BIOS settings, probabaly related to HWPM settings')
         return ERROR
     else:
         max_p_states = p_states - 5
     if(t_states < 2):
         print('This system support T states numbers are too smalL , please check BIOS settings, probabaly need to enable ACPI T state settings in BIOS')
         print('Current test will ignore T state testing until get correct T state numbers')
         max_t_states = 0
     else:
         max_t_states = t_states - 1
     #Set power budget to 0 watts
     print(NM_007_WIN.__name__ + ':Set power budget to 0 watts')
     # Coverter 0 watt power_budget  int value to hex value for byte[6:5]- Power Budget
     power_budget = int_to_hex( 0, 2 )
     # No control component id settings
     component_id = 0
     rsp = set_total_power_budget_py(ipmi, d0h_platform_domain , d0h_component_control_disable , power_budget , component_id )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     #Set Max Allowed P-state/T-state
     print(NM_007_WIN.__name__ + ':Set Maximum allowed P/T state to max_p_states = %d, max_t_states = %d ' %(max_p_states, max_t_states))
     rsp = set_max_pt_states_py(ipmi, d2h_ctl_knob_max_pt , max_p_states, max_t_states )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR     
     #Get Max Allowed CPU P/T-state
     max_allowed_p_states, max_allowed_t_states = get_max_allowed_pt_states(ipmi, d3h_ctl_knob_max_pt )
     if((max_allowed_p_states != max_p_states) or (max_allowed_t_states!= max_t_states)):
         print(NM_007_WIN.__name__ + ':Set Maximum allowed P/T state test fail !!!! Set max_p_states = %d, max_t_states = %d , But current maximun allowed P state = %d , maximun allowed T state = %d ' %(max_p_states, max_t_states , max_allowed_p_states, max_allowed_t_states))
         return ERROR
     # Read Platform Power via 0xC8h cmd again to make sure power drop
     time.sleep(3) # Wait for power drop after capping time longer than correction time settings
     power_average_cap = read_power_py(ipmi, global_power_mode , platform_domain, AC_power_side, 0)
     if(power_average_cap == ERROR):
         print(NM_007_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Below is check the power reading value to make sure if power capping really work. Make sure power drop to capping value.
     elif(power_average_cap > power_average_stress*85/100):
         print(NM_007_WIN.__name__ + ':Power limit error!!! Platfrom power reading still higher than limit value !!!')
         return ERROR
     # Power Reading OK
     print(NM_007_WIN.__name__  + ':Platform Power Reading OK')
     print(NM_007_WIN.__name__  + ':After NM Capping average platform power reading = %6d watts' %power_average_cap)

     return SUCCESSFUL

#Define NM_014 : Fast NM Limiting  test process in Mehlow Windows 
# Note :  1. XML file set : Configuation -> Node Manager -> NM Fast Limiting -> NM Fast Limiting Enable = True , Poling Interval = 10msec
# Note :  2. PSU PMbus FW support Read_Eout = 0x87h cmd
# Note:   3. Platform Power Source from PSU or HSC with 100mesc polling reate in SDR (  BMC is not support this function )
def NM_014_WIN(ipmi):
     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 80secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS, LOG_SAVE_OFF )
     time.sleep(30)
     # Read Platform DC side Power via 0xC8h cmd
     power_average_stress = read_power_py(ipmi , global_power_mode, hw_protection_domain, DC_power_side, 0 )
     if(power_average_stress == ERROR):
         print(NM_014_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_014_WIN.__name__ + ':Platform Power Reading OK')
     print(NM_014_WIN.__name__ + ':Currently Full Stress Average Platform Power Reading = %6d watts' %power_average_stress)
     # Read DC side Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, hw_protection_domain , 0, 1, 0)
     # Check if DC side Power Draw Range data are correct
     if(max_draw_range > (0.8*power_average_stress) and (0.8*power_average_stress) > min_draw_range):
         # Power Draw Range OK
         print(NM_014_WIN.__name__ + ':Platform Power Draw Range Setting OK')
         print(NM_014_WIN.__name__ + ":Power Capping value = %6d watt" % (power_average_stress*4/5))
     else:
         print(NM_014_WIN.__name__ + ':Error ! Platform Power Draw Rnage Setting Error!!!')
         return ERROR
     # Check if Correction time data are correct
     if(min_correction_time == ERROR):
         print(NM_014_WIN.__name__ + ':Error! Correction Time value not correct !!!')
         return ERROR
     # Correction Time OK
     print(NM_014_WIN.__name__ + ':Correction Time Value OK')
     print(NM_014_WIN.__name__ + ":Set correction time value = %6d msec" % (min_correction_time))     
     #Set Power Draw range via 0xCBh cmd in HW protection domain :  maximum power drange range in domain 3 = 80% of power_average_stress 
     sts = set_nm_power_draw_range_py(ipmi, cbh_hw_protection_domain , min_draw_range , 0.8*power_average_stress )
     if(sts == ERROR):
         print(NM_014_WIN.__name__ + ':set_nm_power_draw_range 0xCBh fail !!!')
         return ERROR
     # Read Platform Power via 0xC8h cmd again to make sure power drop
     time.sleep(3) # Wait for power drop after capping time longer than correction time settings
     power_average_cap = read_power_py(ipmi, global_power_mode , hw_protection_domain, DC_power_side, 0)
     if(power_average_cap == ERROR):
         print(NM_014_WIN.__name__ + ':DC side power reading error!!!')
         return ERROR
     # Below is check the power reading value to make sure if power capping really work. Make sure power drop to capping value.
     elif(power_average_cap > power_average_stress*85/100):
         print(NM_014_WIN.__name__ + ': Fast NM Power limit error!!! DC side power reading still higher than capping value !!!')
         print(NM_014_WIN.__name__ + ':Expected limit value = %6d , But currecnt platfrom power reading %6d' %((power_average_stress*4/5) , power_average_cap))
         return ERROR
     # Power Reading OK
     print(NM_014_WIN.__name__  + ':Platform Power Reading OK')
     print(NM_014_WIN.__name__  + ':After NM Capping average platform power reading = %6d watts' %power_average_cap)
     # Check if Limiting Policy ID =  0 via 0xF2 cmd
     limiting_policy_id = get_limiting_policy_id(ipmi , f2h_hw_protection_domain )
     print(NM_014_WIN.__name__  + ': Current Limiting Policy ID = %d' %limiting_policy_id)
     if(limiting_policy_id != 0):
          print(NM_014_WIN.__name__ + ': Fast NM Power limit error!!! Limiting Policy ID not correct !!! Should Be ID 0 to limit power')
          return ERROR
     
     return SUCCESSFUL

## Function : RECOVERY PSU SETTING IN CASE PSU Continuous ERROR ALEERT after testing
def SMART_PSU_RECOVERY(ipmi, default_ot_warm_low_byte, default_ot_warm_high_byte , bus , target_addr ):
     #Restor PSU OT_WARM_LIMIT value to default, suppose PROHOC event should gone!
     # Send PMbus Proxy cmd to write current Over Temperature Threshold value =  default_ot_warm value
     print('Start Recovery PSU Default Settings.....')
     write_len = 3
     read_len = 0
     pmbus_cmd_aray = [PMBUS_READ_WRITE_OT_WARM_LIMIT, default_ot_warm_low_byte , default_ot_warm_high_byte]
     rsp = send_raw_pmbus_write_cmd_extend_py(ipmi, d9h_trans_type_write_word, d9h_pec_report, d9h_pec_en, bus , target_addr , 0 , 0 , 0 , d9h_trans_potocol_pmbus , write_len , read_len , pmbus_cmd_aray)
     # Check pmbus rsp  data
     if(rsp == ERROR):
         print('ERROR!!! send pmbus error ! respond data error')
         return ERROR

     return SUCCESSFUL

## Function : SMART_001 Test Process: Verify SMART/CLST  function.
def SMART_001_WIN(ipmi):
     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Prepare Package Thermal Status MSR0x1B1  : RdpkgConfig , index 0x14 
     raw_peci = peci_raw_rdpkgconfig(0, 20 , 0, 0 )
     # Send Package Thermal Status via ME RAW PECI proxy: Write length = 5 byte , Read_Length = 5 bytes
     resp = send_raw_peci_py(ipmi, peci_40h_client_addr_cpu0, peci_40h_interface_fall_back, 5, 5, raw_peci )
     if(resp == ERROR):
         print('ERROR!!! send_raw_peci(): respond data error')
         return ERROR
     #Check Thermal Status before SMART testing
     if(ord(resp[4]) != 0x40):
         print('ERROR!!! send_raw_peci(): PCU respond data error')
         return ERROR
     elif((ord(resp[5])!= 0) or (ord(resp[6])!= 0)):
         print(' send_raw_peci(): CPU Thermal status incorrect , probabaly already have thermal event happen before test.')
         #return ERROR   
     # Read PSU Over Temperature Threshold value via PMbus Proxy
     write_len = 1
     read_len = 2
     bus = d9h_sml1
     target_addr = 0xb0
     pmbus_cmd = PMBUS_READ_WRITE_OT_WARM_LIMIT
     # Send PMbus Proxy cmd to get current Over Temperature Threshold value
     rsp = send_raw_pmbus_cmd_extend_py(ipmi, d9h_trans_type_read_word, d9h_pec_report, d9h_pec_en, bus , target_addr , 0 , 0 , 0 , d9h_trans_potocol_pmbus , write_len , read_len , pmbus_cmd)
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     # Transfer value to real value is linear data format , X = Y*2^N
     # Calculate N : High Byte bit[7:3]
     N  = get_bits_data_py( ord(rsp[5]) , 3 , 5)
     # Transfer N data to 2's complement value
     N_2complement = two_complement(N , 5)
     # Calculate Y : High Byte bit[2:0]
     Y1  = get_bits_data_py( ord(rsp[5]) , 0 , 3)
     Y1  = Y1 * 256
     Y2  = ord(rsp[4])
     Y   = Y1 + Y2   
	 # Calculate ot_warm value from rsp Byte[6:5] value, total 2 bytes
     default_ot_warm_high_byte = ord(rsp[5])
     default_ot_warm_low_byte = ord(rsp[4])
     default_ot_warm = Y*math.pow(2,N_2complement)
     print('Current default OT WARM temp value = %6d' %default_ot_warm) 
     # Run load on host system with PTU 100% loading for 80secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS, LOG_SAVE_OFF )
     time.sleep(10)
     # Read Platform Power via 0xC8h cmd
     power_average_stress = read_power_py(ipmi , global_power_mode, platform_domain,AC_power_side, 0 )
     if(power_average_stress == ERROR):
         print(SMART_001_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Power Reading OK
     print(SMART_001_WIN.__name__ + ':Platform Power Reading OK')
     print(SMART_001_WIN.__name__ + ':Currently Full Stress Average Platform Power Reading = %6d watts' %power_average_stress)     
     # Change OT_WARM_LIMIT value to 10 degree
     # Send PMbus Proxy cmd to write current Over Temperature Threshold value = 10 degree C
     write_len = 3
     read_len = 0
     pmbus_cmd_aray = [PMBUS_READ_WRITE_OT_WARM_LIMIT, 0x14 , 0xf8]
     rsp = send_raw_pmbus_write_cmd_extend_py(ipmi, d9h_trans_type_write_word, d9h_pec_report, d9h_pec_en, bus , target_addr , 0 , 0 , 0 , d9h_trans_potocol_pmbus , write_len , read_len , pmbus_cmd_aray)
     # Check pmbus rsp  data
     if(rsp == ERROR):
         print('ERROR!!! send pmbus error ! respond data error')
         SMART_PSU_RECOVERY(ipmi,default_ot_warm_low_byte, default_ot_warm_high_byte, bus, target_addr )
         return ERROR     
     # Send Package Thermal Status again via ME RAW PECI proxy. Check event happen
     resp = send_raw_peci_py(ipmi, peci_40h_client_addr_cpu0, peci_40h_interface_fall_back, 5, 5, raw_peci )
     if(resp == ERROR):
         print('ERROR!!! send_raw_peci(): respond data error')
         SMART_PSU_RECOVERY(ipmi,default_ot_warm_low_byte, default_ot_warm_high_byte, bus, target_addr )
         return ERROR
     #Check Thermal Status to make sure CPU prohot event happen
     if(ord(resp[4]) != 0x40):
         print('ERROR!!! send_raw_peci(): PCU respond data error')
         SMART_PSU_RECOVERY(ipmi,default_ot_warm_low_byte, default_ot_warm_high_byte, bus, target_addr )
         return ERROR
     prochot_sts        = get_bits_data_py( ord(resp[5]) , 2 , 1)
     prochot_sts_log    = get_bits_data_py( ord(resp[5]) , 3 , 1)
     print('SMART_001_WIN : prochot_sts = %d , prochot_sts_log =%d ' %(prochot_sts, prochot_sts_log))
     if( (prochot_sts == 0) and (prochot_sts_log==0)):
         print('SMART/CLST Fail! No PROCHOT event happen after event triggered ')
         SMART_PSU_RECOVERY(ipmi,default_ot_warm_low_byte, default_ot_warm_high_byte, bus, target_addr )
         return ERROR
     time.sleep(10)
     ##Check PL2 register make sure limiting is 0 watt
     # Prepare Package Thermal Status MSR 0x610  : RdpkgConfig , index 0x1B 
     raw_peci = peci_raw_rdpkgconfig(0, 27 , 0, 0 )
     # Send Package Thermal Status via ME RAW PECI proxy: Write length = 5 byte , Read_Length = 5 bytes
     resp = send_raw_peci_py(ipmi, peci_40h_client_addr_cpu0, peci_40h_interface_fall_back, 5, 5, raw_peci )
     if(resp == ERROR):
         print('ERROR!!! send_raw_peci(): respond data error')
         SMART_PSU_RECOVERY(ipmi,default_ot_warm_low_byte, default_ot_warm_high_byte, bus, target_addr )
         return ERROR
     if(ord(resp[4]) != 0x40):
         print('ERROR!!! send_raw_peci(): PCU respond data error')
         SMART_PSU_RECOVERY(ipmi,default_ot_warm_low_byte, default_ot_warm_high_byte, bus, target_addr )
         return ERROR
     #Check ME limiting value in PL2, suppose should be 0 watts
     if(ord(resp[6]) != 0x80):
         print('ERROR!!!  PL2 limiting value unexpected')
         SMART_PSU_RECOVERY(ipmi,default_ot_warm_low_byte, default_ot_warm_high_byte, bus, target_addr )
         return ERROR
     #Restor PSU OT_WARM_LIMIT value to default, suppose PROHOC event should gone!
     # Send PMbus Proxy cmd to write current Over Temperature Threshold value =  default_ot_warm value
     SMART_PSU_RECOVERY(ipmi,default_ot_warm_low_byte, default_ot_warm_high_byte, bus, target_addr )
     # Check pmbus rsp  data
     if(rsp == ERROR):
         print('ERROR!!! send pmbus error ! respond data error')
         return ERROR 
     #Delay 30 secs for PSU restore , then check if System go back to normal
     time.sleep(30)
     power_average_cap = read_power_py(ipmi, global_power_mode , platform_domain, AC_power_side, 0)
     if(power_average_cap == ERROR):
         print(SMART_001_WIN.__name__ + ':Platform power reading error  !!!')
         return ERROR
     if(power_average_cap < 0.8*power_average_stress):
         print (SMART_001_WIN.__name__ + 'ERROR!! After release SMART/CLST event, system no go back to normal')
         return ERROR

     return SUCCESSFUL

#Define PM_002 : Missing Power reading  test process in Mehlow Windows
def PM_002_WIN(ipmi):
     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 30secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS, LOG_SAVE_OFF )
     #Waiting 20 secs for PTU stress ready
     print(PM_002_WIN.__name__ + ':Waiting 20 secs for PTU stress ready....')     
     time.sleep(20)
     # Read Platform Power via 0xC8h cmd
     power_average_stress = read_power_py(ipmi , global_power_mode, platform_domain,AC_power_side, 0 )
     if(power_average_stress == ERROR):
         print(PM_002_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Power Reading OK
     print(PM_002_WIN.__name__ + ':Platform Power Reading OK')
     print(PM_002_WIN.__name__ + ':Currently Full Stress Average Platform Power Reading = %6d watts' %power_average_stress)
     # Read Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, platform_domain, 0, 1, 0)
     # Check if Power Draw Range data are correct
     if(max_draw_range > (0.8*power_average_stress) and (0.8*power_average_stress) > min_draw_range):
         # Power Draw Range OK
         print(PM_002_WIN.__name__ + ':Platform Power Draw Range Setting OK')
         print(PM_002_WIN.__name__ + ":Power Capping value = %6d watt" % (power_average_stress*4/5))
     else:
         print(PM_002_WIN.__name__ + ':Error ! Platform Power Draw Rnage Setting Error!!!')
         return ERROR
     # Check if Correction time data are correct
     if(min_correction_time == ERROR):
         print(PM_002_WIN.__name__ + ':Error! Correction Time value not correct !!!')
         return ERROR
     # Correction Time OK
     print(PM_002_WIN.__name__ + ':Correction Time Value OK')
     print(PM_002_WIN.__name__ + ":Set correction time value = %6d msec" % (min_correction_time))
     #Read CPU Power Readgin before Set Missing Power Policy
     # Read CPU Power via 0xC8h cmd
     cpu_power_stress = read_power_py(ipmi, global_power_mode , cpu_domain, AC_power_side, 0)
     if(cpu_power_stress == ERROR):
         print(PM_002_WIN.__name__ + ':CPU power reading error!!!')
         return ERROR         
     # Set Power Capping via 0xC1h cmd in police id #3, target limit = 80% of full stress value, correction time = minimum support correction time
     # Set throttle percentage = 100%
     throttle_level = 100
     # Set policy trigger lmit = 0.1sec
     trigger_limit = 1
     sts = set_nm_power_policy_py( ipmi, c1h_platform_domain, c1h_policy_enable, 3, c1h_missing_power_reading_trigger, c1h_add_policy, c1h_auto_aggressive, c1h_presistent, c1h_alert_enable, c1h_shutdown_disable, AC_power_side, throttle_level , min_correction_time, trigger_limit, c1h_minimum_report_period )
     if(sts == ERROR):
         print(PM_002_WIN.__name__ + ':set_nm_power_policy fail !!!')
         return ERROR
     #Chane PSU slave address and Reset BMC to make power source missing happen.
     psu1_addr = 0
     sts = set_psu_configuation_py(ipmi, d7h_platform_domain, psu1_addr, psu1_addr, psu1_addr, psu1_addr, psu1_addr, psu1_addr, psu1_addr, psu1_addr)
     if(sts == ERROR):
         print(PM_002_WIN.__name__ + ':set psu configuation addr fail !!!')
         return ERROR
     #Reset BMC in case power source is from BMC
#     ipmi.target = pyipmi.Target(target_bmc_addr)
#     target_routing = [(0x20,0)]
#     ipmi.target.set_routing(target_routing)
#     sts = cold_reset_py(ipmi)
#     if(sts == ERROR):
#         print(PM_002_WIN.__name__ + ':Reset BMC Fail! If your power source is BMC , please contact with BMC for this fail!!!')
#         return ERROR
     #Change Aardvark target to ME
#     ipmi.target = pyipmi.Target(target_me_addr)
#     target_routing = [(0x2c,6)]
#     ipmi.target.set_routing(target_routing)
     # Read Platform Power via 0xC8h cmd again to make sure power drop
     print(PM_002_WIN.__name__ + ':Waiting 40 secs for Miss Power reading triggered ready....')
     time.sleep(40) # Wait for Missing power reading event happen 
     power_average_cap = read_power_py(ipmi, global_power_mode , platform_domain, AC_power_side, 0)
     if(power_average_cap == ERROR):
         print(PM_002_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Below is check the power reading value to make sure if power capping really work. Make sure power drop to capping value.
     elif(power_average_cap != 0 ):
         print(PM_002_WIN.__name__ + ':Can not Trigger Missing Power Event !!! Platfrom power reading still Exist !!!')
         print(PM_002_WIN.__name__ + ':Current Platform Power Reading value = %6d' %power_average_cap)
         return ERROR
     # Check if Limiting Policy ID =  3 via 0xF2 cmd
     limiting_policy_id = get_limiting_policy_id(ipmi , f2h_platform_domain )
     print(PM_002_WIN.__name__  + ': Current Limiting Policy ID = %d' %limiting_policy_id)
     if(limiting_policy_id != 3):
          print(PM_002_WIN.__name__ + ': Boot Time Power limit error!!! Limiting Policy ID not correct !!! Should Be ID 0 to limit power')
          return ERROR          
     #Read CPU Power again make sure CPU Power be capping after policy triggered happen     
     cpu_power_cap = read_power_py(ipmi, global_power_mode , cpu_domain, AC_power_side, 0)
     if(cpu_power_cap == ERROR):
         print(PM_002_WIN.__name__ + ':CPU power reading error!!!')
         return ERROR
     # Below is check the power reading value to make sure if power capping really work. Make sure power drop to capping value.
     elif(cpu_power_cap > cpu_power_stress*50/100):
         print(PM_002_WIN.__name__ + ':Missing Power limit error!!! CPU power reading still higher than capping value !!!')
         print(PM_002_WIN.__name__ + ':before capping cpu power reading value = %6d , But currecnt CPU power reading %6d' %(cpu_power_stress , cpu_power_cap))
         return ERROR
     # Power Reading OK
     print(PM_002_WIN.__name__  + ':CPU Power Reading OK')
     print(PM_002_WIN.__name__  + ':After NM Capping average platform power reading = %6d watts' %power_average_cap)
     # Check CPU Throttle % statistic via 0xC8h to make sure policy behavior is correct
     cpu_throttle_percentage = read_power_py(ipmi , global_throttling_sts_mode, platform_domain,AC_power_side, 0 )
     if(power_average_stress == ERROR):
         print(PM_002_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     if(cpu_throttle_percentage != throttle_level):
         print(PM_002_WIN.__name__ + ': CPU throttle percentage = %d. It is incorrect!! Correct throttle percentage should be %d percentage reading error!!!' %(cpu_throttle_percentage,throttle_level))
         return ERROR
     else:
         print(PM_002_WIN.__name__ + ': CPU throttle percentage = %d.' %cpu_throttle_percentage)

     return SUCCESSFUL

#Define PM_003 test: Set Total Power Budget control process in Mehlow Windows
def PM_003_WIN(ipmi):

     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 80secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS, LOG_SAVE_OFF )
     time.sleep(30)
     # Read Platform Power via 0xC8h cmd
     power_average_stress = read_power_py(ipmi , global_power_mode, platform_domain,AC_power_side, 0 )
     if(power_average_stress == ERROR):
         print(PM_003_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Power Reading OK
     print(PM_003_WIN.__name__ + ':Platform Power Reading OK')
     print(PM_003_WIN.__name__ + ':Currently Full Stress Average Platform Power Reading = %6d watts' %power_average_stress)
     # Send C0h Disable NM policy control
     print(PM_003_WIN.__name__ + ':Disable NM Policy Control before test Set Maximum allowed P/T state function')
     rsp = enable_disable_nm_policy_control_py(ipmi , c0h_global_disable , c0h_platform_domain , 1 )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     #Set power budget to 50% of full stress platform power watts
     total_power_budget = 0.5*power_average_stress
     print(PM_003_WIN.__name__ + ':Set power budget to %d watts' %total_power_budget)
     # Coverter 0 watt power_budget  int value to hex value for byte[6:5]- Power Budget
     set_power_budget = int_to_hex( total_power_budget , 2 )
     # No control component id settings
     component_id = 0
     rsp = set_total_power_budget_py(ipmi, d0h_platform_domain , d0h_component_control_disable , set_power_budget , component_id )
     # Check if rsp data correct
     sts = ipmi_resp_analyst_py( ord(rsp[0]), OEM )
     if(sts != SUCCESSFUL ):
         return ERROR
     # Read Platform Power via 0xC8h cmd again to make sure power drop
     time.sleep(3) # Wait for power drop after capping time longer than correction time settings
     power_average_cap = read_power_py(ipmi, global_power_mode , platform_domain, AC_power_side, 0)
     if(power_average_cap == ERROR):
         print(PM_003_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Below is check the power reading value to make sure if power capping really work. Make sure power drop to capping value.
     elif(power_average_cap > power_average_stress*55/100):
         print(PM_003_WIN.__name__ + ':Power limit error!!! Platfrom power reading still higher than limit value !!!')
         return ERROR
     # Power Reading OK
     print(PM_003_WIN.__name__  + ':Platform Power Reading OK')
     print(PM_003_WIN.__name__  + ':After Set Total Power Budget, current average platform power reading = %6d watts' %power_average_cap)

     return SUCCESSFUL

#Define PM_004 : Set Power Draw Range process in Mehlow Windows 
def PM_004_WIN(ipmi):
     # Read Domain 0 Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, platform_domain , 0, 1, 0)
     # Check if Power Draw Range data are correct
     if(max_draw_range >  min_draw_range):
         # Power Draw Range OK
         print(PM_004_WIN.__name__ + ':Platform Power Draw Range Read OK')
         print(PM_004_WIN.__name__ + ":Current Maximum Power Draw Range= %6d watt, Minimum Power Draw Range = %6d" % (max_draw_range, min_draw_range))
     else:
         print(PM_004_WIN.__name__ + ':Error ! Platform Power Draw Rnage Error!!!')
         return ERROR    
     #Set Power Draw range via 0xCBh cmd in platform domain :  maximum power drange range in domain 0 = 500 watts , minimum power drange range = 10 watts
     sts = set_nm_power_draw_range_py(ipmi, cbh_platform_domain , 10 , 500 )
     if(sts == ERROR):
         print(PM_004_WIN.__name__ + ':set_nm_power_draw_range 0xCBh fail !!!')
         return ERROR
     # Check result : Read Domain 0 Power Draw Range and Correction time via 0xC9h cmd again
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, platform_domain , 0, 1, 0)
     # Check if Power Draw Range data are correct
     if((max_draw_range == 500) and  (min_draw_range == 10)):
         # Power Draw Range OK
         print(PM_004_WIN.__name__ + ':Platform Power Draw Range Set OK')
         print(PM_004_WIN.__name__ + ":Current Maximum Power Draw Range= %6d watt, Minimum Power Draw Range = %6d" % (max_draw_range, min_draw_range))
     else:
         print(PM_004_WIN.__name__ + ':Error ! Platform Power Draw Rnage Error!!!')
         return ERROR
     
     return SUCCESSFUL

#Define PM_005 test process in Mehlow Windows : Read HW Prtection domain reading
def PM_005_WIN(ipmi):

     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 80secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS, LOG_SAVE_OFF )
     time.sleep(30)
     # Read HW Prtection domain (#3) Power via 0xC8h cmd
     power_average_stress = read_power_py(ipmi , global_power_mode, hw_protection_domain,DC_power_side, 0 )
     if(power_average_stress == ERROR):
         print(PM_005_WIN.__name__ + ':DC side power reading error!!!')
         return ERROR
     # Power Reading OK
     print(PM_005_WIN.__name__ + '::DC side Power Reading OK')
     print(PM_005_WIN.__name__ + ':Currently Full Stress Average :DC side Power Reading = %6d watts' %power_average_stress)
     # Read Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, hw_protection_domain, 0, 1, 1)
     # Check if Power Draw Range data are correct
     if(max_draw_range > (0.8*power_average_stress) and (0.8*power_average_stress) > min_draw_range):
         # Power Draw Range OK
         print(PM_005_WIN.__name__ + ':DC side Power Draw Range Setting OK')
         print(PM_005_WIN.__name__ + ":Power Capping value = %6d watt" % (power_average_stress*4/5))
     else:
         print(PM_005_WIN.__name__ + ':Error ! DC side Power Draw Rnage Setting Error!!!')
         return ERROR
     # Check if Correction time data are correct
     if(min_correction_time == ERROR):
         print(PM_005_WIN.__name__ + ':Error! Correction Time value not correct !!!')
         return ERROR
     # Correction Time OK
     print(PM_005_WIN.__name__ + ':Correction Time Value OK')
     print(PM_005_WIN.__name__ + ":Set correction time value = %6d msec" % (min_correction_time))
     # Set Power Capping via 0xC1h cmd in police id #3, target limit = 80% of full stress value, correction time = minimum support correction time
     sts = set_nm_power_policy_py( ipmi, c1h_platform_domain, c1h_policy_enable, 3, c1h_no_policy_trigger, c1h_add_policy, c1h_auto_aggressive, c1h_presistent, c1h_alert_enable, c1h_shutdown_disable, DC_power_side, (power_average_stress*4/5), min_correction_time, c1h_trigger_limit_null, c1h_minimum_report_period )
     if(sts == ERROR):
         print(PM_005_WIN.__name__ + ':set_nm_power_policy fail !!!')
         return ERROR
     # Read Platform Power via 0xC8h cmd again to make sure power drop
     time.sleep(3) # Wait for power drop after capping time longer than correction time settings
     power_average_cap = read_power_py(ipmi, global_power_mode , hw_protection_domain, DC_power_side, 0)
     if(power_average_cap == ERROR):
         print(PM_005_WIN.__name__ + ':DC side Power reading error!!!')
         return ERROR
     # Below is check the power reading value to make sure if power capping really work. Make sure power drop to capping value.
     elif(power_average_cap > power_average_stress*85/100):
         print(PM_005_WIN.__name__ + ':Power limit error!!! DC side Power reading still higher than capping value !!!')
         print(PM_005_WIN.__name__ + ':Expected limit value = %6d , But currecnt platfrom power reading %6d' %((power_average_stress*4/5) , power_average_cap))
         return ERROR
     # Power Reading OK
     print(PM_005_WIN.__name__  + ':DC side Power Reading OK')
     print(PM_005_WIN.__name__  + ':After NM Capping average platform power reading = %6d watts' %power_average_cap)

     return SUCCESSFUL

#Define PM_006 test process in Mehlow Windows : Read HW Prtection domain limiting
def PM_006_WIN(ipmi):

     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 80secs
     ssh_send_cmd_switch(background_run_enable,  PTUGEN_PATH , PTUGEN_P100_30SECS, LOG_SAVE_OFF )
     time.sleep(30)
     # Read HW Prtection domain (#3) Power via 0xC8h cmd
     power_average_stress = read_power_py(ipmi , global_power_mode, hw_protection_domain,DC_power_side, 0 )
     if(power_average_stress == ERROR):
         print(PM_006_WIN.__name__ + ':DC side power reading error!!!')
         return ERROR
     # Power Reading OK
     print(PM_006_WIN.__name__ + '::DC side Power Reading OK')
     print(PM_006_WIN.__name__ + ':Currently Full Stress Average :DC side Power Reading = %6d watts' %power_average_stress)
     # Read Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, hw_protection_domain, 0, 1, 1)
     # Check if Power Draw Range data are correct
     if(max_draw_range > (0.8*power_average_stress) and (0.8*power_average_stress) > min_draw_range):
         # Power Draw Range OK
         print(PM_006_WIN.__name__ + ':DC side Power Draw Range Setting OK')
         print(PM_006_WIN.__name__ + ":Power Capping value = %6d watt" % (power_average_stress*4/5))
     else:
         print(PM_006_WIN.__name__ + ':Error ! DC side Power Draw Rnage Setting Error!!!')
         return ERROR
     # Check if Correction time data are correct
     if(min_correction_time == ERROR):
         print(PM_006_WIN.__name__ + ':Error! Correction Time value not correct !!!')
         return ERROR
     # Correction Time OK
     print(PM_006_WIN.__name__ + ':Correction Time Value OK')
     print(PM_006_WIN.__name__ + ":Set correction time value = %6d msec" % (min_correction_time))
     # Set Power Capping via 0xC1h cmd in police id #3, target limit = 80% of full stress value, correction time = minimum support correction time
     sts = set_nm_power_policy_py( ipmi, c1h_platform_domain, c1h_policy_enable, 3, c1h_no_policy_trigger, c1h_add_policy, c1h_auto_aggressive, c1h_presistent, c1h_alert_enable, c1h_shutdown_disable, DC_power_side, (power_average_stress*4/5), min_correction_time, c1h_trigger_limit_null, c1h_minimum_report_period )
     if(sts == ERROR):
         print(PM_006_WIN.__name__ + ':set_nm_power_policy fail !!!')
         return ERROR
     # Read Platform Power via 0xC8h cmd again to make sure power drop
     time.sleep(3) # Wait for power drop after capping time longer than correction time settings
     power_average_cap = read_power_py(ipmi, global_power_mode , hw_protection_domain, DC_power_side, 0)
     if(power_average_cap == ERROR):
         print(PM_006_WIN.__name__ + ':DC side Power reading error!!!')
         return ERROR
     # Below is check the power reading value to make sure if power capping really work. Make sure power drop to capping value.
     elif(power_average_cap > power_average_stress*85/100):
         print(PM_006_WIN.__name__ + ':Power limit error!!! DC side Power reading still higher than capping value !!!')
         print(PM_006_WIN.__name__ + ':Expected limit value = %6d , But currecnt platfrom power reading %6d' %((power_average_stress*4/5) , power_average_cap))
         return ERROR
     # Power Reading OK
     print(PM_006_WIN.__name__  + ':DC side Power Reading OK')
     print(PM_006_WIN.__name__  + ':After NM Capping average platform power reading = %6d watts' %power_average_cap)

     return SUCCESSFUL

## Function : BTG_003 Test Process: Verify  OOB BTG Commmunication-Version check
def BTG_003_WIN(ipmi):
     # Send 0x82h Get BTG Health cmd to make sure BTG function enabled and support profile 4 FVE
     rsp, force_btg_acm_boot_profile, pbe_sts, enf_sts, measure_boot, verify_boot, btg_disable_in_fpf = get_boot_guard_health_py(ipmi)
     if(force_btg_acm_boot_profile != 1 ): #byte8[5]
          print('Error ! SPS FW BTG - Force Boot Guard ACM Boot Policy is %d, correct status must 1  ' %force_btg_acm_boot_profile)
          return ERROR
     elif(pbe_sts != 1 ):#byte9[5]
          print('Error ! SPS FW BTG - Protect BIOS Environment Policy (PBE) Status is %d, correct status must 1  ' %pbe_sts)
          return ERROR
     elif(enf_sts != 3 ):#byte9[7:6]
          print('Error ! SPS FW BTG - Error Enforcement Policy (ENF) is %d, correct status must 3  ' %enf_sts)
          return ERROR
     elif(measure_boot != 0 ):#byte10[0]
          print('Error ! SPS FW BTG - Measured Boot Policy (M) is %d, correct status must 0  ' %measure_boot)
          return ERROR
     elif(verify_boot != 1 ):#byte10[1]
          print('Error ! SPS FW BTG - Verified Boot Policy (V) is %d, correct status must 1  ' %verify_boot)
          return ERROR
     elif(btg_disable_in_fpf != 1 ):#byte12[6]
          print('Error ! SPS FW BTG - BTG is disabled in PCH fuse status is %d, correct status must 1  ' %btg_disable_in_fpf)
          return ERROR
     else:
          print('ERROR!! PTT version incorrect ... Check FW status and XML file settings')
          return ERROR

     return ERROR

## Function : PTT_003 Test Process: Verify  OOB PTT Commmunication -Capability check
def PTT_003_WIN(ipmi):
     # Send 0x71h Get PTT Capability cmd to make sure PTT function is enabled 
     ptt_support = get_ptt_capabilties_py(ipmi)
     if(ptt_support == 0):
          print('SPS FW PTT fcuntion currently is Not support in this system. Check if XML file settings is correct and function settings must enabled.')
          return ERROR
     elif(ptt_support == 1 ):
          print('SPS FW PTT fcuntion support , BUT currently function is Not be enabled in this system. Check XML file settings')
          return ERROR
     elif(ptt_support == 3 ):
          print('SPS FW PTT fcuntion support and enabled.')
          return SUCCESSFUL
     else:
          print('ERROR!! PTT in unknown state... Check FW status and XML file settings')
          return ERROR

     return ERROR

## Function : PTT_004 Test Process: Verify  OOB PTT Commmunication-Version check
def PTT_004_WIN(ipmi):
     # Send 0x71h Get PTT Capability cmd to make sure PTT function is enabled 
     ptt_version, ptt_interface_version, security_version, patch_version, major_version, minor_version = get_ptt_version_py(ipmi)
     if(ptt_version == 1 ):
          print('SPS FW PTT version is %d , Support PTT gen 3.0' %ptt_version)
          return SUCCESSFUL
     else:
          print('ERROR!! PTT version incorrect ... Check FW status and XML file settings')
          return ERROR

     return ERROR

#Define Chassis_power_on cmd  for Mehlow
def DC_CYCLE(ipmi):
     # Change Aardvark target to BMC for power status check
     ipmi.target = pyipmi.Target(target_bmc_addr)
     target_routing = [(0x20,0)]
     ipmi.target.set_routing(target_routing)
     ipmi, power_status = get_chassis_status_py(ipmi)
     print(DC_CYCLE.__name__ + 'power status = %d ' %power_status )
     # Shutdown OS 
     if(power_status == 1):
         # Shutdown OS and DC power via ACPI process
         ssh_send_cmd_switch(background_run_enable,  SSH_CMD_PATH_EMPTY , centos_dc_off, LOG_SAVE_OFF )
         # Waiting 30 secs to make sure system turn off
         print(DC_CYCLE.__name__ + ':Wait 30 secs for OS shutdown to S5')
         time.sleep(30) 
         # Check if system in power off mode
         ipmi, power_status = get_chassis_status_py(ipmi)
         if(power_status != 0 ):
             print(DC_CYCLE.__name__ + 'Error !! Can Not shutdown system normally ' )
             print(DC_CYCLE.__name__ + 'power status = %d ' %power_status )
             return ERROR
     # Turn on system power 
     elif(power_status == 0):         
         ipmi, sts = chassis_control_py(ipmi , chassis_control_on)
         if(sts == ERROR):
             print(DC_CYCLE.__name__ + ':chassis power on fail !!!')
             return ERROR
         # delay 180 secs for system power on and boot into OS again 
         print(DC_CYCLE.__name__ + ':Wait 180 secs for system boot up to OS')
         #time.sleep(180)
         OS_STS = 0
         timeout = 0
         #Check if OS is available
         while(OS_STS == 0 and timeout != OS_BOOT_FAIL_TIMEOUT):
             OS_STS = check_os_available()
             DEBUG('OS Not Ready , OS_STS = %d' %OS_STS)
             time.sleep(1)
             timeout = timeout + 1
             
          # Check if system in power on mode
         ipmi, power_status = get_chassis_status_py(ipmi)
         if(power_status != 1 ):
             print(DC_CYCLE.__name__ + 'Error !! Can Not turn on system normally ' )
             print(DC_CYCLE.__name__ + 'power status = %d ' %power_status )
             return ERROR 

     return ipmi, SUCCESSFUL

#Define Chassis_power reset cmd  for Mehlow
def RESET_CYCLE(ipmi):
     # Change Aardvark target to BMC for power status check
     ipmi.target = pyipmi.Target(target_bmc_addr)
     target_routing = [(0x20,0)]
     ipmi.target.set_routing(target_routing)
     ipmi, power_status = get_chassis_status_py(ipmi)
     print(DC_CYCLE.__name__ + 'power status = %d ' %power_status )
     # Reset system power 
     if(power_status == 1):         
         ipmi, sts = chassis_control_py(ipmi , chassis_control_reset)
         if(sts == ERROR):
             print(DC_CYCLE.__name__ + ':chassis power on fail !!!')
             return ERROR
         # delay 23 secs for system power on and boot into OS again 
         print(DC_CYCLE.__name__ + ':Wait 23 secs for system boot up to S0')
         time.sleep(23)
          # Check if system in power on mode
         ipmi, power_status = get_chassis_status_py(ipmi)
         if(power_status != 1 ):
             print(DC_CYCLE.__name__ + 'Error !! Can Not turn on system normally ' )
             print(DC_CYCLE.__name__ + 'power status = %d ' %power_status )
             return ERROR

     return ipmi, SUCCESSFUL

#Define Chassis_power_on cmd  for Mehlow
def DC_CYCLE_LOOP_WIN(ipmi , loop):
     count = 0
     print(DC_CYCLE_LOOP_WIN.__name__ + 'Start DC CYCLE LOOP TEST .... ')
     for count in range(0, loop):
         print(DC_CYCLE_LOOP_WIN.__name__ + 'Current Loop # %d ' %count)
         ipmi, sts = DC_CYCLE(ipmi)
         if(sts == ERROR):
             print(DC_CYCLE_LOOP_WIN.__name__ + ':DC CYCLE LOOP TEST FAIL !!!')
             return ERROR  
         # Re-initial ipmi for ME bridge cmd
         ipmi.target = pyipmi.Target(target_me_addr)
         target_routing = [(0x2c,6)]
         ipmi.target.set_routing(target_routing)
         # Check ME status make sure ME FW in normal operation state
         rsp, current_status, operation_state , eop = mesdc_get_version_py(ipmi)
         if(current_status !=5):
              print(DC_CYCLE_LOOP_WIN.__name__ + ': ME FW not in normal operation state. DC CYCLE LOOP TEST FAIL !!!')
              return ERROR
         ipmi, sts = DC_CYCLE(ipmi)
         if(sts == ERROR):
             print(DC_CYCLE_LOOP_WIN.__name__ + ':DC CYCLE LOOP TEST FAIL !!!')
             return ERROR
         # Re-initial ipmi for ME bridge cmd
         ipmi.target = pyipmi.Target(target_me_addr)
         target_routing = [(0x2c,6)]
         ipmi.target.set_routing(target_routing)
         # Check ME status make sure ME FW in normal operation state
         rsp, current_status, operation_state, eop = mesdc_get_version_py(ipmi)
         if(current_status !=5):
              print(DC_CYCLE_LOOP_WIN.__name__ + ': ME FW not in normal operation state. DC CYCLE LOOP TEST FAIL !!!')
              return ERROR
         count = count + 1 

     return SUCCESSFUL

#Define Chassis_power_on cmd  for Mehlow
def RESET_CYCLE_LOOP_WIN(ipmi , loop):
     count = 0
     print(RESET_CYCLE_LOOP_WIN.__name__ + 'Start RESET CYCLE LOOP TEST .... ')
     for count in range(0, loop):
         print(RESET_CYCLE_LOOP_WIN.__name__ + 'Current Loop # %d ' %count)
         ipmi, sts = RESET_CYCLE(ipmi)
         if(sts == ERROR):
             print(DC_CYCLE_LOOP_WIN.__name__ + ':RESET CYCLE LOOP TEST FAIL !!!')
             return ERROR  
         # Re-initial ipmi for ME bridge cmd
         ipmi.target = pyipmi.Target(target_me_addr)
         target_routing = [(0x2c,6)]
         ipmi.target.set_routing(target_routing)
         # Check ME status make sure ME FW in normal operation state
         rsp, current_status, operation_state, eop = mesdc_get_version_py(ipmi)
         if(current_status !=5):
              print(RESET_CYCLE_LOOP_WIN.__name__ + ': ME FW not in normal operation state. DC CYCLE LOOP TEST FAIL !!!')
              return ERROR

         count = count + 1 

     return SUCCESSFUL

#Define MCTP_004 Test  for Mehlow
def MCTP_004_WIN(ipmi, mctp_device_number):
     print(MCTP_004_WIN.__name__ + 'Start MCTP_004 TEST, Please Make sure you MCTP device already be pluged in the PCIe slot .... ')
     eop = 0
     time_count = 0
     # Check if ME already in EOP state
     while( eop == 0):
         rsp, current_status, operation_state , eop= mesdc_get_version_py(ipmi)
         if(rsp == ERROR):
             print(MCTP_004_WIN.__name__ + ':MCTP_004 TEST FAIL !!!')
             return ERROR
         if(time_count > 600): # Make sure program will not go to dead loop due to system error status
             print(PTU_003_WIN.__name__ + ':PTU_003 TEST FAIL !!!')
             return ERROR
         time_count = time_count + 1
         time.sleep(1)
     # Check how many MCTP devices be discovered 
     if(eop == 1):
         print(MCTP_004_WIN.__name__ + ':ME received BIOS Send EOP, Start Check Number of MCTP devices be discovered')
         mctp_discovered = mesdc_get_mctp_statistic_py(ipmi)
         if(mctp_discovered != mctp_device_number):
             print(MCTP_004_WIN.__name__ + ':%d number of MCTP devices be plugged in system , But only  %d number of MCTP devices be discovered MCTP_004 TEST FAIL !!!' %(mctp_device_number , mctp_discovered ))
             return ERROR

     print(MCTP_004_WIN.__name__ + ':%d number of MCTP devices be found in system  ' %mctp_discovered)
     
     return SUCCESSFUL

#Define PTU_003 test process in Mehlow Windows
def PTU_003_WIN(ipmi):
     print(PTU_003_WIN.__name__ + ':NM PTU_003 TEST Start ....')
     # Read Platform Power via 0xC8h cmd, Make sure platform power reading is OK
     power_average_stress = read_power_py(ipmi , global_power_mode, platform_domain,AC_power_side, 0 )     
     if(power_average_stress == ERROR):
         print(PTU_003_WIN.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Read Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, platform_domain, 0, 1, 0)
     if(max_draw_range == ERROR):
         print(PTU_003_WIN.__name__ + ':NM PTU_003 Test fail because power draw range can not be received !!!')
         return ERROR
     # Send PTU Launch
     sts = set_ptu_launch_request_py(ipmi, nmptu_60h_launch )      
     if(sts == ERROR):
         print(PTU_003_WIN.__name__ + ':NM PTU_003 Test fail !!!')
         return ERROR     
     # Reset OS and DC power via ACPI process
     ssh_send_cmd_switch(background_run_enable,  SSH_CMD_PATH_EMPTY , centos_reset, LOG_SAVE_OFF )     
     # Waiting System Reboot.
     print(PTU_003_WIN.__name__ + ':Wait 30 secs for system reboot Test')
     time.sleep(30)
     # Check NM PTU Activate status
     manufacture_optin, bios_optin, bmc_activate, bios_activate, oem_empty_run, rom_launch, bmc_phase_only = mesdc_get_nm_ptu_launch_state_py(ipmi)
     if( (manufacture_optin != 1) or (bios_optin!= 1) or (bmc_activate != 1) or  (rom_launch != 1)):
         print(PTU_003_WIN.__name__ + ':NM PTU Lanuch status incorrect , NM PTU_003 Test fail !!!')
         print(PTU_003_WIN.__name__ + ':Correct state should be : manufacture_optin = 1, bios_optin = 1, bmc_activate = 1, rom_launch =1')        
         print(PTU_003_WIN.__name__ + ':manufacture_optin = %d , bios_optin = %d , bmc_activate = %d, bios_activate =%d , rom_launch = %d , bmc_phase_only = %d' %(manufacture_optin, bios_optin, bmc_activate , bios_activate, rom_launch , bmc_phase_only ))     
         return ERROR  
     # Waiting for NM PTU Test finish 
     print(PTU_003_WIN.__name__ + ':Wait 120 secs for NM PTU Calibration testing....')
     time.sleep(120)
     # Check if ME receive EOP
     eop = 0
     time_count = 0
     while(eop == 0):
         rsp, current_status, operation_state , eop= mesdc_get_version_py(ipmi)
         if(rsp == ERROR):
             print(PTU_003_WIN.__name__ + ':NM PTU_003 TEST FAIL !!!')
             return ERROR
         if(time_count > 300): # Make sure program will not go to dead loop due to system error status
             print(PTU_003_WIN.__name__ + ':NM PTU_003 TEST FAIL !!!')
             return ERROR
         time_count = time_count + 1
         time.sleep(1)
     # Get NM PTU Result via 0x61h cmd
     max_power, min_power, eff_power = get_ptu_launch_result_py(ipmi, nmptu_61h_platform)
     # Read Power Draw Range and Correction time via 0xC9h cmd again
     max_draw_range_ptu, min_draw_range_ptu, min_correction_time, max_correction_time = get_platform_power_draw_range_py( ipmi, platform_domain, 0, 1, 0)
     if(max_draw_range == ERROR):
         print(PTU_003_WIN.__name__ + ':NM PTU_003 Test fail because power draw range can not be received !!!')
         return ERROR
     #Check if Power draw range be automatically updated
     if( (max_draw_range_ptu != max_power) or (min_draw_range_ptu != min_power ) ):
         print(PTU_003_WIN.__name__ + ':NM PTU_003 Test fail because power draw range not be changed automatically !!!') 
         return ERROR

     #Waiting for 50 secs to make sure system already boot into OS again.
     print('Waiting for 50 secs to make sure system already boot into OS again... ')   
     time.sleep(50)     
     return SUCCESSFUL

def easy_loop():
     ipmi = aardvark_ipmi_init(target_me_addr, target_me_bridge_channel)
     val = 1
     while(val == 1):
         ipmi.target = pyipmi.Target(target_bmc_addr)
         target_routing = [(0x20,0)]
         ipmi.target.set_routing(target_routing)
         ipmi, power_status = get_chassis_status_py(ipmi)
         print( 'power status = %d ' %power_status )
         time.sleep(5)
         ipmi.target = pyipmi.Target(target_me_addr)
         target_routing = [(0x2c,6)]
         ipmi.target.set_routing(target_routing)
         rsp, current_status, operation_state = mesdc_get_version_py(ipmi)
         time.sleep(5)
     print('ERROR')
     return ERROR

def print_test_result():
     size = len(NM_TEST_STS)
     print('/////////////////////////// Test Result ////////////////////////////////////')
     count = 0
     for count in range(0, size ):
         if(NM_TEST_STS[count] == SUCCESSFUL):
              print(NM_TEST_ITEM[count] + ' Test : Pass ')
         elif(NM_TEST_STS[count] == NONE):
              print( NM_TEST_ITEM[count] + 'Not in test list ,  Not Test')
         else:
              print(NM_TEST_ITEM[count] + ' Test: Fail !!!')
              print('Please enable debug mode for more detail test information')
         
## Below is __Main__

#sts = 0
#while(sts == 0):
#     sts = check_os_available()
#     DEBUG('sts = %d' %sts)
     
# Initial aardvark
ipmi = aardvark_ipmi_init(target_me_addr, target_me_bridge_channel)
# Config Test List file
test_schedule = test_schedule()
sts = run_schedule_py(ipmi, test_schedule)
# Print Test Result
sts = print_test_result()

