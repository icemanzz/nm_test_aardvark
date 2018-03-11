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
              # below are PECI_000 ~ PECI_014
              ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE, ENABLE]
## Global Test Status
NM_TEST_STS = [NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, \
               # below are PECI_000 ~ PECI_014 test status
               NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE]

##Function :  Send IPMB cmd via aardvark and return response data 
def send_ipmb_aardvark(ipmi , netfn, raw):
     print('Send IPMB raw cmd via Aardvark : raw 0x%x %s' % (netfn , raw))
     raw_bytes = array.array('B', [int(d, 0) for d in raw[0:]])
     rsp = ipmi.raw_command(lun, netfn, raw_bytes.tostring())
     print('Response Data: ' + ' '.join('%02x' % ord(d) for d in rsp))
     return rsp

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

## Function : 0xDFH, Force SPS FW Recovery to default
def force_me_recovery(command):
     dfh_raw = dfh_raw_to_str(command)
     # Send 0xDFh with command option
     ipmisend1 = ipmi_network_bridge_raw_cmd_header + dfh_raw
     DEBUG('send dfh cmd: ' + ipmisend1)
     resp = os.popen(ipmisend1).read()
     DEBUG(resp)
     # Check if rsp data correct
     sts = ipmi_resp_analyst( resp, OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return SUCCESSFUL

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
     
## Function : 0xC9H, Get NM capability and platform power Draw Range
def get_platform_power_draw_range(c9h_domain, c9h_policy_trigger_type, c9h_policy_type, c9h_power_domain):
     c9h_raw = c9h_raw_to_str(c9h_domain, c9h_policy_trigger_type, c9h_policy_type, c9h_power_domain)
     # Send 0xC9h to know Power Draw Rnage
     ipmisend1 = ipmi_network_bridge_raw_cmd_header + c9h_raw
     DEBUG('send c9h cmd: ' + ipmisend1)
     resp = os.popen(ipmisend1).read()
     DEBUG(resp)
     # Check if rsp data correct
     sts = ipmi_resp_analyst( resp, OEM )
     if(sts != SUCCESSFUL ):
         return ERROR, ERROR, ERROR, ERROR
     # Calculate Max power draw range Byte[7:6] value, total 2 bytes
     max_draw_range = calculate_byte_value(resp, 6, 2)
     DEBUG('max_draw_range = %6d' %max_draw_range)
     # Calculate Min power draw range Byte[9:8] value, total 2 bytes
     min_draw_range = calculate_byte_value(resp, 8, 2)
     DEBUG('min_draw_range = %6d' %min_draw_range)
     if(max_draw_range > 0):
         DEBUG('Get Power Draw Range OK')
     else:
         DEBUG('!!! Get Power Draw Range Fail !!!')
         return ERROR, ERROR, ERROR, ERROR
     # Calculate Min correcction time Byte[13:10] value, total 4 bytes
     min_correction_time = calculate_byte_value(resp, 10, 4)
     DEBUG('minimun correction time = %6d' %min_correction_time)
     # Calculate Max correcction time Byte[17:14] value, total 4 bytes
     max_correction_time = calculate_byte_value(resp, 14, 4)
     DEBUG('maxmun correction time = %6d' %max_correction_time)
     if(min_correction_time > 0):
         DEBUG('Get correction time value OK')
     else:
         DEBUG('!!! Get correction time Fail !!!')
         return ERROR, ERROR, ERROR, ERROR


     return  max_draw_range, min_draw_range, min_correction_time, max_correction_time

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
def set_nm_power_policy( domain, policy_enable, policy_id, policy_trigger_type, policy_add, aggressive, storage_mode, alert, shutdown, power_domain, limit_value, min_correction_time, trigger_limit, report_period ):
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
     c1h_raw =  c1h_raw_to_str(domain, policy_enable, policy_id, policy_trigger_type, policy_add, aggressive, storage_mode, alert, shutdown, power_domain, limit, correction, trigger_point, statistic_period )
     ipmisend1 = ipmi_network_bridge_raw_cmd_header + c1h_raw
     DEBUG('send c1h cmd: ' + ipmisend1)
     resp = os.popen(ipmisend1).read()
     DEBUG(resp)
     # Check if rsp data correct
     sts = ipmi_resp_analyst( resp, OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return SUCCESSFUL

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


## Fucntion : Send IPMI GET Device ID
##            target = 0 = Send cmd to BMC.  target = 1 = Send cmd to ME
def get_device_id( target ):
     get_did_raw = get_did_raw_to_str()
     if(target == 0):
         # Send Get DID to BMC
         ipmisend1 = ipmi_network_raw_cmd_header + get_did_raw
         DEBUG('send Get DID cmd to BMC: ' + ipmisend1)
         resp = os.popen(ipmisend1).read()
         DEBUG(resp)
         # Check if rsp data correct
         sts = ipmi_resp_analyst( resp, App )
         if(sts != SUCCESSFUL ):
             return ERROR
         return resp
     elif(target == 1):
         # Send Get DID to ME
         ipmisend1 = ipmi_network_bridge_raw_cmd_header + get_did_raw
         DEBUG('send Get DID cmd to ME: ' + ipmisend1)
         resp = os.popen(ipmisend1).read()
         DEBUG(resp)
         # Check if rsp data correct
         sts = ipmi_resp_analyst( resp, App )
         if(sts != SUCCESSFUL ):
             return ERROR
         # Analyst get did resp data format
         # Get Major Version = resp byte4 bits[6:0]
         marjor_version    = get_bits_data( resp, 4 , 0 , 7)
         DEBUG('get_me_device_id : Marjor_version = %d' %marjor_version)
         # Get Device Available bit : byte4 bit[7] = 1 = device in boot loader mode. = 0 = normal operation mode.
         available_bit     = get_bits_data( resp, 4  , 7 , 1)
         DEBUG('get_me_device_id : Available Bit = %d' % available_bit)
         # Get Minor version (byte5 bit[7:4]) and Milestone version (byte5 bits[3:0])number
         milestone_version     = get_bits_data( resp, 5 , 0 , 4)
         DEBUG('get_me_device_id : milestone_version = %d' %milestone_version)
         minor_version         = get_bits_data( resp, 5 , 3 , 4)
         DEBUG('get_me_device_id : minor_version = %d' %minor_version)
         # Get Build version number byte14=A.B and byte15 bit[7:4] =C, build version = 100A+10B+C
         build_version_AB  = get_bits_data( resp, 14 , 0 , 8)
         DEBUG('get_me_device_id : build_version_AB = %d' %build_version_AB)
         build_version_C   = get_bits_data( resp, 15 , 4 , 4)
         DEBUG('get_me_device_id : build_version_C Bit = %d' %build_version_C)
         sps_version = format(marjor_version, '02x') + '.' + format(minor_version, '02x') + '.' + format(milestone_version, '02x') + '.' + format(build_version_AB,'02x')+format(build_version_C, 'x')
         DEBUG('Current SPS FW version = ' + sps_version )
         # Get byte11 bit[7:0] platform SKU
         platform = get_bits_data( resp, 11 , 0 , 8)
         DEBUG('get_me_device_id : platform = %d' %platform)
         # Get byte13 bit[3:0] DCMI version, bytes13 bit[7:4] = NM version
         nm = get_bits_data( resp, 13 , 0 , 4)
         DEBUG('get_me_device_id : nm = %d' %nm)
         dcmi   = get_bits_data( resp, 13 , 4 , 4)
         DEBUG('get_me_device_id : dcmi = %d' %dcmi)
         # Get byte16 bit[1:0] image flag
         image = get_bits_data( resp, 16 , 0 , 2)
         DEBUG('get_me_device_id : image_sts = %d' %image)
         return sps_version, platform , dcmi , nm , image
     else:
         DEBUG('get_me_device_id : traget parameter = %d no support' %target)
         return ERROR

     return ERROR

## Function : Restore SPS FW to manufacture default
def facture_default(command):
     # Send 0xDFh with command to ME
     sts = force_me_recovery(command)
     if(sts != SUCCESSFUL ):
         return ERROR
     if(command == 1):
         # Add delay time 5 secs to make sure me go back to stable mode
         time.sleep(10)
         # Check if SPS FW boot into recovery mode.
         # Send Get DID cmd to ME
         resp = get_device_id(get_did_target_me)
         # Check resp byte16 - image flag to see if SPS FW run in recover mode
     elif(command == 2):
         # Add delay time 5 secs to make sure me go back to stable mode
         time.sleep(10)
         # Check if SPS FW back to operation mode.
         # Send Get DID cmd to ME
         sps_version, platform, dcmi, nm, image  = get_device_id(get_did_target_me)
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
## Target = 0 = BMC
## Target = 1 = ME
def get_sel_time(target):
     get_sel_time_raw = get_sel_time_raw_to_str()
     if(target == 0):
         # Send Get SEL TIME to BMC
         ipmisend1 = ipmi_network_raw_cmd_header + get_sel_time_raw
         DEBUG('send Get SEL TIME cmd to BMC: ' + ipmisend1)
         resp = os.popen(ipmisend1).read()
         DEBUG(resp)
         # Check if rsp data correct
         sts = ipmi_resp_analyst( resp, Storage )
         if(sts != SUCCESSFUL ):
             return ERROR
         # Calculate RTC TIME value Byte[5:2] value, total 4 bytes
         rtc_time = calculate_byte_value(resp, 2, 4)
         DEBUG('rtc_time = %6d' %rtc_time)
         return rtc_time
     elif(target == 1):
        # Send Get SEL TIME to ME
         ipmisend1 = ipmi_network_bridge_raw_cmd_header + get_sel_time_raw
         DEBUG('send Get SEL TIME cmd to ME: ' + ipmisend1)
         resp = os.popen(ipmisend1).read()
         DEBUG(resp)
         # Check if rsp data correct
         sts = ipmi_resp_analyst( resp, Storage )
         if(sts != SUCCESSFUL ):
             return ERROR
         # Calculate RTC TIME value Byte[5:2] value, total 4 bytes
         rtc_time = calculate_byte_value(resp, 2, 4)
         DEBUG('rtc_time = %6d' %rtc_time)
         if(rtc_time > 4294967294):
             print('ERROR !!! ME CANNOT get Valid time from system RTC')
             print('!!! Check SYSTEM BIOS RTC TIME RANGE MUST between 1/Jan/2010 to 31/Dec/2079')
             return ERROR
         return rtc_time
     else:
         DEBUG('get_sel_time() : traget parameter = %d no support' %target)
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
def send_raw_peci(client_addr, interface, write_length, read_length, peci_cmd ):
     peci_40h_raw = peci_40h_raw_to_str(client_addr, interface, write_length, read_length, peci_cmd)
     # Send PECI PROXY to ME
     ipmisend1 = ipmi_network_bridge_raw_cmd_header + peci_40h_raw
     DEBUG('send raw PECI proxy cmd to ME: ' + ipmisend1)
     resp = os.popen(ipmisend1).read()
     DEBUG(resp)
     # Check if rsp data correct
     sts = ipmi_resp_analyst( resp, OEM )
     if(sts != SUCCESSFUL ):
         return ERROR

     return resp

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
def get_cpu_temp(cpu_id, peci_interface):
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
     resp = send_raw_peci(PECI_CLIENT_ADDR, peci_interface, 1, 2, raw_peci )
     if(resp == ERROR):
         DEBUG('ERROR!!! send_raw_peci(): respond data error')
         return ERROR
     # Ananlyst GetTemp Real value: GET PECI RESP DATA Byte[N:5] value, total 2 bytes = Read_Length
     get_temp_resp = calculate_byte_value(resp, 5, 2)
     # Transfer data to 2's complement value 4 bytes = 16 bits
     Tmargin = two_complement(get_temp_resp , 16)
     #  Tmargin is the DTS offset value to Tprohot.The resulotion is 1/64 degress C
     Tmargin = abs(( Tmargin / 64))
     DEBUG('PECI GetTemp() = Tmargin = %6d' %Tmargin)
     # Get Tprochot value
     # Prepare RdpkgConfig , index 16 , Thermal Target for Tjmax value
     raw_peci = peci_raw_rdpkgconfig(0, 16, 0, 0 )
     # Send GetTemp via ME RAW PECI proxy: Write length = 5 byte , Read_Length = 5 bytes
     resp = send_raw_peci(PECI_CLIENT_ADDR, peci_interface, 5, 5, raw_peci )
     if(resp == ERROR):
         DEBUG('ERROR!!! send_raw_peci(): respond data error')
         return ERROR
     # Calculate Tjmax value Byte8 of PECI resp data , total 1 byte
     Tjmax = calculate_byte_value(resp, 8, 1)
     DEBUG('CPU0 Tjmax = %6d' %Tjmax)
     # Calculate current CPU Die Temperature = Tjmax - Tmargin
     CPU_Temperature = Tjmax - Tmargin
     DEBUG('Current CPU Die Temperature = %6d' %CPU_Temperature )

     return CPU_Temperature

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
def get_sensor_reading(sensor_number, target):
     sn_number = int_to_hex( sensor_number, 1 )
     get_sensor_reading_raw = get_sensor_reading_raw_to_str(sn_number)
     if(target == get_sensor_reading_target_bmc):
         # Send PECI PROXY to BMC
         ipmisend1 = ipmi_network_raw_cmd_header + get_sensor_reading_raw
         DEBUG('send get sensor reading cmd to ME: ' + ipmisend1)
         resp = os.popen(ipmisend1).read()
     elif(target == get_sensor_reading_target_me):
         # Send PECI PROXY to ME
         ipmisend1 = ipmi_network_bridge_raw_cmd_header + get_sensor_reading_raw
         DEBUG('send get sensor reading cmd to ME: ' + ipmisend1)
         resp = os.popen(ipmisend1).read()
     else:
         DEBUG('get_sensor_reading(): ERROR!!! Target not support !!!')
         return ERROR
     DEBUG(resp)
     # Check if rsp data correct
     sts = ipmi_resp_analyst( resp, Sensor )
     if(sts != SUCCESSFUL ):
         DEBUG('get_sensor_reading() : ERROR !!! IPMI respond data error ')
         return ERROR
     # Check if sensor available : byte3 bit[5] = 1 means sensor unabailable. = 0 means sensor abailable
     available_bit = get_bits_data( resp, 3, 5, 1)
     DEBUG('get_sensor_reading : Available Bit = %d' %available_bit)
     # Check sensor scan settings : byte3 bit[6] = 0 means sensor scan disable. = 1 means sensor scan enable.
     scan_bit = get_bits_data( resp, 3, 6, 1)
     DEBUG('get_sensor_reading : Scan Bit = %d' %scan_bit)
     # Check event message settings : byte3 bit[7] = 0 means sensor event message disable. = 1 means sensor event message enable.
     event_message_bit = get_bits_data( resp, 3  , 7 , 1)
     DEBUG('get_sensor_reading : Event Message Bit = %d' %event_message_bit)
     # Check if sensor abailable
     if(available_bit == 1):
         DEBUG('get_sensor_reading : Sensor number %2x not abailable' %sensor_number )
         return ERROR
     # Calculate sensor reading value Byte2 of respond message , total 1 byte
     sensor_reading = calculate_byte_value(resp, 2, 1)

     return sensor_reading

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

## Function : NM_003 Test Process: Verify CPU domain power reading is accuracy.
def NM_003():
     # Check Global Switch value: Makue sure if test list include this test item
     if(NM_TEST_EN[3] == DISABLE):
         DEBUG('No NM_003 in test list. Transfer to next test item.')
         return SUCCESSFUL
     # Run load on host system with PTU 100% loading for 20secs
     os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' -t 3 > ' + PTU_MON_LOG)
     os.system('nohup ssh ' + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' -p 100 -t 30 &')
     # Add delay time 5 secs to make sure PTUGEN stress is stable
     time.sleep(5)
     # Read CPU Power via 0xC8h cmd
     power_average_stress = platform_power(global_power_mode , cpu_domain, AC_power_side, 0)
     if(power_average_stress == ERROR):
         print(NM_003.__name__ + ':CPU power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_003.__name__ + ':CPU Power Reading OK')
     print(NM_003.__name__ + ':Currently Full Stress Average CPU Power Reading = %6d watts' %power_average_stress)
     # Add time delay to make sure last ptugen stress is finish
     time.sleep(15)
     # RUN PTUGEN again and Read CPU Power from PTUMON Log
     os.system('nohup ssh ' + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' -p 100 -t 30 &')
     # Remove previous log file
     os.system('rm -rf ' + PTU_MON_LOG)
     # Add delay time 5 secs to make sure PTUGEN stress is stable
     time.sleep(5)
     # Start RUN PTUMON 3 secs
     os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' -t 3 > ' + PTU_MON_LOG)
     # Read PTUMON LOG
     ptumon_power = read_ptumon(cpu_domain)
     if(ptumon_power == ERROR):
         print(NM_003.__name__ + ':CPU power reading in PTUMON log error!!!')
         return ERROR
     # CPU Power Reading in PTUMON is OK
     print(NM_003.__name__ + ': PTUMON CPU Power Reading = %6d' %ptumon_power )
     # Compare the CPU power reading value between NM and PTUMON, the accuracy must below 3%
     if( (ptumon_power*0.97) < power_average_stress < (ptumon_power*1.03)):
         print(NM_003.__name__ + ':CPU power reading accuracy is pass')
     else:
         print(NM_003.__name__ + ':CPU power reading accuracy is error !!!')
         return ERROR

     return SUCCESSFUL

## Function : NM_004 Test Process: Verify Memory domain power reading is accuracy.
def NM_004():
     # Check Global Switch value: Makue sure if test list include this test item
     if(NM_TEST_EN[4] == DISABLE):
         DEBUG('No NM_004 in test list. Transfer to next test item.')
         return SUCCESSFUL
     # Run load on host system by PTU memory stress tool for 20secs
     os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' -t 3 > ' + PTU_MON_LOG)
     os.system('nohup ssh ' + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' -mt 3 -t 40 &')
     # Add delay time 15 secs to make sure PTUGEN stress is stable
     print(NM_004.__name__ + ': Wait 15 secs for Memory power stress stable...')
     time.sleep(15)
     # Read Memory Power via 0xC8h cmd
     power_average_stress = platform_power(global_power_mode , memory_domain, AC_power_side, 0)
     if(power_average_stress == ERROR):
         print(NM_004.__name__ + ':Memory power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_004.__name__ + ':Memory Power Reading OK')
     print(NM_004.__name__ + ':Currently Full Stress Average Memory Power Reading = %6d watts' %power_average_stress)
     # Add time delay 30 secs to make sure last ptugen stress is finish
     print(NM_004.__name__ + ':Wait 30 secs for PTU tool finish previous jobs....')
     time.sleep(30)
     # RUN PTUGEN again and Read Memory Power from PTUMON Log
     os.system('nohup ssh ' + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' -mt 3 -t 40 &')
     # Remove previous log file
     os.system('rm -rf ' + PTU_MON_LOG)
     # Add delay time 15 secs to make sure PTUGEN stress is stable
     print(NM_004.__name__ + ':Wait 15 secs for Memory power stress stable....')
     time.sleep(15)
     # Start RUN PTUMON 3 secs
     os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' -t 3 > ' + PTU_MON_LOG)
     # Read PTUMON LOG
     ptumon_power = read_ptumon(memory_domain)
     if(ptumon_power == ERROR):
         print(NM_004.__name__ + ':Memory power reading in PTUMON log error!!!')
         return ERROR
     # Memory Power Reading in PTUMON is OK
     print(NM_004.__name__ + ': PTUMON Memory Power Reading = %6f' %ptumon_power )
     # Compare the Memory power reading value between NM and PTUMON, the accuracy must below 3%
     if( (ptumon_power*0.97) < power_average_stress < (ptumon_power*1.03)):
         print(NM_004.__name__ + ':Memory power reading accuracy is pass')
     elif( (ptumon_power < 10) & abs((power_average_stress - ptumon_power)) < 1.5 ):
         print(NM_004.__name__ + ': This systems memory power consumption are very small < 10 watts druing memory stress test...')
         print(NM_004.__name__ + ': Suggest to increase DIMM numbers to improve test accuracy...')
         print(NM_004.__name__ + ': In this HW configuration, Memory Power difference is small than 1.5 watts. The result is Pass.')
     else:
         print(NM_004.__name__ + ':Memory power reading accuracy is error !!!')
         return ERROR

     return SUCCESSFUL

