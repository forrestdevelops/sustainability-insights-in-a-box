#!/bin/bash
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


echo "Waiting for Superset admin creation..."
# create Admin user, you can read these values from env or anywhere else possible
superset fab create-admin --username "$ADMIN_USERNAME" --firstname Superset --lastname Admin --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD"

echo "Waiting for Superset upgrade..."
# Upgrading Superset metastore
superset db upgrade

echo "Waiting for Superset init..."
# setup roles and permissions
superset superset init 

echo "Waiting for Superset dashboard loading"

# Wait for Superset server to start
sleep 5

sed -i'' -e "s/REPLACE_USER_NAME/$DBUSER/g; s/REPLACE_USER_PWD/$DBPASS/g; s/REPLACE_DB_PORT/$DBPORT/g; s/REPLACE_DB_NAME/$DBNAME/g" /tmp/default_dashboards/databases/susi.yaml

# Create dashboard zip folder
cd /tmp && zip -r default_dashboards.zip default_dashboards

sleep 10

# Run dashboard import command
superset import-dashboards -p /tmp/default_dashboards.zip -u admin

echo "Waiting for Superset server start..."

# Starting server
/bin/sh -c /usr/bin/run-server.sh
