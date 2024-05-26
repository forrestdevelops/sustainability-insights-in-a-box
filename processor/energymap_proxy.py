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

import json
import os
import requests
import time
from utils.applog import logger

# Caches CO2 data for a location
# dict of (lat, long) and (timestamp, co2intensity)
co2_intensity_cache = {}

def get_co2_intensity(device, lat,long):
  
  # EnergyMap URL and API keys
  energymap = os.environ.get('ENERGYMAP_API', 'https://api.electricitymap.org/')
  api_key = os.environ.get('ENERGYMAP_KEY', '')

  if not api_key:
    logger.info("Energymap API key not given. Skipping")
    return None

  # fetch co2intensity for the given (lat, long), if already exists
  # if the cached value is less than 1hr old, reuse
  record = co2_intensity_cache.get((lat, long))
  if record and time.time() - record[0] < 360:
     logger.debug(f"{device} returning from cache")
     return record[1]
  
  # Else, fetch the co2intensity again
  try:
    response = requests.get(
        url = f'{energymap}/v3/carbon-intensity/latest?lat={lat}&lon={long}&emissionFactorType=direct',
        headers = { "auth-token": api_key },
        verify = True,
        timeout = 15)
    if response.status_code != 200:
        logger.error(f"{device} Failed to fetch co2 emission data {response.text}")
        return None
    else:
        payload = json.loads(response.text)
        logger.debug(f"{device} payload")
        co2_intensity = payload['carbonIntensity']
        # update cache
        co2_intensity_cache[(lat, long)] = (time.time(), co2_intensity)
        return co2_intensity
       
  except Exception as e:
    logger.error(f"{device} Failed to fetch report data {e}")
    return None

