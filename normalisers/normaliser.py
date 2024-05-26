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

class Normaliser:
    '''
    Abstract base class for device type and access protocol specific Normalisers
    Subclasses must implement normalise() method
    '''

    def __init__(self, customer):
        self._models = []
        self._customer = customer
    
    def normalise(self, sites, device_config, command_data):
        pass

    def _tokenize_fsm(self, data, filename):
        import os
        import textfsm

        fsm_file = os.path.join(os.path.dirname(__file__), 'textfsm_templates', filename)
        logging.debug(f"Textfsm file in {fsm_file}")
        with open(fsm_file) as template:
            fsm = textfsm.TextFSM(template)
        try:
            result = fsm.ParseText(data)
            logging.debug(result)
            parsed = [dict(zip(fsm.header,i)) for i in result]
        except Exception as inst:
            logging.error(inst)
            parsed = []
        return parsed
