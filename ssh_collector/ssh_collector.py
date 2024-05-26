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
from ssh_connection import SSH_Connection
from normalisers import normaliser_factory
from utils import messaging
from utils.applog import logconfig, logger

def main():

    # Messaging topics to consume and publish
    schedules_topic = os.environ.get('SCHEDULES_TOPIC', 'ssh_schedules')
    collections_topic = os.environ.get('COLLECTIONS_TOPIC', 'collections')
    batch_size = int(os.environ.get('BATCH_SIZE', 10))

    # Start with a baseline logger level
    logconfig(level = 'INFO')
    logger.info(f"Waiting for collection requests")

    # Run event loop forever, waking up to receive collection tasks through messaging
    try:
        while True:
            payload = messaging.consume(schedules_topic, 'collector')
            task_config = json.loads(payload)
            customer = task_config['customer']['name']
            sites = task_config['sites']
            device = task_config['device']['name']
            conn_type = task_config['device']['connection']
            loglevel = task_config['loglevel']['console']

            # Reconfigure logformat to include customer name and desired loglevel
            logconfig(customer, loglevel)

            normaliser = normaliser_factory.get_normaliser(task_config)
            commands = normaliser.get_commands()
            logger.debug(commands)

            connection = SSH_Connection(task_config)
            if not connection:
                logger.error(f"{device} Invalid connection configuration, skipping collection")
                continue

            logger.info(f"{device} Trying to connect through {conn_type}")
            if not connection.connect():
                logger.error(f"{device} Failed connecting to device, skipping collection")
                continue
            else:
                logger.info(f"{device} Successfully connected")

            logger.info(f"{device} Executing commands")
            command_data = connection.execute(commands)
            connection.disconnect()
            logger.debug(command_data)

            if not command_data:
                logger.error(f"{device} Error executing commands")
                continue
            else:
                logger.info(f"{device} Normalising data into POWEFF model")
                
            poweff_data = normaliser.normalise(sites, task_config['device'], command_data)
            if not poweff_data:
                logger.error(f"{device} Failed to build POWEFF model, skipping device")
                continue
            else:
                logger.info(f"{device} Successfully built POWEFF model")
                logger.debug(poweff_data)
            
            for poweff_index in range(0, len(poweff_data), batch_size):
                batch_task = task_config.copy()
                batch_poweff = poweff_data[poweff_index:poweff_index + batch_size]
                batch_task['poweff'] = list(filter(None, batch_poweff))
                logger.info(f"{device} sending batch index {poweff_index} of POWEFF data to message queue")
                logger.debug(batch_task)
                messaging.produce(topic = collections_topic, key = device, message = batch_task)
            
    except KeyboardInterrupt as e:
        logger.info(f"Interrupt received, shutting down...")
        messaging.shutdown()
        sys.exit(0)

if __name__ == '__main__':
    main()

