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


import os
import schedule
import sys
import time
import configurator
from utils import messaging
from utils.applog import logger

def main():
    """
    Entrypoint for scheduler app
    Loads configurations from the file
    Schedules collections and runs event loop
    At scheduled event, pushes collection task configuration on messaging bus
    """
    try:
        configurator.initialise()
    except Exception as e:
        logger.critical(f"Failed to initialise application {e}")
        sys.exit(1)
    
    _schedule_collection()

    # Run event loop forever, waking up to run scheduled collections
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt as e:
        logger.info(f"Interrupt received, shutting down...")
        messaging.shutdown()
        sys.exit(0)

def _schedule_collection():
    """
    Schedules device collections
    Parameters:
        None
    Returns:
        None
    """
    devices = configurator.get_config('devices')
    for device_name, device_config in devices.items():
        if device_config['collection']['enabled']:
            schedule.every(device_config['collection']['interval']).minutes.do(_process_task, device_name)
            logger.info(f"{device_name} Collection scheduled at every {device_config['collection']['interval']} minutes")
        else:
            logger.info(f"{device_name} Collection not enabled, skipping")
            continue
    return

def _process_task(task_data):
    """
    Callback function for scheduled jobs
    Parameters:
        None
    Returns:
        None
    """
    task_config = {}
    task_config['customer'] = { 'name': 'metrics'}
    task_config['loglevel'] = configurator.get_config('loglevel')

    # add device name, configuration and connection details
    task_config['device'] = configurator.get_config('devices')[task_data]
    task_config['device']['name'] = task_data
    task_config['connections'] = configurator.get_config('connections')
    task_config['sites'] = configurator.get_config('sites')
    connection_type = task_config['device']['connection']
    topic = f"{connection_type}_schedules"
    # use device hostname as topic key
    key = task_data
    print (task_config)
    logger.info(f"{task_config['device']['name']} Triggering collection")

    # publish payload on either schedules topic or reports topic
    messaging.produce(topic = topic, key = key, message = task_config)
    return

if __name__ == '__main__':
    main()
