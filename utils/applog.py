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

# uses the root logger
logger = logging.getLogger()

def logconfig(customer = 'System', level = 'INFO'):
    """
    Configures the logging format and level
    Parameters:
        customer (string): customer name or defaults to 'System'
        level (string): One of OFF, ERROR, INFO, DEBUG. Defaults to INFO
    Returns:
        logger (logging.Logger) logger instance for the app
    """
    global logger

    # reset logging levels, this works only the first time
    logging.basicConfig(level=logging.NOTSET)

    # fetch handler if already set, else create one
    if len(logger.handlers) == 0:
        console = logging.StreamHandler()
        logger.addHandler(console)
    else:
        console = logger.handlers[0]
    
    format = logging.Formatter(f"%(asctime)s %(levelname)s %(filename)s:%(lineno)s {customer} %(message)s", datefmt='%d-%b-%y %H:%M:%S')
    console.setFormatter(format)

    # Python logger does not have OFF level.
    # If the user intends to turns off logging altogether,
    # then set the log threshold to +1 more than the highest loglevel
    # Else set the desired log level
    if 'OFF' == level:
        log_level = logging.CRITICAL + 1
    else:
        log_level = logging.getLevelName(level)
    console.setLevel(log_level)

    return logger