## Function : NM_006 Test Process: Verify ME RTC TIME is accuracy.
def NM_006():
     # Check Global Switch value: Makue sure if test list include this test item
     if(NM_TEST_EN[6] == DISABLE):
         DEBUG('No NM_006 in test list. Transfer to next test item.')
         return SUCCESSFUL
     # Get ME RTC TIME via 0x48 cmd
     print(NM_006.__name__ + ':Start checking if ME RTC cunter is normal...')
     loop = 0
     temp_time = 0
     for loop in range(0, 10):
         rtc_me = get_sel_time(get_sel_time_target_me)
         if(rtc_me == ERROR):
              DEBUG(NM_006.__name__ + ':ERROR!!! Get ME SEL TIME IPMI Resp data error!!!')
              return ERROR
         elif(rtc_me <= temp_time):
              DEBUG(NM_006.__name__ + ':ERROR !!! ME RTC count not move.')
              return ERROR
         # Get RTC data OK
         DEBUG(NM_006.__name__ + ':Get ME RTC OK')
         DEBUG(NM_006.__name__ + ':ME SEL RTC TIME Reading = %12d secs' %rtc_me)
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
     print(NM_006.__name__ + ':Get OS RTC TIME...')
     os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + OSRTC + ' > ' + OS_RTC_LOG)
     # Compare OS RTC TIME with ME RTC TIME
     print(NM_006.__name__ + ':Start compare ME RTC and OS RTC time...')
     rtc_os = read_keyword_file(OS_RTC_LOG, 'RTC' , 14 , 0 , 0)
     print('OS RTC Year = ' + rtc_os[0:4])
     print('OS RTC Month = ' + rtc_os[5:7])
     print('OS RTC Data = ' + rtc_os[8:10])
     print('OS RTC Hour = ' + rtc_os[11:13])
     print('OS RTC Min = ' + rtc_os[14:16])
     print('OS RTC Sec = ' + rtc_os[17:19])
     # Check if hour and min values are accuracy
     if((abs(rtc_me_hour - int(rtc_os[11:13],0)) > 1) or (abs(rtc_me_min - int(rtc_os[14:16],0)) > 1 ) ):
         print('ERROR !!! ME RTC hour or min values not accuracy')
         return ERROR
     # Check if ME RTC sec value accuracy. By default ME syncronize with Host RTC every 5 secs. So suppose sec difference value between ME RTC and Host msut small than 5 secs
     elif(abs(rtc_me_sec - int(rtc_os[17:19],0)) > 5 ):
         print('ERROR !!! ME RTC hour or min values not accuracy')
         return ERROR

     return SUCCESSFUL

