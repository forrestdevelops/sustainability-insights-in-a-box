# Copyright 2024 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import re
from datetime import datetime
from utils import dbcon
from utils.applog import logger

def process_assets(customer, device, poweff):
    """
    Process assets from Poweff and insert into database
    Parameters:
        customer: customer name
        device: device hostname
        poweff: Referene to "lmo" object in POWEFF payload
    Returns:
        on success: array of assets in the form
            [
                {
                    'hostname': device name
                    'serial': serial key, may include empty ''
                    'pid': string, product ID
                }
            ]
        on error: empty []
    """
    assets = []
    for i in poweff['inst']:
        serial = i["ietf-lmo-assets-inventory:serial-number"].strip()
        pid = i["ietf-lmo-assets-inventory:pid"].strip()

        if pid:
            assets.append(dict([
                ('hostname', device),
                ('serial', serial),
                ('pid', pid)
            ]))

    if assets:
        dbcon.insert_assets(customer, device, assets)

    return assets


def process_interfaces(customer, device, poweff):
    """
    Process interfaces from Poweff and insert into database
    Parameters:
        customer: customer name
        device: device hostname
        poweff: Referene to "lmo" object in POWEFF payload
    Returns:
        on success: array of assets in the form
            [
                {
                    'timestamp': timestamp with timezone
                    'hostname': device name
                    'ifname': integer, power input in watts
                    'bandwidth': integer, interface bandwidth in Kbps
                    'traffic_in': integer, total incoming traffic in Kbps
                    'traffic_out': integer, total outgoinf traffic in Kbps
                    'utilization': integer, psu efficiency in percentage
                }
            ]
        on error: empty []
    """
    # As per POWEFF spec, interfaces are only in first asset
    metrics = []
    for i in poweff['inst'][0]['ietf-susi-power-traffic:interfaces']['interface']:
        # TODO: Below two filters probably moved to Tooling
        # Skip loopback, virtual interfaces etc
        if re.search(r'\.\d+$|^Loopback|^Port-channel|^Vlan|^mgmt|^Po|^Tunnel|^Bundle', i['name'], re.IGNORECASE):
            continue
        # Some old interfaces are reported with 0 bandwith
        if i['bandwidth'] == 0:
            continue

        metrics.append(dict([
            ('timestamp', datetime.fromtimestamp(int(poweff['timestamp']))),
            ('hostname', device),
            ('ifname', i['name']),
            ('bandwidth', i['bandwidth']),
            ('traffic_in', i['statistics']['input-data-rate']),
            ('traffic_out', i['statistics']['output-data-rate']),
            ('utilization', (i['statistics']['input-data-rate'] +
             i['statistics']['output-data-rate']) * 100 / i['bandwidth'])
        ]))

    logger.debug(metrics)
    if metrics:
        dbcon.insert_ifmetrics(customer, device, metrics)

    return metrics


