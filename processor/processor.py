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
import sys
from datetime import datetime
import energymap_proxy
import poweff_helper as helper
from utils import messaging, dbcon
from utils.applog import logconfig, logger

def main():

    # Start with a baseline logger level
    logconfig(level='INFO')
    collections_topic = os.environ.get('COLLECTIONS_TOPIC', 'collections')

    # Connect to DB
    try:
        dbcon.connect()
    except Exception as e:
        logger.critical(f"Failed connecting to database {e}")
        sys.exit(1)

    logger.info(f"Waiting for POWEFF metric payloads")

    # Run event loop forever, waking up to receive POWEFF tasks through messaging
    try:
        while True:
            payload = messaging.consume(collections_topic, 'processor')
            task_config = json.loads(payload)
            customer = task_config['customer']['name']
            device = task_config['device']['name']
            loglevel = task_config['loglevel']['console']

            # Reconfigure logformat to include customer name and desired loglevel
            logconfig(customer, loglevel)

            # Locate root level in each POWEFF entry and start processing
            # Collector *always* pushes valid payload as per POWEFF schema
            # So this json key traversal is safe enough
            # But values are filled at runtime and need to validated
            for poweff in task_config['poweff']:

                root = poweff["data"]["ietf-lmo:lmos"]["lmo"]
                site = root['inst'][0]["ietf-susi-asset-ext:site"]
                device = root['inst'][0]['ietf-lmo-assets-inventory:name']
                family = root['ietf-susi-asset-ext:device_family']

                # Process assets, interfaces and sensors from POWEFF
                logger.info(f"{device} processing energy metrics")
                assets = helper.process_assets(customer, device, root)
                ifaces = helper.process_interfaces(customer, device, root)
                powers, vitals = helper.process_sensors(customer, device, root)

                # Initialise all metrics with default values
                metrics = {
                    'timestamp': datetime.fromtimestamp(int(root['timestamp'])),
                    'site': site,
                    'hostname': device,
                    'family': family,
                    'power_in': 0,
                    'power_out': 0,
                    'power_efficiency': 0,
                    'power_available': 0,
                    'power_utilization': 0,
                    'traffic_in': 0,
                    'traffic_out': 0,
                    'traffic_efficiency': 0,
                    'temperature': vitals.get('temperature', -1),
                    'cpu_usage': vitals.get('cpu_usage', -1),
                    'memory_usage': vitals.get('memory_usage', -1),
                    'co2_intensity': 0
                }

                # Fill in power metrics
                for i in powers:
                    metrics['power_in'] += i['power_in']
                    metrics['power_out'] += i['power_out']
                metrics['power_efficiency'] = 0 if (metrics['power_in'] == 0) else int(
                    metrics['power_out'] * 100/metrics['power_in'])
                metrics['power_available'] = helper.process_psus(device, assets)

                metrics['power_utilization'] = 0 if (metrics['power_available'] == 0) else int(
                    metrics['power_in'] * 100/metrics['power_available'])

                # Fill in traffic data
                for i in ifaces:
                    metrics['traffic_in'] += i['traffic_in']
                    metrics['traffic_out'] += i['traffic_out']
                # Traffic in and out are in Kbps, Total traffic in Gbps
                total_traffic = (
                    metrics['traffic_in'] + metrics['traffic_out'])/1000000
                metrics['traffic_efficiency'] = 0 if (
                    total_traffic == 0) else int(metrics['power_in']/total_traffic)
                lat = root['inst'][0]['ietf-lmo-assets-inventory:install-location']['geolocation']['latitude']
                long = root['inst'][0]['ietf-lmo-assets-inventory:install-location']['geolocation']['longitude']
                co2_intensity = energymap_proxy.get_co2_intensity(device, lat, long)
                if co2_intensity:
                    metrics['co2_intensity'] = co2_intensity
                elif 'avg_co2_intensity' in task_config['sites'][site]:
                    metrics['co2_intensity'] = int(task_config['sites'][site]['avg_co2_intensity'])
                    logger.info(f'{device} Using default CO2 intensity from config file instead')
                else:
                    logger.warning(f'{device} No default CO2 intensity on site {site} of config file. CO2 intensity will be set to 0.')

                # Write record to DB
                logger.debug(metrics)
                dbcon.insert_powermetrics(customer, device, metrics)

            logger.info(f"{device} completed energy and sustainability calculations")

    except KeyboardInterrupt as e:
        logger.info(f"Interrupt received, shutting down...")
        messaging.shutdown()
        sys.exit(0)

if __name__ == '__main__':
    main()