## Function : NM_009 Test Process: Verify that power limiting is working correctly in platform power domain.
def NM_009():
     # Check Global Switch value: Makue sure if test list include this test item
     if(NM_TEST_EN[9] == DISABLE):
         DEBUG('No NM_009 in test list. Transfer to next test item.')
         return SUCCESSFUL
     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 30secs
     os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' ' + PTUMON_3SECS)
     os.system('nohup ssh ' + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' ' + PTUGEN_P100_30SECS + ' &')
     time.sleep(30)
     # Read Platform Power via 0xC8h cmd
     power_average_stress = platform_power(global_power_mode , platform_domain, AC_power_side, 0)
     if(power_average_stress == ERROR):
         print(NM_009.__name__ + ':Platform power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_009.__name__ + ':Platform Power Reading OK')
     print(NM_009.__name__ + ':Currently Full Stress Average Platform Power Reading = %6d watts' %power_average_stress)
     # Read Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range( platform_domain, 0, 1, 0)
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
     sts = set_nm_power_policy( c1h_platform_domain, c1h_policy_enable, 3, c1h_no_policy_trigger, c1h_add_policy, c1h_auto_aggressive, c1h_presistent, c1h_alert_enable, c1h_shutdown_disable, AC_power_side, (power_average_stress*4/5), min_correction_time, c1h_trigger_limit_null, c1h_minimum_report_period )
     if(sts == ERROR):
         print(NM_009.__name__ + ':set_nm_power_policy fail !!!')
         return ERROR
     # Read Platform Power via 0xC8h cmd again to make sure power drop
     time.sleep(3) # Wait for power drop after capping time longer than correction time settings
     power_average_cap = platform_power(global_power_mode , platform_domain, AC_power_side, 0)
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
def NM_010():
     # Check Global Switch value: Makue sure if test list include this test item
     if(NM_TEST_EN[10] == DISABLE):
         DEBUG('No NM_010 in test list. Transfer to next test item.')
         return SUCCESSFUL
     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 20secs
     os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' ' + PTUMON_3SECS)
     os.system('nohup ssh ' + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' ' + PTUGEN_P100_30SECS + ' &')
     time.sleep(5)
     # Read CPU Power via 0xC8h cmd
     power_average_stress = platform_power(global_power_mode , cpu_domain, AC_power_side, 0)
     if(power_average_stress == ERROR):
         print(NM_010.__name__ + ':CPU power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_010.__name__ + ':CPU Power Reading OK')
     print(NM_010.__name__ + ':Currently Full Stress Average CPU Power Reading = %6d watts' %power_average_stress)
     # Read Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range( cpu_domain, 0, 1, 0)
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
     sts = set_nm_power_policy( c1h_cpu_domain, c1h_policy_enable, 3, c1h_no_policy_trigger, c1h_add_policy, c1h_auto_aggressive, c1h_presistent, c1h_alert_enable, c1h_shutdown_disable, AC_power_side, (power_average_stress*4/5), min_correction_time, c1h_trigger_limit_null, c1h_minimum_report_period )
     if(sts == ERROR):
         print(NM_010.__name__ + ':set_nm_power_policy fail !!!')
         return ERROR
     # Read CPU Power via 0xC8h cmd again to make sure power drop
     time.sleep(3) # Wait for power drop after capping time longer than correction time settings
     power_average_cap = platform_power(global_power_mode , cpu_domain, AC_power_side, 0)
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

## Function : NM_011 Test Process: Verify that power limiting is working correctly in memory power domain.
def NM_011():
     # Check Global Switch value: Makue sure if test list include this test item
     if(NM_TEST_EN[11] == DISABLE):
         DEBUG('No NM_011 in test list. Transfer to next test item.')
         return SUCCESSFUL
     # Run load on host system with PTU 100% loading for 20secs
     os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' -t 3 > ' + PTU_MON_LOG)
     os.system('nohup ssh ' + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' -mt 3 -t 30 &')
     time.sleep(5)
     # Read Memory Power via 0xC8h cmd
     power_average_stress = platform_power(global_power_mode , memory_domain, AC_power_side, 0)
     if(power_average_stress == ERROR):
         print(NM_011.__name__ + ':Memory power reading error!!!')
         return ERROR
     # Power Reading OK
     print(NM_011.__name__ + ':Memory Power Reading OK')
     print(NM_011.__name__ + ':Currently Full Stress Average Memory Power Reading = %6d watts' %power_average_stress)
     # Read Power Draw Range and Correction time via 0xC9h cmd
     max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range( memory_domain, 0, 1, 0)
     # Check if Power Draw Range data are correct
     if(max_draw_range > (0.8*power_average_stress) and (0.8*power_average_stress) > min_draw_range):
         # Power Draw Range OK
         print(NM_011.__name__ + ':Memory Power Draw Range Setting OK')
         print(NM_011.__name__ + ":Power Capping value = %6d watt" % (power_average_stress*4/5))
     else:
         print(NM_011.__name__ + ':Error ! Memory Power Draw Rnage Setting Error!!!')
         return ERROR
     # Check if Correction time data are correct
     if(min_correction_time == ERROR):
         print(NM_011.__name__ + ':Error! Correction Time value not correct !!!')
         return ERROR
     # Correction Time OK
     print(NM_011.__name__ + ':Correction Time Value OK')
     print(NM_011.__name__ + ":Set correction time value = %6d msec" % (min_correction_time))
     # Set Power Capping via 0xC1h cmd in police id #3, target limit = 80% of full stress value, correction time = minimum support correction time
     sts = set_nm_power_policy( c1h_memory_domain, c1h_policy_enable, 3, c1h_no_policy_trigger, c1h_add_policy, c1h_auto_aggressive, c1h_presistent, c1h_alert_enable, c1h_shutdown_disable,  AC_power_side, (power_average_stress*4/5), min_correction_time, c1h_trigger_limit_null, c1h_minimum_report_period )
     if(sts == ERROR):
         print(NM_011.__name__ + ':set_nm_power_policy fail !!!')
         return ERROR
     # Read Memory Power via 0xC8h cmd again to make sure power drop
     time.sleep(3) # Wait for power drop after capping time longer than correction time settings
     power_average_cap = platform_power(global_power_mode , memory_domain, AC_power_side, 0)
     if(power_average_cap == ERROR):
         print(NM_011.__name__ + ':Memory power reading error!!!')
         return ERROR
     # Below is check the power reading value to make sure if power capping really work. Make sure power drop to capping value.
     elif(power_average_cap > power_average_stress*85/100):
         print(NM_011.__name__ + ':Power limit error!!! Platfrom power reading still higher than capping value !!!')
         print(NM_011.__name__ + ':Expected limit value = %6d , But currecnt platfrom power reading %6d' %((power_average_stress*4/5) , power_average_cap))
         return ERROR
     # Power Reading OK
     print(NM_011.__name__  + ':Memory Power Reading OK')
     print(NM_011.__name__  + ':After NM Capping average memory power reading = %6d watts' %power_average_cap)

     return SUCCESSFUL