def process_sensors(customer, device, poweff):
    """
    Process sensors from Poweff and insert into database
    Parameters:
        customer: customer name
        device: device hostname
        poweff: Referene to "lmo" object in POWEFF payload
    Returns:
        on success: array of psu and system vital metrics
        PSU metrics as,
            [
                {
                    'timestamp': timestamp with timezone
                    'hostname': device name
                    'power_in': integer, input power in watts
                    'power_out': integer, output power in watts
                    'power_efficiency': integer, psu efficiency in percentage
                }
            ]
        system vitals as,
            {
                'temperature': temperature status -1 unknown, 0 normal, 1 warning, 2 critical
                'cpu_usage': -1 unknown, 0 - 100% otherwise
                'memory_usage': -1 unknown, 0 - 100% otherwise
            }
    """

    # Define temperature levels
    temperatures = {"Unknown": -1, "Normal": 0, "Warning": 1, "Critical": 2}
    # Initialise sensors to defaults
    vitals = {'cpu_usage': -1, 'memory_usage': -1, 'temperature': -1}
    psus = {}

    # Capture values of CPU, Memory and Power sensors
    vitals['temperature'] = -1
    for i in poweff['inst'][0]['ietf-susi-power-environment:sensors']['sensors']:
        if i['sensor-name'] in ['Pin', 'Pout', 'Vin', 'Vout', 'Iin', 'Iout']:
            psus[i['sensor-location']] = psus.get(i['sensor-location'], {})
            psus[i['sensor-location']][i['sensor-name']
                                       ] = i['sensor-current-reading']
        elif i['sensor-name'] == 'CPU-5Min':
            vitals['cpu_usage'] = i['sensor-current-reading']
        elif i['sensor-name'] == 'Memory':
            vitals['memory_usage'] = i['sensor-current-reading']
        # Among the many temperature sensors, capture the highest one
        elif i['sensor-units'] == 'Celsius':
            level = temperatures.get(i['sensor-state'], -1)
            if vitals['temperature'] < level:
                vitals['temperature'] = level
        else:
            # Ignore all other sensors for now
            pass

    # initialise psu metrics
    metrics = []
    for k, v in psus.items():
        d = dict([
                ('timestamp', datetime.fromtimestamp(
                    int(poweff['timestamp']))),
                ('hostname', device),
                ('psuname', k)
        ])

        # Devices like ASR1k report only Voltage and Current
        # Calculate Power as,
        # P = Vrms * Irms (for AC) or V * I (for DC)
        # This device specific behaviour to be moved to Collector?
        if 'Vin' in v and 'Iin' in v:
            v['Pin'] = v['Vin'] * v['Iin']
        if 'Vout' in v and 'Iout' in v:
            v['Pout'] = v['Vout'] * v['Iout']
        logger.debug(v)

        # If both Pin and Pout are available, then all good
        # Else assume 88% efficiency and then calculate the other
        # TODO: read efficiency from PSU specs
        if 'Pin' in v and 'Pout' in v:
            d['power_in'] = v['Pin']
            d['power_out'] = v['Pout']
            d['power_efficiency'] = 0 if (
                v['Pin'] == 0) else int(v['Pout'] * 100/v['Pin'])
        elif 'Pin' in v:
            d['power_in'] = v['Pin']
            d['power_out'] = 0.88 * v['Pin']
            d['power_efficiency'] = 88
        elif 'Pout' in v:
            d['power_out'] = v['Pout']
            d['power_in'] = v['Pout'] / 0.88
            d['power_efficiency'] = 88
        else:
            logger.warning('No power measurements found')
            continue
        metrics.append(d)

    logger.debug(metrics)
    logger.debug(vitals)
    if metrics:
        dbcon.insert_psumetrics(customer, device, metrics)

    return metrics, vitals


