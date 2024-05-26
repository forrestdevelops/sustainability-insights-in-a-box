#!/bin/sh
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


###
# DB Initialization script for SUSI Tooling
# Requires 
#

quit() {
    code=$1
    shift
    echo $*
    exit $code
}

[ -n "${DBUSER}" ] || quit 1 "DBUSER env not set" 
[ -n "${DBPASS}" ] || quit 1 "DBPASS env not set" 
[ -n "${DBNAME}" ] || quit 1 "DBNAME env not set" 
[ -n "${SCHEMA}" ] || quit 1 "SCHEMA env not set" 

psql -U postgres \
-c "CREATE DATABASE ${DBNAME};" \
-c "CREATE USER ${DBUSER} WITH PASSWORD '${DBPASS}'; \
    GRANT ALL PRIVILEGES ON DATABASE ${DBNAME} TO ${DBUSER}; \
"
 
PGPASSWORD=${DBPASS} psql -U ${DBUSER} -d ${DBNAME} -c "\
CREATE SCHEMA ${SCHEMA}; \
CREATE TABLE ${SCHEMA}.assets (  \
hostname TEXT NOT NULL,  \
serial TEXT NOT NULL,  \
pid TEXT NOT NULL  \
);  \
CREATE TABLE ${SCHEMA}.powermetrics (  \
timestamp TIMESTAMPTZ NOT NULL,  \
site TEXT NOT NULL,  \
hostname TEXT NOT NULL,  \
family TEXT NOT NULL, \
power_in INTEGER,  \
power_out INTEGER,  \
power_efficiency INTEGER,  \
power_available INTEGER,  \
power_utilization INTEGER,  \
traffic_in INTEGER,  \
traffic_out INTEGER,  \
traffic_efficiency INTEGER,  \
temperature INTEGER,  \
cpu_usage  INTEGER,  \
memory_usage INTEGER,  \
co2_intensity INTEGER  \
);  \
CREATE TABLE ${SCHEMA}.psumetrics (  \
timestamp TIMESTAMPTZ NOT NULL,  \
hostname TEXT NOT NULL,  \
psuname TEXT,  \
power_in INTEGER,  \
power_out INTEGER,  \
power_efficiency INTEGER  \
);  \
CREATE TABLE ${SCHEMA}.ifmetrics (  \
timestamp TIMESTAMPTZ NOT NULL,  \
hostname TEXT NOT NULL,  \
ifname TEXT NOT NULL,  \
bandwidth INTEGER,  \
data_in INTEGER,  \
data_out INTEGER,  \
utilization INTEGER,  \
power INTEGER  \
);  \
create view ${SCHEMA}.vw_site_week_timebucket as SELECT time_bucket_gapfill('1 hour', timestamp) as bucket,site, family, hostname, locf(avg(power_in)) as power_in, locf(avg(power_efficiency)) as power_efficiency, locf(avg(power_utilization)) as power_utilization, locf(avg(traffic_efficiency)) as traffic_efficiency, max(temperature) as temperature, max(cpu_usage) as cpu, max(memory_usage) as memory, locf(avg(co2_intensity)) as co2_intensity FROM ${SCHEMA}.powermetrics WHERE timestamp < NOW() AND timestamp > NOW() - INTERVAL '30 days' GROUP BY bucket, site, family, hostname ORDER BY hostname, bucket ASC; \
SELECT create_hypertable('${SCHEMA}.powermetrics', 'timestamp');  \
SELECT create_hypertable('${SCHEMA}.psumetrics', 'timestamp');  \
SELECT create_hypertable('${SCHEMA}.ifmetrics', 'timestamp');  \
"