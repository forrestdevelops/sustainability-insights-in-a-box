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

from confluent_kafka import Producer, Consumer
import json
import os
import logging

_producer = _consumer = None


def produce(topic, key, message):

    global _producer

    if _producer is None:
        kafka_config = {}
        kafka_config['bootstrap.servers'] = os.environ.get('BOOTSTRAP_SERVERS', 'localhost:29092')
        _producer = Producer(kafka_config)

    try:
        _producer.produce(topic, key = key, value = json.dumps(message))
    except Exception as e:
        logging.error(f"Failed to publish to message queue {topic}")
        raise e

    return True

def shutdown():
    if _producer:
        _producer.flush()
    if _consumer:
        _consumer.close()

def consume(topic, group):

    global _consumer

    if _consumer is None:
        props = { 
            'bootstrap.servers' : os.environ.get('BOOTSTRAP_SERVERS', 'localhost:29092'),
            'group.id' : group,
            'enable.partition.eof' : False,
            'enable.auto.commit' : True,
            'auto.commit.interval.ms': 5000
        }
        _consumer = Consumer(props)
        _consumer.subscribe([topic])

    try:
        while True:
            message = _consumer.poll(timeout = 1)
            if message is None:
                continue

            if message.error():
                logging.error(f"error {message.error()}")
                continue
            return message.value().decode('utf-8')
    except Exception as e:
        logging.error(f"Could not fetch from message queue {topic}")
        raise e
