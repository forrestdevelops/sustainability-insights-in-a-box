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

import datetime
import json
import calendar

class PoweffModel:
    """
    Represents POWEFF Specification LMO Type
    """

    def __init__(self):
        self._family = ''
        self._assets = []
        date = datetime.datetime.utcnow()
        self._timestamp = str(calendar.timegm(date.utctimetuple()))

    def __str__(self):
        return(json.dumps(self.serialise()))

    def set_family(self, family):
        """
        Sets device family
        Parameters:
            family: device family i.e. ASR1k, ASR9k etc
        """
        self._family = family

    def add_asset(self, asset):
        """
        Adds assets to the toplevel LMO object
        Parameters:
            asset: POWEFF Asset object to be be added
        """
        self._assets.append(asset)

    def add_interface(self, interface):
        """
        Utility method, adds interface to the first asset in the list
        Parameters:
            interface: POWEFF Interface object to be added
        """
        self._assets[0].add_interface(interface)

    def add_sensor(self, sensor):
        """
        Utility method, adds sensor to the first asset in the list
        Parameters:
            sensor: POWEFF Sensor object to be added
        """
        self._assets[0].add_sensor(sensor)

    def serialise(self):
        """
        Produces JSON representation of the POWEFF model
        recursively calling serialise on the constituent assets
        Returns:
            poweff model in json format
        """
        assets = []
        for asset in self._assets:
            assets.append(asset.serialise())

        poweff = {
            'data': {
                'ietf-lmo:lmos': {
                    'lmo': {
                        'lmo-class': 'ietf-lmo-asset:asset',
                        'timestamp': self._timestamp,
                        'ietf-susi-asset-ext:device_family': self._family,
                        'inst': assets
                    }
                }
            }
        }
        try:
            _ = poweff['data']['ietf-lmo:lmos']['lmo']['inst'][0]['ietf-susi-power-traffic:interfaces']
        except:
            raise Exception("No Interfaces Found")
        try:
            _ = poweff['data']['ietf-lmo:lmos']['lmo']['inst'][0]['ietf-susi-power-environment:sensors']
        except:
            raise Exception("No Sensors Found")
        return poweff

class Asset:
    """
    Represents POWEFF Specification Asset Type
    """

    def __init__(self, **kwargs):

        # set defaults to avoid serialisation errors
        self._interfaces = []
        self._sensors = []
        self._pid = kwargs.get('pid', '')
        self._vid = kwargs.get('vid', '')
        self._hostname = kwargs.get('hostname', '')
        self._entity = kwargs.get('entity', '')
        self._description = kwargs.get('description', '')
        self._serial = kwargs.get('serial', '')
        self._status = kwargs.get('status', 'True')
        self._slot = kwargs.get('slot', '')
        self._lat = kwargs.get('lat', '0.0')
        self._long = kwargs.get('long', '0.0')
        self._site = kwargs.get('site', '')
        self._customer = kwargs.get('customer', '')

    def __str__(self):
        return(json.dumps(self.serialise()))

    def add_interface(self, interface):
        """
        Adds an interface to this asset
        """
        self._interfaces.append(interface)

    def add_sensor(self, sensor):
        """
        Adds a sensor to this asset
        """
        self._sensors.append(sensor)

    def serialise(self):
        """
        Produces JSON representation of the POWEFF asset
        recursively calling serialise on the constituent interfaces and sensors
        Returns:
            poweff model of this asset in json format
        """
        poweff = {
            'id': self._pid,
            'parent': {
                'lmo-class': 'ietf-lmo-assets-inventory:asset',
                'id': self._hostname
            },
            'ietf-lmo-assets-inventory:name': self._hostname,
            'ietf-lmo-assets-inventory:pid': self._pid,
            'ietf-lmo-assets-inventory:description': self._description,
            'ietf-lmo-assets-inventory:serial-number': self._serial,
            'ietf-lmo-assets-inventory:entity-name': self._entity,
            'ietf-lmo-assets-inventory:vid': self._vid,
            'ietf-susi-asset-ext:status': self._status,
            'ietf-susi-asset-ext:slot': self._slot,
            'ietf-susi-asset-ext:site': self._site,
            'ietf-lmo-assets-inventory:uid': self._customer + self._pid + self._serial,
            'ietf-lmo-assets-inventory:install-location': {
                'geolocation': {
                    'latitude': self._lat,
                    'longitude': self._long
                }
            }
        }

        interfaces = []
        for interface in self._interfaces:
            interfaces.append(interface.serialise())
        if len(interfaces) > 0:
            poweff.setdefault('ietf-susi-power-traffic:interfaces',{})
            poweff['ietf-susi-power-traffic:interfaces']['interface'] = interfaces
        sensors = []
        for sensor in self._sensors:
            sensors.append(sensor.serialise())
        if len(sensors) > 0:
            poweff.setdefault('ietf-susi-power-environment:sensors',{})
            poweff['ietf-susi-power-environment:sensors']['sensors'] = sensors

        return poweff

class Interface:
    """
    Represents POWEFF Specification Interface Type
    """

    def __init__(self, **kwargs):

        # set defaults to avoid serialisation errors
        self._name = kwargs.get('ifname')
        self._index = kwargs.get('index', '')
        self._id = kwargs.get('id', '')
        self._type = kwargs.get('type', '')
        self._bandwidth = kwargs.get('bandwidth', 0)
        self._speed = kwargs.get('speed', 0)
        self._input_packet_rate = kwargs.get('input_packet_rate', 0)
        self._input_data_rate = kwargs.get('input_data_rate', 0)
        self._output_packet_rate = kwargs.get('output_packet_rate', 0)
        self._output_data_rate = kwargs.get('output_data_rate', 0)
        self._data_rate_frequency = kwargs.get('data_rate_frequency', 0)
    
    def __str__(self):
        return(json.dumps(self.serialise()))

    def serialise(self):
        """
        Produces JSON representation of the POWEFF interface
        Returns:
            poweff model of this interface in json format
        """
        poweff = {
            'name': self._name,
            'if-index': self._index,
            'interface-type': self._type,
            'bandwidth': self._bandwidth,
            'speed': self._speed,
            'data-rate-frequency': self._data_rate_frequency,
            'statistics': {
                'input-data-rate': self._input_data_rate,
                'input-packet-rate': self._input_packet_rate,
                'output-data-rate': self._output_data_rate,
                'output-packet-rate': self._output_packet_rate
            }
        }
        return poweff

class Sensor:
    """
    Represents POWEFF Specification Sensor Type
    """

    def __init__(self, **kwargs):

        # update from args, else set defaults
        self._location = kwargs.get('location', '')
        self._name = kwargs.get('name', '')
        self._state = kwargs.get('state', '')
        self._reading = float(kwargs.get('reading', '0.0'))
        self._units = kwargs.get('units', '')

    def __str__(self):
        return(json.dumps(self.serialise()))

    def serialise(self):
        """
        Produces JSON representation of the POWEFF sensor
        Returns:
            poweff model of this sensor in json format
        """
        poweff = {
            'sensor-location': self._location,
            'sensor-current-reading': self._reading,
            'sensor-units': self._units,
            'sensor-state': self._state,
            'sensor-name': self._name
        }
        return poweff