## Function : PECI_004 Test Process: Verify PECI proxy function.
def PECI_004():
     # Check Global Switch value: Makue sure if test list include this test item
     if(NM_TEST_EN[19] == DISABLE):
         DEBUG('No PECI_004 in test list. Transfer to next test item.')
         return SUCCESSFUL
     # Send Get DID to ME to make sure the platform PECI configuation
     sps_version, platform, dcmi, nm, image  = get_device_id(get_did_target_me)
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
                    cpu_temp = get_cpu_temp(loop, interface )
                    if(cpu_temp == ERROR):
                         print('ERROR !!! CPU%d GetTemp PECI cmd via interface= %d fail!!!' %(loop, interface))
                         return ERROR
                    print('CPU%d Temp = %2d via interface= %d' %(loop, cpu_temp, interface))
          return SUCCESSFUL
     elif(platform == 9):
          print('SPS FW is run in Greenlow Platfrom, no Inbend PECI function support. Only test PECI wire.')
     else:
          print('unknown platform , test will include Inbend PECI and peci wire')
     print('ERROR !!! Exception Error in PECI_004 test')

     return ERROR

## Function : Detect current system configuation : CPU number , power source , DIMM numbers,
def system_config_detect():
     # Get SPS FW version
     sps_version, platform, dcmi, nm, image  = get_device_id(get_did_target_me)
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
     pch_tem = get_sensor_reading(pch_temp, get_sensor_reading_target_me)
     if(pch_tem == ERROR):
          print(system_config_detect.__name__ + ':Sensor number: %2x not exist' %pch_tem)
          # No PCH temperature reading data : Disable related test items.
     else:
          print('PCH Temperature = %2d' %pch_tem)
     # Detect CUPS sensor#
     cups_core_workload = get_sensor_reading(cups_core, get_sensor_reading_target_me)
     if(cups_core_workload == ERROR):
          print(system_config_detect.__name__ + ': CUPS core Workload Sensor number: %2s not exist' %cups_core_workload)
         # No CUPS Core Workload reading data : Disable related test items. Disable CUPS_001~CUPS_005
     else:
          print('CPU CORE CUPS Workload Reading = %2d' %cups_core_workload)
     # Detect Platfrom power source via Get PSU configuation, BMC E2 OEM cmd and HSC sensor #
     # Detect SMART/CLST function via Sensor# and Get PSU configuation
     # Detect HPIO source via sensor#0xAE and 0xDEh
     hpio_pwr_reading = get_sensor_reading(hpio_domain_pwr, get_sensor_reading_target_me)
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
               hpio_pwr_reading = get_sensor_reading(loop, get_sensor_reading_target_me)
               if(hpio_pwr_reading != ERROR):
                    print(system_config_detect.__name__ + ': HPIO PWR dedicated sensor number: %2x exist' %loop)
                    print(system_config_detect.__name__ + ': HPIO snnsor number : 0x%2x reading = %2d' %(loop, hpio_pwr_reading))
                     # Enable HPIO related test items
                    NM_TEST_EN[ 5] = ENABLE
                    NM_TEST_EN[12] = ENABLE

     return SUCCESSFUL

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
def sps_sts():
     # Send Get DID to ME
     sps_version, platform, dcmi, nm, image  = get_device_id(get_did_target_me)
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
     # Read Test Item from file
     ## Below is inital AC ON/OFF status
     if os.path.isfile(NM_TEST_LIST_WIN) :
          DEBUG('file exist')
          file = open(NM_TEST_FILE_WIN, 'r')
          with open(NM_TEST_FILE_WIN, "r") as ins:
              test_list = []
              for line in ins:
                  test_list.append(line.rstrip('\n'))
          file.close()
          DEBUG(test_list)
     else:
          DEBUG('file not exist, create file')
          file = open(NM_TEST_FILE_WIN, 'w')
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
def run_schedule(test_schedule):
     # Base on system configuation to disable Non-Support test items in test_schedule
     system_config_detect()
     count = 0
     for test_item in test_schedule:
          # Restore to SPS FW to default for next test Item
          sts_restore = facture_default(dfh_command_restore_default)
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
                    sts = NM_009()
                    NM_TEST_STS[test_item] = sts
          elif(test_item == 10):
               print('Start to run NM_010 test....')
               if(NM_TEST_EN[10] == DISABLE):
                    print('NM_010 test will be disabled due to System Not support this feature')
               else:
                    sts = NM_010()
                    NM_TEST_STS[test_item] = sts
          elif(test_item == 11):
               print('Start to run NM_011 test....')
               if(NM_TEST_EN[11] == DISABLE):
                    print('NM_011 test will be disabled due to System Not support this feature')
               else:
                    sts = NM_011()
                    NM_TEST_STS[test_item] = sts
          elif(test_item == 3):
               print('Start to run NM_003 test....')
               sts = NM_003()
               NM_TEST_STS[test_item] = sts
          elif(test_item == 4):
               print('Start to run NM_004 test....')
               sts = NM_004()
               NM_TEST_STS[test_item] = sts
          elif(test_item == 6):
               print('Start to run NM_006 test....')
               sts = NM_006()
               NM_TEST_STS[test_item] = sts
          elif(test_item == 19):
               print('Start to run PECI_004 test....')
               sts = PECI_004()
               NM_TEST_STS[test_item] = sts
          else:
               print('test item not in list .....')
               return ERROR

     return SUCCESSFUL
     
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
               print('Start to run NM_003 test....')
               sts = NM_003()
               NM_TEST_STS[test_item] = sts
          elif(test_item == 4):
               print('Start to run NM_004 test....')
               sts = NM_004()
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
def aardvark_ipmi_init():
    ## Test pyIPMI
    opts, args = getopt.getopt(sys.argv[1:], 't:hvVI:H:U:P:o:b:')
    interface_name = 'aardvark'
    name = 'pullups'
    value = 'off'
    aardvark_pullups = False
    aardvark_serial = None
    aardvark_target_power = False
    target_address = 0x2c
    target_routing = [(0x2c,6)]
    ###
    interface = pyipmi.interfaces.create_interface(interface_name, serial_number=aardvark_serial)
    ipmi = pyipmi.create_connection(interface)
    ipmi.target = pyipmi.Target(target_address)
    ipmi.target.set_routing(target_routing)
    
    return ipmi
    