def process_psus(device, assets):
    """
    Process reported assets on the device to find PSUs
    Parameters:
        hostname: device hostname
        assets: Assets reported on the device, a list in the format
            [
                {
                    'hostname': device name
                    'serial': serial key, may include empty ''
                    'pid': string, product ID
                }
            ]
    Returns:
        on success: power available as sum nominal output power from all PSUs
        on failure: 0
    """

    '''
    Use below sample assets data to trace the code
    [ {'hostname': '192.37.62.134', 'serial': 'SSI15010A28', 'pid': 'N2K-C2248TP-1GE'}, 
      {'hostname': '192.37.62.134', 'serial': 'SSI142501FV', 'pid': 'N2K-C2248TP-1GE'}, 
      {'hostname': '192.37.62.134', 'serial': 'FDO23491DSD', 'pid': 'N9K-C93180YC-EX'}, 
      {'hostname': '192.37.62.134', 'serial': 'FDO23491DSD', 'pid': 'N9K-C93180YC-EX'}, 
      {'hostname': '192.37.62.134', 'serial': 'DCC234040BE', 'pid': 'NXA-PAC-650W-PE'}, 
      {'hostname': '192.37.62.134', 'serial': 'DCC234040B0', 'pid': 'NXA-PAC-650W-PE'}, 
      {'hostname': '192.37.62.134', 'serial': 'N/A','pid': 'NXA-FAN-30CFM-F'}, 
      {'hostname': '192.37.62.134', 'serial': 'N/A', 'pid': 'NXA-FAN-30CFM-F'}, 
      {'hostname': '192.37.62.134', 'serial': 'N/A', 'pid': 'NXA-FAN-30CFM-F'}, 
      {'hostname': '192.37.62.134', 'serial': 'N/A', 'pid': 'NXA-FAN-30CFM-F'}, 
      {'hostname': '192.37.62.134', 'serial': 'JAF1430AKLK', 'pid': 'N2K-C2248TP-1GE'}, 
      {'hostname': '192.37.62.134', 'serial': 'N/A', 'pid': 'N2K-C2248-FAN'}, 
      {'hostname': '192.37.62.134', 'serial': 'LIT143607RK', 'pid': 'N2200-PAC-400W'}, 
      {'hostname': '192.37.62.134', 'serial': 'LIT143607XP', 'pid': 'N2200-PAC-400W'}, 
      {'hostname': '192.37.62.134', 'serial': 'JAF1505CFHK', 'pid': 'N2K-C2248TP-1GE'}, 
      {'hostname': '192.37.62.134', 'serial': 'N/A', 'pid': 'N2K-C2248-FAN'}, 
      {'hostname': '192.37.62.134', 'serial': 'DTN1832PBFM', 'pid': 'N2200-PAC-400W'}, 
      {'hostname': '192.37.62.134', 'serial': 'LIT142829HC', 'pid': 'N2200-PAC-400W'}
    ]
    '''   
    # Exract all PIDs from the assets 
    pids = [i['pid'] for i in assets]
    '''
    pids = ['N2K-C2248TP-1GE', 'N2K-C2248TP-1GE', 'N9K-C93180YC-EX', 'N9K-C93180YC-EX', 
            'NXA-PAC-650W-PE', 'NXA-PAC-650W-PE', 'NXA-FAN-30CFM-F', 'NXA-FAN-30CFM-F', 
            'NXA-FAN-30CFM-F', 'NXA-FAN-30CFM-F', 'N2K-C2248TP-1GE', 'N2K-C2248-FAN', 
            'N2200-PAC-400W', 'N2200-PAC-400W', 'N2K-C2248TP-1GE', 'N2K-C2248-FAN', 
            'N2200-PAC-400W', 'N2200-PAC-400W']
    '''

    # Lookup power specification for these PIDs in the DB
    psu_specs = dbcon.fetch_psu_specs(device, pids)
    '''
    Of the given PIDs, say only one is in the DB
    [{'pid': 'NXA-PAC-650W-PE', 'nominal_power': 650, 'available_power': 598, 'efficiency': 92}]
    '''
    # Extract available_power from the DB result
    psu_avl = {i['pid']: i['available_power'] for i in psu_specs}
    '''
    psu_avl = {'NXA-PAC-650W-PE': 598}
    '''

    # DB results need further processing, for two cases:
    # 1. While device may have two or more PSUs of the type i.e.PID, 
    #    DB result would only contain one. In the example, device has two "NXA-PAC-650W-PE"
    # 2. Some PSUs may not have been added to the DB at all
    #    device has four N2200-PAC-400W which is not in the DB yet
    power_total = 0
    # loop over device PIDs
    for pid in pids:
        # match with DB result
        power_avl = psu_avl.get(pid, 0)

        # if not found i.e. 2nd case above, use regex to try extracting power rating from the PID itself
        '''
        consider NXA-PAC-650W-PE, N2200-PAC-400W, N77-AC-3KW and  N7K-AC-7.5KW-INT
        '''
        if power_avl == 0:
            match = re.search(r"(\d+\.*\d*)KW", pid)
            if match:
                # Units in KW e.g. N77-AC-3KW and  N7K-AC-7.5KW-INT
                power_avl = int(float(match.group(1)) * 1000)
            else:
                match = re.search(r"(\d+)W", pid)
                if match:
                    # Units in W e.g. NXA-PAC-650W-PE, N2200-PAC-400W
                    power_avl = int(match.group(1))
                else:
                    # No match, may not be PSU PID
                    power_avl = 0
            
            if power_avl != 0:
                logger.warn(f"{device} PSU specs not found for {pid}, assumed Pout {power_avl}W")
   
        # add to available power
        '''
        In this example, 650 + 650 + 400 + 400 + 400 + 400 = 2900
        '''
        power_total += power_avl
    
    logger.debug (power_total)
    return power_total
