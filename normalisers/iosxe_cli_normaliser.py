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

import logging
import re
from .model import PoweffModel, Asset, Interface, Sensor
from .normaliser import Normaliser

class Iosxe_Cli_Normaliser(Normaliser):

    def __init__(self, customer):
        super().__init__(customer)

    def get_commands(self):
        return {
            "show-inventory": "show inventory",
            "show-interfaces": "show interfaces",
            "show-ifindex": "show snmp mib ifmib ifindex",
            "show-environment": "show environment",
            "show-processes-cpu": "show processes cpu",
            "show-memory": "show platform software status control-processor brief"
        }
    
    def normalise(self, sites, device_config, command_data):

        current_device = PoweffModel()
        device = device_config['name']
        current_device.set_family(device_config['family'])

        hostname = device

        sitename = device_config['site']

        try:
            logging.info(f"{device} Extracting location data from site {sitename}")
            location = sites[sitename]
            logging.debug(location)
        except:
            logging.error(f"{device} Failed to extract location data")
            return None

        try:
            logging.info(f"{device} Extracting assets")
            asset_data = self._parse_assets(command_data)
            if len(asset_data) == 0:
                raise Exception("Parsing assets returned empty list")
            logging.debug(asset_data)
        except Exception as e:
            logging.error(f"{device} Failed to extract assets. Error Message {e}")
            return None
        
        try:
            logging.info(f"{device} Extracting interfaces")
            interface_data = self._parse_interfaces(command_data)
            if len(interface_data) == 0:
                raise Exception("Parsing interfaces returned empty list")
            logging.debug(interface_data)
        except:
            logging.error(f"{device} Failed to extract interfaces")
            return None
        
        try:
            logging.info(f"{device} Extracting sensors")
            sensor_data = self._parse_sensors(command_data)
            if len(sensor_data) == 0:
                # do not raise exception because main chassis assets and interfaces might be used later on
                logging.warning("Sensor data returned empty list. POWEFF data will still be processed.")
            logging.debug(sensor_data)
        except Exception as e:
            logging.error(f"{device} Failed to extract sensors. Error Message {e}")
            return None

        logging.info(f"{device} Building POWEFF Model")
        for i in asset_data:
            asset = Asset(
                pid = i['pid'],
                hostname = hostname,
                entity = i['entity'],
                description = i['description'],
                serial = i['serial'],
                vid = i['vid'],
                slot = i['slot'],
                lat = location['Latitude'],
                long = location['Longitude'],
                site = sitename,
                customer = self._customer
            )
            current_device.add_asset(asset)

        for i in interface_data:
            interface = Interface(
                ifname = i['name'],
                index = i.get('if-index', ''),
                bandwidth = i['bandwidth'],
                type=i['interface-type'],
                speed = i['speed'],
                data_rate_frequency = i['data_rate_frequency'],
                input_packet_rate = i['input_packet_rate'],
                input_data_rate = i['input_data_rate'],
                output_packet_rate = i['output_packet_rate'],
                output_data_rate = i['output_data_rate']
            )
            current_device.add_interface(interface)
        
        for i in sensor_data:
            sensor = Sensor(
                location = i['location'],
                name = i['name'],
                state = i['state'],
                reading = i['reading'],
                units = i['units']
            )
            current_device.add_sensor(sensor)
        
        try:
            poweff_current = current_device.serialise()
        except Exception as e:
            logging.error(f"{device} Failed to serialize. Error Message {e}")
            return None
        
        self._models.append(poweff_current)

        return self._models

    def _parse_assets(self, command_data):
        try:
            asset_data = self._parse_inventory_textfsm(command_data)
        except:
            asset_data = []

        return asset_data

    def _parse_inventory_textfsm(self, command_data):
        show_inventory = self._tokenize_fsm(command_data['show-inventory'], 'iosxe_show_inventory.fsm')
        logging.debug(show_inventory)

        asset_data = []
        
        for inv in show_inventory:

            params = {'entity': inv['NAME'].strip(),
                      'description': inv['DESCR'].strip(),
                      'pid': inv['PID'].strip(),
                      'serial': inv['SN'].strip(),
                      'vid': inv['VID'].strip(),
                      'slot': 'None'}
            
            if params['serial'].lower() in ("N/A", ""):
                params['serial'] = "NA"
            if params['vid'].lower() in ("N/A", ""):
                params['vid'] = "NA"

            asset_data.append(params)

        asset_data[0]['slot'] = 'Chassis'

        return asset_data

    def _parse_interfaces(self, command_data):
        tokenized_snmp_interface = self._tokenize_fsm(command_data.get('show-ifindex', ""), 'iosxe_show_snmp_mib_ifmib_ifindex.fsm')
        logging.debug(tokenized_snmp_interface)

        interface_data = []
        tokenized = self._tokenize_fsm(command_data.get('show-interfaces', ''), 'iosxe_show_interfaces.fsm')
        logging.debug(tokenized)

        for interface_token in tokenized:
            interface = {}
            name = interface_token["INTERFACE"]
            if not self._is_physical_interface(name):
                logging.debug(f"Interface {name} is a virtual. Skipping.")
                continue
            if "up" not in interface_token["LINK_STATUS"]:
                logging.debug(f"Interface {name} is down. Skipping")
                continue
            interface["name"] = name
            interface["if-index"] = self._match_ifindex(name, tokenized_snmp_interface)
            interface["interface-type"] = interface_token["HARDWARE_TYPE"]
            
            # units already in Kbit, eg "10000000 Kbit"
            bandwidth_match = re.search(r"\d+", interface_token["BANDWIDTH"]) 
            if bandwidth_match:
                interface["bandwidth"] = int(bandwidth_match[0])
            else:
                interface["bandwidth"] = 0
            # sample "10 Gb/s", "auto-speed", 
            duplex_speed_raw = interface_token["SPEED"]
            duplex_speed = duplex_speed_raw
            if re.search(r"\d+\s?\Sb", duplex_speed_raw):
                duplex_speed = int(re.search(r"\d+", duplex_speed_raw)[0])
                if "kb" in duplex_speed_raw.lower():
                    pass
                elif "mb" in duplex_speed_raw.lower():
                    duplex_speed *= 1000
                elif "gb" in duplex_speed_raw.lower():
                    duplex_speed *= 1000000
                else:
                    logging.warn(f"Could not identify Duplex speed units in '{duplex_speed_raw}'. Placing raw extract instead")
                    duplex_speed = duplex_speed_raw
            interface["speed"] = duplex_speed
            
            try:
                bps_to_kbps = 0.001
                interface["input_packet_rate"] = int(interface_token["INPUT_RATE_PPS"]) # Units in packets/s
                interface["input_data_rate"] = int(int(interface_token["INPUT_RATE_BPS"]) * bps_to_kbps) # Units in kpbs
                interface["output_packet_rate"] = int(interface_token["OUTPUT_RATE_PPS"]) # Units in packets/s
                interface["output_data_rate"] = int(int(interface_token["OUTPUT_RATE_BPS"]) * bps_to_kbps) # Units in kpbs

                # sample "30 seconds", "1 minute"
                load_interval_raw = interface_token["LOAD_INTERVAL_INPUT"]
                load_interval_val = int(re.search(r"\d+", load_interval_raw)[0])
                if "minute" in load_interval_raw:
                    load_interval_val *= 60
                interface["data_rate_frequency"] = load_interval_val
            except: #some interfaces such as loopbacks will not have have these data rates
                interface["data_rate_frequency"] = 0
                interface["input_packet_rate"] = 0
                interface["input_data_rate"] = 0
                interface["output_packet_rate"] = 0
                interface["output_data_rate"] = 0

            interface_data.append(interface)

        return interface_data

    def _parse_sensors(self, command_data):
        pass


    def _parse_cpu_textfsm(self, command_data):
        tokenized = self._tokenize_fsm(command_data['show-processes-cpu'], 'iosxe_show_processes_cpu.fsm')
        logging.debug(tokenized)

        if len(tokenized) == 0:
            logging.warning("CPU textfsm returned empty list. Skipping.")
            return []
        elif len(tokenized) > 1:
            logging.error("Unexpected behavior: CPU textfsm returned more than one value. Skipping.")
            return []
        
        try:
            cpu_1min = float(tokenized[0]['CPU_1min'])
            cpu_5min = float(tokenized[0]['CPU_5min'])
        except:
            logging.error("Extracted CPU usages not numerical")
            return []
        
        sensor_cpu_five_min = {
            'location': 'Chassis',
            'reading': cpu_5min,
            'units': 'Percentage',
            'state': 'NA',
            'name': 'CPU-5Min'
        }
        return [sensor_cpu_five_min]

    def _parse_memory_textfsm(self, command_data):
        tokenized = self._tokenize_fsm(command_data['show-memory'], 'iosxe_show_mem.fsm')
        logging.debug(tokenized)

        if len(tokenized) == 0:
            logging.warning("Memory textfsm returned empty list. Skipping.")
            return []
        elif len(tokenized) > 1:
            logging.warning("Unexpected behavior: Memory textfsm returned more than one value. Taking only the first value.")
        try:
            mem_total = int(tokenized[0]['mem_total'])
            mem_used = int(tokenized[0]['mem_used'])
            mem_free = int(tokenized[0]['mem_free'])
        except:
            logging.error("Extracted Memory usages not an integer")
            return []
        
        if abs(mem_free + mem_used - mem_total) > 10:
            logging.error("Extracted Memory usages do not add up correctly")
            return []

        sensor_memory = {
            'location': 'Chassis',
            'reading': round(100*(mem_used/mem_total), 2),
            'units': 'Percentage',
            'state': 'NA',
            'name': 'Memory'
        }
        return [sensor_memory]
    
    def _parse_temperature_textfsm(self, command_data):
        pass

    def _match_ifindex(self, ifname, tokenized):
        for i in tokenized:
            if ifname == i['IFNAME']:
                return i['IFINDEX']
        return ""

    def _is_physical_interface(self, name):
        # TODO other cases, if any
        if re.search(r'ethernet\s?[\d\/]+|gige\s?[\d\/]+|mgmteth', name.lower()):
            return True
        return False