#Define NM_009 test process in Mehlow Windows
def NM_009_WIN(ipmi):

     # Detect PTU PATH and parameters settings
     PTUGEN_P100_30SECS, PTUMON_3SECS, PTUMON_PATH, PTUGEN_PATH = ptu_parameters_detect()
     # Run load on host system with PTU 100% loading for 30secs
     #os.system(WIN_SSH_PATH + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' ' + PTUMON_3SECS)
     os.system( WIN_BACKGROUND_RUN + WIN_SSH_PATH + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' ' + PTUGEN_P100_30SECS + ' &')
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
     #os.system('ssh ' + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' ' + PTUMON_3SECS)
     os.system( WIN_BACKGROUND_RUN + WIN_SSH_PATH + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' ' + PTUGEN_P100_30SECS + ' &')
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
     # Get ME RTC TIME via 0x48 cmd
     print(NM_006.__name__ + ':Start checking if ME RTC cunter is normal...')
     loop = 0
     temp_time = 0
     for loop in range(0, 10):
         rtc_me = get_sel_time_py(ipmi)
         if(rtc_me == ERROR):
              DEBUG(NM_006.__name__ + ':ERROR!!! Get ME SEL TIME IPMI Resp data error!!!')
              return ERROR
         elif(rtc_me <= temp_time):
              DEBUG(NM_006.__name__ + ':ERROR !!! ME RTC count not move.')
              return ERROR
         # Get RTC data OK
         DEBUG(NM_006.__name__ + ':Get ME RTC OK')
         DEBUG(NM_006.__name__ + ':ME SEL RTC TIME Reading = %12d secs' %rtc_me)
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
     print(NM_006.__name__ + ':Get OS RTC TIME...')
     os.system(WIN_SSH_PATH + os_user + '@'+ os_ip_addr + ' -t sudo ' + OSRTC + ' > ' + OS_RTC_LOG_WIN)
     # Compare OS RTC TIME with ME RTC TIME
     print(NM_006.__name__ + ':Start compare ME RTC and OS RTC time...')
     rtc_os = read_keyword_file(OS_RTC_LOG_WIN, 'RTC' , 14 , 0 , 0)
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
     #os.system(WIN_SSH_PATH + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' ' + PTUMON_3SECS)
     os.system( WIN_BACKGROUND_RUN + WIN_SSH_PATH + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' ' + PTUGEN_P100_30SECS + ' &')
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
         max_p_states = p_states - 1
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
     # Run load on host system with PTU 100% loading for 30secs
     #os.system(WIN_SSH_PATH + os_user + '@'+ os_ip_addr + ' -t sudo ' + PTUMON_PATH + ' ' + PTUMON_3SECS)
     os.system( WIN_BACKGROUND_RUN + WIN_SSH_PATH + os_user + '@' + os_ip_addr +' -t sudo ' + PTUGEN_PATH + ' ' + PTUGEN_P100_30SECS + ' &')
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

	 
def main(argv):
   print 'usage : peci_proxy.py [PECI_CLIENT_ADDR : CPU0 = 0x30 , CPU1=0x31, CPU2= 0x32, CPU3=0x33... ] '
   print '                       [peci_interface : Fallback =0, Inbend PECI = 1, PECI wire = 2] '
   print '                       [write_len : ] '
   print '                       [read_len : ] '
   print '                       [raw_peci : ] '
   print 'example GET_TEMP() : > python peci_proxy.py 0x30 0 1 2 1  '
   print 'example RdPkgConfig(): Package Thermal Status MSR 0x1B1 : > python peci_proxy.py 0x30 0 5 5 0xa1 0 0x14 0 0'

   PECI_CLIENT_ADDR = int(sys.argv[1], 16)
   peci_interface = int(sys.argv[2], 16)
   write_len = int(sys.argv[3], 16)
   read_len = int(sys.argv[4], 16)
   raw_peci = []
   loop = 0
   for loop in range(0 , (len(sys.argv)- 5)):
        raw_peci.append('0x'+ format(int(sys.argv[5+loop], 16),'02x'))
   DEBUG(raw_peci)  
   ipmi = aardvark_ipmi_init()
   # Prepare GetTemp PECI raw data aray
   while (1):
        # Send GetTemp via ME RAW PECI proxy: Write length = 1 byte , Read_Length = 2 bytes
        resp = send_raw_peci_py(ipmi , PECI_CLIENT_ADDR, peci_interface, write_len , read_len , raw_peci )
        time.sleep(0.5)
        
   print('Loop exit ~ Bye!')           
	 
