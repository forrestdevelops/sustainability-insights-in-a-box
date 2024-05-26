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

from .asr1k_cli_normaliser import Asr1k_Cli_Normaliser
from .cat9300_cli_normaliser import Cat9300_Cli_Normaliser

def get_normaliser(task_config):

    """
    Given device os and connection protocol, returns instance of suitable Normaliser 
    Parameters:
        task_config: collection task config dict including os_type and connection
    Returns:
        Instance of suitable Normaliser class
    """

    conn_type = task_config['device'].get('connection')
    family = task_config['device'].get('family')
    customer = task_config['customer']['name']
    
    if (conn_type in ('ssh', 'cspc', 'radkit')):
        if family == 'ASR1k' :
            return Asr1k_Cli_Normaliser(customer)
        elif family == 'Cat9300':
            return Cat9300_Cli_Normaliser(customer)
        else:
            None
    else:
        # Should never reach this line
        # Supported combinations must be validated in Inventory Yaml
        None
