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

FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
}

ENABLE_PROXY_FIX = True
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
  {
      "id": 'standard_color_scheme',
      "description": '',
      "label": 'Standard color scheme',
      "colors":
       ['#fbab18', '#0d274d', '#00bceb', '#6abf4b', '#e2231a', '#eed202', '#00bceb','#495057','#ced4da']
  }]
APP_NAME = "Sustainability Insights Tool (SIT)"
D3_FORMAT = {
  "decimal": ",",
  "thousands": ".",
  "grouping": [3],
  "currency": ["£", ""],
  "dateTime": "%a %e %b %X %Y",
  "date": "%d/%m/%Y",
  "time": "%H:%M:%S",
  "periods": ["AM", "PM"],
  "days": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
  "shortDays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
  "shortMonths": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
}