import os
import re
import datetime
import os.path
import time
import math
import numpy
from os_parameters_define import *
from utility_function import *
from nm_ipmi_raw_to_str import *
from error_messages_define import *

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


## Function : NM_009 Test Process: Verify that power limiting is working correctly in platform power domain.
def NM_009(os_ip_addr, bmc_ip_addr, user, password ):
     # Run load on host system with PTU 100% loading for 20secs
     os.system('ssh howard@'+ os_ip_addr +' -t sudo /home/howard/PTU/PURLEY/ptumon -t 3')
     os.system('nohup ssh howard@'+ os_ip_addr+' -t sudo /home/howard/PTU/PURLEY/ptugen -p 100 -t 30 &')
     time.sleep(5)
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


## Below is __Main__
sts = NM_009(os_ip_addr, bmc_ip_addr, user, password)
if(sts == SUCCESSFUL):
     print('NM_009 Platform Power Limit Test: Pass')
else:
     print('NM_009 Platform Power Limit Test: Fail !!!')
     print('Please enable debug mode for more detail test information')

