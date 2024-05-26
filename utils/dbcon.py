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
import psycopg2
from utils.applog import logger

cnxn = None

def connect():
    global cnxn

    if not cnxn:
        dbuser = os.environ.get('DBUSER', 'susit')
        dbpass = os.environ.get('DBPASS')
        dbhost = os.environ.get('DBHOST', 'localhost')
        dbport = os.environ.get('DBPORT', '5432')
        dbname = os.environ.get('DBNAME', 'susit')

        try:
            dbstr = f"postgres://{dbuser}:{dbpass}@{dbhost}:{dbport}/{dbname}"
            cnxn = psycopg2.connect(dbstr)
            logger.info(f"Connected to database {dbname}")
        except (Exception, psycopg2.DatabaseError) as e:
            raise e
    return cnxn

def fetch_assets(customer, hostname):
    """
    Reads device asset information from asset table in customer schema
    Parameters:
        customer: customer name/schema
        hostname: device hostname
    Returns:
        assets: array of assets in the form
            [
                {
                    'hostname': device name
                    'serial': integer, input power in watts
                    'pid': string, product ID
                }
            ]
        Exception on failure
    """
    assets = []
    try:
        connect()
        cursor = cnxn.cursor()
        cursor.execute(
            f"SELECT serial, pid from {customer}.assets WHERE hostname = '{hostname}'")
        results = cursor.fetchall()
        for i in results:
            assets.append(
                dict([('hostname', hostname), ('serial', i[0]), ('pid', i[1])]))
    except (Exception, psycopg2.DatabaseError) as e:
            logger.error(f"{hostname} failed to fetch assets details {e}")
            cnxn.rollback()
    finally:
        cursor.close()
    return assets

def insert_assets(customer, hostname, assets):
    """
    Inserts device asset information to asset table in customer schema
    Parameters:
        customer: customer name/schema to insert to
        hostname: device hostname
        assets: array of assets in the form
            [
                {
                    'hostname': device name
                    'serial': inger, input power in watts
                    'pid': string, product ID
                }
            ]
    Returns:
        None on success
        Exception on failure
    """

    # if matching values already exist, then skip
    existing = fetch_assets(customer, hostname)
    if assets and assets == existing:
        return

    try:
        connect()
        cursor = cnxn.cursor()

        # this table needs to hold only the latest entries
        # in the rare event of new assets getting added, then
        # delete all entries and then insert, rather than selecting updates and deletes
        if existing:
            cursor.execute(
                f"DELETE FROM {customer}.assets WHERE hostname = '{hostname}'")
            
        # insert new values
        values = ','.join(cursor.mogrify('(%s, %s, %s)', (hostname, i['serial'], i['pid'])).decode('utf-8') for i in assets)
        cursor.execute(
            f"INSERT INTO {customer}.assets (hostname, serial, pid) VALUES {values}")
        cnxn.commit()
    except (Exception, psycopg2.DatabaseError) as e:
        logger.error(f"{hostname} failed to insert assets details {e}")
        logger.error(f"{hostname} attempted to insert {assets}")
        cnxn.rollback()
    finally:
        cursor.close()
    return

def insert_psumetrics(customer, hostname, metrics):
    """
    Inserts PSU metrics to psumetrics timeseries table in customer schema
    Parameters:
        customer: customer name/schema to insert to
        hostname: device hostname
        metrics: array of psu metrics in the form
            [
                {
                    'timestamp': timestamp with timezone
                    'hostname': device name
                    'power_in': integer, input power in watts
                    'power_out': integer, output power in watts
                    'power_efficiency': integer, psu efficiency in percentage
                }
            ]
    Returns:
        None on success
        Exception on failure
    """
    try:
        connect()
        cursor = cnxn.cursor()
        values = ','.join(cursor.mogrify(
            '(%s, %s, %s, %s, %s, %s)', (
                i['timestamp'], hostname, i['psuname'],i['power_in'], i['power_out'], i['power_efficiency']
            )).decode('utf-8') for i in metrics)
        cursor.execute(f"INSERT INTO {customer}.psumetrics VALUES {values}")
        cnxn.commit()
    except (Exception, psycopg2.DatabaseError) as e:
        logger.error(f"{hostname} failed to insert psu metrics {e}")
        logger.error(f"{hostname} attempted to insert {metrics}")
        cnxn.rollback()
    finally:
        cursor.close()
    return

def insert_ifmetrics(customer, hostname, metrics):
    """
    Inserts Interface metrics to ifmetrics timeseries table in customer schema
    Parameters:
        customer: customer name/schema to insert to
        hostname: device hostname
        metrics: array of interface metrics in the form
            [
                {
                    'timestamp': timestamp with timezone
                    'hostname': device name
                    'ifname': integer, power input in watts
                    'bandwidth': integer, interface bandwidth in Kbps
                    'traffic_in': integer, total incoming traffic in Kbps
                    'traffic_out': integer, total outgoinf traffic in Kbps
                    'utilization': integer, psu efficiency in percentage
                }
            ]
    Returns:
        None on success
        Exception on failure
    """
    try:
        connect()
        cursor = cnxn.cursor()
        values = ','.join(cursor.mogrify(
            '(%s, %s, %s, %s, %s, %s, %s)', (
                i['timestamp'], hostname, i['ifname'],i['bandwidth'], i['traffic_in'], i['traffic_out'], i['utilization']
            )).decode('utf-8') for i in metrics)
        cursor.execute(f"INSERT INTO {customer}.ifmetrics VALUES {values}")
        cnxn.commit()
    except (Exception, psycopg2.DatabaseError) as e:
        logger.error(f"{hostname} failed to insert interface metrics {e}")
        logger.error(f"{hostname} attempted to insert {metrics}")
        cnxn.rollback()
    finally:
        cursor.close()
    return

