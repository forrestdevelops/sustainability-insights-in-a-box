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

class Cat9300_Cli_Normaliser(Iosxe_Cli_Normaliser):

    def __init__(self, customer):
        super().__init__(customer)

    def get_commands(self):
        return {
            "show-inventory": "show inventory",
            "show-interfaces": "show interfaces",
            "show-ifindex": "show snmp mib ifmib ifindex",
            "show-environment": "show environment all",
            "show-processes-cpu": "show processes cpu",
            "show-memory": "show platform software status control-processor brief"
        }

    def normalise(self, sites, device_config, command_data):
        return super().normalise(sites, device_config, command_data)

    def _parse_assets(self, command_data):
        return super()._parse_assets(command_data)

    def _parse_interfaces(self, command_data):
        return super()._parse_interfaces(command_data)

    def _parse_sensors(self, command_data):
        sensor_data = []
        sensor_data.extend(self._parse_power_cat9k(command_data))
        sensor_data.extend(self._parse_cpu_textfsm(command_data))
        sensor_data.extend(self._parse_memory_textfsm(command_data))
        sensor_data.extend(self._parse_temperature_textfsm(command_data))
        return sensor_data

    def _parse_power_cat9k(self, command_data):
        sensor_data = []

        show_environment = self._tokenize_fsm(command_data.get('show-environment', ''),
                                                       'catalyst9k_show_env_all.fsm')
        logging.debug(show_environment)

        chassis_total_power_out = 0
        chassis_total_power_in = 0

        for sensor in show_environment:
            try:
                sensor_reading = float(sensor['READING'])
            except:
                logging.error(f"Sensor reading {sensor['READING']} is not numerical")
            
            sensor_location = sensor['NAME']

            if 'mw' in sensor['UNITS'].lower():
                sensor_reading /= 1000
                sensor_units = 'W'
            elif sensor['UNITS'].lower() in ('w', 'watt', 'watts'):
                sensor_units = 'W'
            else:
                logging.debug(f"Skipping sensor {sensor}. Units not in Watts or mW")
                continue

            if 'powin' in sensor['SENSOR'].lower():
                sensor_name = 'Pin'
                chassis_total_power_in += sensor_reading
            elif 'powout' in sensor['SENSOR'].lower():
                sensor_name = 'Pout'
                chassis_total_power_out += sensor_reading
            else:
                logging.debug(f"Skipping sensor {sensor}. Is not POWin or POWout or Power")
                continue

            sensor = {
                'location': sensor_location,
                'name': sensor_name,
                'state': sensor['STATE'],
                'reading': sensor_reading,
                'units': sensor_units
            }

        if int(chassis_total_power_out) != 0:
            sensor_chassis_pout = {
                    'location': 'Chassis',
                    'reading': chassis_total_power_out,
                    'units': 'W',
                    'state': 'NA',
                    'name': 'Pout'
                    }
            sensor_data.append(sensor_chassis_pout)
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
            sensor_data.append(sensor_chassis_pin)
        else:
            logging.debug("Chassis Pin is 0. Skipping sensor data.")

        return sensor_data

    def _parse_temperature_textfsm(self, command_data):
        logging.info("Parsring Temperature")

        sensor_data = []

        show_environment = self._tokenize_fsm(command_data.get('show-environment', ''),
                                                       'catalyst9k_show_env_all.fsm')
        logging.debug(show_environment)


        for sensor in show_environment:
            try:
                sensor_reading = float(sensor['READING'])
            except:
                logging.error(f"Sensor reading {sensor['READING']} is not numerical")
                continue

            sensor_location = sensor['SENSOR']
            if 'inlet' not in sensor_location.lower():
                logging.debug(f"Skipping sensor {sensor}. Is not inlet")
                continue
            sensor_state = sensor['STATE']
            if sensor_state.lower().strip() in ("normal", "good", "green"):
                sensor_state = "Normal"
            elif sensor_state.lower().strip() in ("yellow"):
                sensor_state = "Warning"
            elif sensor_state.lower().strip() in ("red"):
                sensor_state = "Critical"
            else:
                logging.warning(f"Unable to identify Inlet temperature sensor state is '{sensor_state}'")
                sensor_state = sensor['STATE']


            if 'celsius' in sensor['UNITS'].lower():
                sensor_units = 'Celsius'
            else:
                logging.warning(f"Unable to identify temperature unit '{sensor['UNITS']}")
                sensor_units = sensor['UNITS']

            sensor_temperature = {
                'location': sensor['SENSOR'],
                'reading': sensor_reading,
                'units': sensor_units,
                'state': sensor_state,
                'name': 'Temp'
            }

        sensor_data.append(sensor_temperature)

        return sensor_data