## Below is __Main__
if __name__ == "__main__":
     main(sys.argv[1:])



#ipmi = aardvark_ipmi_init()
#facture_default_py(ipmi, dfh_command_restore_default)
#sts = NM_007_WIN(ipmi)
#sts = sps_sts_py(ipmi)
#sts1 = NM_009_WIN(ipmi)
#sts2 = NM_010_WIN(ipmi)
#sts3 = NM_006_WIN(ipmi)
#sts4 = PECI_004_WIN(ipmi)

#/////////////////////////////////////////////
#pch_tem = get_sensor_reading_py(ipmi, pch_temp)
#get_device_id_py(ipmi)
#max_draw_range, min_draw_range, min_correction_time, max_correction_time = get_platform_power_draw_range_py(ipmi, platform_domain, 0, 1, 0)
#set_nm_power_policy_py(ipmi, c1h_platform_domain, c1h_policy_enable, 3, c1h_no_policy_trigger, c1h_add_policy, c1h_auto_aggressive, c1h_presistent, c1h_alert_enable, c1h_shutdown_disable, AC_power_side, (power_average_stress*4/5), min_correction_time, c1h_trigger_limit_null, c1h_minimum_report_period )
#facture_default_py(ipmi, dfh_command_restore_default)
#///// PMbus Test //////
#bus = d9h_sml1
#target_addr = 0xb0 #PSU0
#get_pmbus_version_py(ipmi , bus , target_addr )
#get_pmbus_read_ein_py(ipmi , bus , target_addr )
#get_pmbus_read_pin_py(ipmi , bus , target_addr )
#get_pmbus_read_pout_py(ipmi , bus , target_addr )

# Config Test List file
#test_schedule = test_schedule()
#sts = run_schedule_py(ipmi, test_schedule)
# Print Test Result

