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
import jsonschema
import ruamel.yaml
from utils import secrets
from utils.applog import logconfig, logger
from dateutil import tz

# Application configuration dict loaded from './config.yaml'
_config = {}

def initialise():
    """
    Loads and validates configuration and validates agaisnt schema
    Encrypts secrets like device password on first load
    Schema file location is fixed to ./schema.json
    Config file location is fixed to ./config.yaml
    Parameters:
        None
    Returns:
        None, use get_config to fetch configuration properties
    """
    global _config

    # Start with a baseline logger level
    logconfig()

    # Load schema, config from files, and validate
    # These can throw exceptions that are propapated up
    schema = _load_schema('schema.json')
    _config = _load_config('config.yaml')
    _validate_config(schema, _config)

    # Now reconfigure logger to user desired level for rest of the application logger
    logconfig(customer = 'metrics', level = _config['loglevel'].get('console'))

    # Flag to indicate, whether config file needs to be updated
    changed = False

    # Encrypt device credentials, if not done already
    # If password does not exist (as in cspc/mimir/radkit connection) skip
    # If password exists, but key does not exist, then encrypt
    for d in _config['devices'].keys():
        device_config = _config['devices'][d]
        password = device_config.get('password')
        key = device_config.get('key')
        if password is None:
            continue
        elif key is None:
            device_config['password'], device_config['key'] = secrets.encrypt(
                password)
            changed = True

    # Update config file, if passwords got updated
    if changed:
        logger.info(f"Updating application configuration")
        _update_config('config.yaml', _config)
    else:
        logger.info(f"Loaded application configurations")

def _load_schema(schema_json):
    """
    Loads json schema describing the application configuration
    Subsequent code can assume successful validation
    Parameters:
        schema_json (string): schema file path, normally ./schema.json
    Returns:
        schema (dict): loaded json schema dict
        Raises an exception on failure
    """
    try:
        with open(schema_json, 'r') as f:
            schema = json.loads(f.read())
    except Exception as e:
        logger.critical(f"Failed to load configuration schema {e}")
        raise e
    return schema

def _load_config(config_yaml):
    """
    Loads application configuration file in YAML format
    Parameters:
        config_yaml (string): config file path, normally ./config.yaml
    Returns:
        config (dict): app configuration, yet to be validated
        Raises an exception on failure
    """
    try:
        with open(config_yaml, 'r') as f:
            yaml = ruamel.yaml.YAML()
            config = yaml.load(f)
    except Exception as e:
        logger.critical(f"Failed to load configuration file {e}")
        raise e
    return config

def _validate_config(schema, config):
    """
    Validates configuration against schema to ensure mandatory properties are present and in correct format
    Parameters:
        schema (dict): json schema
        config (dict): app configuration to be validated
    Returns:
        True on success
        Raises an exception on failure
    """
    validator = jsonschema.Draft7Validator(schema, format_checker = jsonschema.FormatChecker())
    try:
        validator.validate(config, schema)
    except Exception as e:
        logger.error(f"Validation failed for configuration file: {e}")
        raise e
    for sitename, value in config['sites'].items():
        if not tz.gettz(value['Timezone']):
            raise Exception(f"Invalid Timezone '{value['Timezone']}' for site '{sitename}'")

    return True

def _update_config(config_yaml, config):
    """
    Updates application configuration with latest contents of config dict
    This is called to write updated password
    Parameters:
        config_yaml (string): Config file path, normally ./config.yaml
        config (dict): Application configuration to write
    Returns:
        True on success
        Raises an exception on failure
    """
    try:
        with open(config_yaml, 'w') as f:
            yaml = ruamel.yaml.YAML()
            yaml.dump(config, f)
    except Exception as e:
        logger.error(f"Failed to update configuration file {e}")
        raise e
    return True


def get_config(section):
    """
    Returns a named section in the configuration
    Parameters:
        section (string): Top level config section name 'customer', 'report', 'devices' etc
    Returns:
        Returns copy of named section configuration
        None if invalid section name
    """
    section_config = _config.get(section)
    if section_config:
        return section_config.copy()
    else:
        return None
