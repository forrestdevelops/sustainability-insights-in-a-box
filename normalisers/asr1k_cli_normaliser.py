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
from .iosxe_cli_normaliser import Iosxe_Cli_Normaliser

class Asr1k_Cli_Normaliser(Iosxe_Cli_Normaliser):

    def __init__(self, customer):
        super().__init__(customer)

    def get_commands(self):
        return super().get_commands()
    
    def normalise(self, sites, device_config, command_data):
        return super().normalise(sites, device_config, command_data)
    
    def _parse_assets(self, command_data):
        return super()._parse_assets(command_data)
    
    def _parse_interfaces(self, command_data):
        return super()._parse_interfaces(command_data)
    
    def _parse_sensors(self, command_data):
        sensor_data = []
        sensor_data.extend(self._parse_power_textfsm(command_data))
        sensor_data.extend(self._parse_cpu_textfsm(command_data))
        sensor_data.extend(self._parse_memory_textfsm(command_data))
        return sensor_data

    def _parse_power_textfsm(self, command_data):
        tokenized = self._tokenize_fsm(command_data['show-environment'], 'asr1k_show_environment.fsm')
        sensor_data = []
        vout_dict = {}
        vin_dict = {}
        iout_dict = {}
        iin_dict = {}
        for sensor in tokenized:
            try:
                sensor_reading = float(sensor['READING'])
            except:
                logging.debug(f"Error extracted sensor reading {sensor['READING']} is not a number")
                continue

            sensor_location = sensor['SLOT']

            if 'vout' in sensor['SENSOR'].lower():
                sensor_name = 'Vout'
                sensor_units = 'V'
                vout_dict[sensor_location] = sensor_reading
            elif 'vin' in sensor['SENSOR'].lower():
                sensor_name = 'Vin'
                sensor_units = 'V'
                vin_dict[sensor_location] = sensor_reading
            elif 'iout' in sensor['SENSOR'].lower():
                sensor_name = 'Iout'
                sensor_units = 'A'
                iout_dict[sensor_location] = sensor_reading
            elif 'iin' in sensor['SENSOR'].lower():
                sensor_name = 'Iin'
                sensor_units = 'A'
                iin_dict[sensor_location] = sensor_reading
            else:
                sensor_name = sensor['SENSOR']
                sensor_units = sensor['UNITS']
                # Only add non-power sensors as there will already be the chassis level power
                sensor_i = {
                        'name': sensor_name,
                        'state': sensor['STATE'],
                        'reading': sensor_reading,
                        'units': sensor_units,
                        'location': sensor_location
                    }
                sensor_data.append(sensor_i)

        logging.debug(sensor_data)
        power_sensors = self._generate_chassis_power_from_vi(vout_dict, vin_dict, iout_dict, iin_dict)
        sensor_data.extend(power_sensors)
        logging.debug(sensor_data)

        return sensor_data
    
    def _parse_cpu_textfsm(self, command_data):
        return super()._parse_cpu_textfsm(command_data)
    
    def _parse_memory_textfsm(self, command_data):
        return super()._parse_memory_textfsm(command_data)
    
    def _generate_chassis_power_from_vi(self, vout_dict, vin_dict, iout_dict, iin_dict):
        chassis_total_power_out = 0
        chassis_total_power_in = 0
        power_sensors = []
        while len(iout_dict) != 0:
            sensor_location = list(iout_dict.keys())[0]
            vout_reading = vout_dict.pop(sensor_location, 0)
            iout_reading = iout_dict.pop(sensor_location, 0)
            if vout_reading == 0:
                logging.warning(f"Vout at power slot {sensor_location} is 0.")
            if iout_reading == 0:
                logging.warning(f"Iout at power slot {sensor_location} is 0.")
            chassis_total_power_out += vout_reading * iout_reading

        while len(iin_dict) != 0:
            sensor_location = list(iin_dict.keys())[0]
            vin_reading = vin_dict.pop(sensor_location, 0)
            iin_reading = iin_dict.pop(sensor_location, 0)
            if vin_reading == 0:
                logging.warning(f"Vin at power slot {sensor_location} is 0.")
            if iin_reading == 0:
                logging.warning(f"Iin at power slot {sensor_location} is 0.")
            chassis_total_power_in += vin_reading * iin_reading

        if vout_dict:
            logging.warning(f"Vout locations {list(vout_dict.keys())} have no corresponding Iout")
        if vin_dict:
            logging.warning(f"Vin locations {list(vin_dict.keys())} have no corresponding Iin")

        if int(chassis_total_power_out) != 0:
            sensor_chassis_pout = {
                    'location': 'Chassis',
                    'reading': chassis_total_power_out,
                    'units': 'W',
                    'state': 'NA',
                    'name': 'Pout'
                    }
            power_sensors.append(sensor_chassis_pout)
        else:
            logging.debug("Chassis Pout is 0. Skipping sensor data.")

        if int(chassis_total_power_in) != 0:
            sensor_chassis_pin = {
                    'location': 'Chassis',
                    'reading': chassis_total_power_in,
                    'units': 'W',
                    'state': 'NA',
                    'name': 'Pin'
                    }
            power_sensors.append(sensor_chassis_pin)
        else:
            logging.debug("Chassis Pin is 0. Skipping sensor data.")

        logging.debug(power_sensors)

        return power_sensors
        