def fetch_powermetrics(customer, site, duration):
    """
    Reads power metrics in customer schema
    Parameters:
        customer: customer name/schema
        site: site name
        duration: query duration in number of days
        timezone: timezone of the site
    Returns:
        assets: array of assets in the form, time bucketed into 1hr each
            [
                {
                    'timestamp': timebucket
                    'site': integer, input power in watts
                    'family': string, device family
                    'hostname': string, device hostname
                    'power_in': float, avg power consumed in kWh
                    'power_efficiency': float, avg PSU efficiency
                    'power_utilization': float, avg PSU utilization
                    'traffic_efficiency': float, avg traffic utilization
                    'temperature': max temperature status
                    'cpu': max cpu usage
                    'memory': max memory usage
                    'co2_intensity': float, average co2 intensity
                    'co2_emission': float, average CO2 Emission in gEqCO2/kWh
                }
            ]
        Exception on failure
    """
    metrics = []
    try:
        connect()
        cursor = cnxn.cursor()
        cursor.execute(
            f"""
            SELECT time_bucket_gapfill('1 hour', timestamp) as bucket,
            site,
            family,
            hostname,
            locf(avg(power_in)) as power_in,
            locf(avg(power_efficiency)) as power_efficiency,
            locf(avg(power_utilization)) as power_utilization,
            locf(avg(traffic_efficiency)) as traffic_efficiency,
            max(temperature) as temperature,
            max(cpu_usage) as cpu,
            max(memory_usage) as memory,
            locf(avg(co2_intensity)) as co2_intensity
            FROM {customer}.powermetrics
            WHERE site = '{site}'
            AND timestamp < NOW()
            AND timestamp > NOW() - INTERVAL '{duration} days'
            GROUP BY bucket, site, family, hostname
            ORDER BY hostname, bucket ASC;
            """)
        results = cursor.fetchall()
        for i in results:
            metrics.append(
                dict([
                    ('timestamp', i[0]),
                    ('site', i[1]),
                    ('family', i[2]),
                    ('hostname', i[3]),
                    ('power_in', i[4]/1000 if i[4] else None),
                    ('power_efficiency', i[5]),
                    ('power_utilization', i[6]),
                    ('traffic_efficiency', i[7]/1000 if i[7] else None),
                    ('temperature', i[8]),
                    ('cpu', i[9]),
                    ('memory', i[10]),
                    ('co2_intensity', i[11]),
                    ('co2_emission', (i[4]/1000 * i[11]) if i[4] and i[11] else None)
                ]))
    except (Exception, psycopg2.DatabaseError) as e:
            logger.error(f"{site} failed to fetch power metrics {e}")
            cnxn.rollback()
    finally:
        cursor.close()
    return metrics

def insert_powermetrics(customer, hostname, metrics):
    """
    Inserts power metrics to powermetrics timeseries table in customer schema
    Parameters:
        customer: customer name/schema to insert to
        hostname: device hostname
        metrics: array of interface metrics in the form
            [
                {
                    'timestamp': timestamp with timezone
                    'site': site name
                    'hostname': device name
                    'power_in': integer, power input in watts
                    'power_out': integer, power output in watts
                    'power_efficiency': integer, power output in watts
                    'power_available': integer, total nominal power in watts
                    'power_utilization': integer, total power consumed / total nominal power in percentage
                    'traffic_in': integer, total incoming traffic in Kbs
                    'traffic_out': integer, total outgoinf traffic in Kbs
                    'traffic_efficiency': integer, total power consumed / total traffic in Watts/Gbps
                    'temperature': temperature status -1 unknown, 0 normal, 1 warning, 2 critical
                    'cpu_usage': -1 unknown, 0 - 100% otherwise
                    'memory_usage': -1 unknown, 0 - 100% otherwise
                    'co2_intensity': co2 intensity at the given site at the given time
                }
            ]
    Returns:
        None on success
        Exception on failure
    """
    try:
        connect()
        cursor = cnxn.cursor()
        values = cursor.mogrify('(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', list(metrics.values())).decode('utf-8')
        cursor.execute(f"INSERT INTO {customer}.powermetrics VALUES {values}")
        cnxn.commit()
    except (Exception, psycopg2.DatabaseError) as e:
        logger.error(f"{hostname} failed to insert power metrics {e}")
        logger.error(f"{hostname} attempted to insert {metrics}")
        cnxn.rollback()
    finally:
        cursor.close()
    return

def fetch_psu_specs(hostname, pidlist):
    specs = []

    if not pidlist:
        return []

    try:
        connect()
        cursor = cnxn.cursor()
        cursor.execute(
            f"SELECT pid, nominal_power, available_power, efficiency from common.psu WHERE pid = ANY (%s)", (pidlist,))
        results = cursor.fetchall()
        for i in results:
            specs.append(
                dict([('pid', i[0]), ('nominal_power', i[1]), ('available_power', i[2]), ('efficiency', i[3])]))
    except (Exception, psycopg2.DatabaseError) as e:
            logger.error(f"{hostname} failed to fetch PSU specs {e}")
            cnxn.rollback()
    finally:
        cursor.close()
    return specs

def fetch_module_specs(pids):
    pass

