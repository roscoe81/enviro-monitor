#!/usr/bin/env python3
#Northcliff Environment Monitor Adafruit IO Feed Setup 7.13-Gen Max, Min and Mean Noise
import requests
import json


# The aio_feed_prefix dictionary sets up the feed name and key prefixes, as well as the dashboard visibility setting. Customise the dictionary based on the names and keys for each household to be monitored,
# and the names and keys of the Enviro Monitors at each property (can be one Indoor unit or one Outdoor unit or a pairing of an Indoor and an Outdoor unit).
# aio_package choices are either "Premium Plus Noise", "Premium Plus", "Premium Noise", "Premium", "Basic Air" or "Basic Combo". All of this data needs to match the setup for each Enviro Monitor's config.json file (i.e. "aio_household_prefix", "aio_location_prefix" and "aio_package")
# Also enter your Adafruit IO User Name and Key
#Enter your data between the #### lines
#####################################################################################################################################################################################################################
aio_feed_prefix = {'Household 1 Name': {'key': 'household1key', 'package': '<aio_package>', 'locations': {'<Location1Name>': '<location1key', '<Location2Name>': '<location2key'}, 'visibility': '<"public" or "private">'},
                   'Household 2 Name': {'key': 'household2key', 'package': '<aio_package>', 'locations': {'<Location1Name>': '<location1key>'}, 'visibility': '<"public" or "private">'}}
aio_user_name = "<Your Adafruit IO User Name>"
aio_key = "<Your Adafruit IO Key>"
#####################################################################################################################################################################################################################


# These dictionaries set up the feed name and key suffixes to support the Enviro readings. Don't change these dictionaries.
enviro_aio_premium_feeds = {"Temperature": "temperature", "Humidity": "humidity", "Barometer": "barometer", "Lux": "lux", "PM1": "pm1", "PM2.5": "pm2-dot-5",
                    "PM10": "pm10", "Reducing": "reducing", "Oxidising": "oxidising", "Ammonia": "ammonia", "Air Quality Level": "air-quality-level", "Air Quality Text": "air-quality-text",
                    "Weather Forecast Text": "weather-forecast", "Weather Forecast Icon": "weather-forecast-icon", "Version": "version"}
enviro_aio_premium_noise_feeds = {"Temperature": "temperature", "Humidity": "humidity", "Barometer": "barometer", "Lux": "lux", "PM1": "pm1", "PM2.5": "pm2-dot-5",
                    "PM10": "pm10", "Reducing": "reducing", "Oxidising": "oxidising", "Ammonia": "ammonia", "Max Noise": "max-noise", "Min Noise": "min-noise", "Mean Noise": "mean-noise",
                                  "Air Quality Level": "air-quality-level", "Air Quality Text": "air-quality-text",
                    "Weather Forecast Text": "weather-forecast", "Weather Forecast Icon": "weather-forecast-icon", "Version": "version"}
enviro_aio_premium_plus_feeds = {"Temperature": "temperature", "Humidity": "humidity", "Barometer": "barometer", "Lux": "lux", "PM1": "pm1", "PM2.5": "pm2-dot-5",
                    "PM10": "pm10", "Carbon Dioxide": "carbon-dioxide", "TVOC": "tvoc", "Reducing": "reducing", "Oxidising": "oxidising", "Ammonia": "ammonia",
                                 "Air Quality Level": "air-quality-level", "Air Quality Text": "air-quality-text", "Weather Forecast Text": "weather-forecast",
                                 "Weather Forecast Icon": "weather-forecast-icon", "Version": "version"}
enviro_aio_premium_plus_noise_feeds = {"Temperature": "temperature", "Humidity": "humidity", "Barometer": "barometer", "Lux": "lux", "PM1": "pm1", "PM2.5": "pm2-dot-5",
                    "PM10": "pm10", "Carbon Dioxide": "carbon-dioxide", "TVOC": "tvoc", "Reducing": "reducing", "Oxidising": "oxidising", "Ammonia": "ammonia",
                                       "Max Noise": "max-noise", "Min Noise": "min-noise", "Mean Noise": "mean-noise", "Air Quality Level": "air-quality-level",
                                       "Air Quality Text": "air-quality-text", "Weather Forecast Text": "weather-forecast", "Weather Forecast Icon": "weather-forecast-icon", "Version": "version"}
enviro_aio_basic_air_feeds = {"PM1": "pm1", "PM2.5": "pm2-dot-5", "PM10": "pm10", "Air Quality Level": "air-quality-level", "Air Quality Text": "air-quality-text"}
enviro_aio_basic_combo_feeds = {"Temperature": "temperature", "Humidity": "humidity", "Barometer": "barometer", "Air Quality Level": "air-quality-level", "Weather Forecast Icon": "weather-forecast-icon"}
enviro_aio_feeds_map = {'Premium Plus': enviro_aio_premium_plus_feeds, 'Premium Plus Noise': enviro_aio_premium_plus_noise_feeds,'Premium': enviro_aio_premium_feeds, 'Premium Noise': enviro_aio_premium_noise_feeds,
                        'Basic Air': enviro_aio_basic_air_feeds, 'Basic Combo': enviro_aio_basic_combo_feeds}
enviro_aio_premium_blocks = [{"name": "Temperature Gauge", "key": "temperature-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "thermometer", "label": "\u00b0 C", "minValue": "0", "maxValue": "40",
                                                                                                                                                 "ringWidth": "25", "minWarning": "5", "maxWarning": "35", "decimalPlaces": "1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                             {"name": "Humidity Gauge", "key": "humidity-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:humidity", "label": "%", "minValue": "0", "maxValue": "100",
                                                                                                                                                 "ringWidth": "25", "minWarning": "30", "maxWarning": "80", "decimalPlaces": "0"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                             {"name": "Air Pressure Gauge", "key": "air-pressure-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:barometer", "label": "hPa", "minValue": "980", "maxValue": "1040",
                                                                                                                                                 "ringWidth": "25", "minWarning": "990", "maxWarning": "1030", "decimalPlaces": "1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]},
                             {"name": "Weather Forecast Icon", "key": "weather-forecast-icon", "visual_type": "icon", "description": "", "properties": {"static": False, "fontColor": "#1B9AF7"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 5, "size_y": 3, "block_feeds": [{"feed_id": "weather-forecast-icon", "group_id": "default"}]},
                             {"name": "Weather Forecast Text", "key": "weather-forecast-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "24", "showIcon": False, "decimalPlaces": "-1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 3,
                             "block_feeds": [{"feed_id": "weather-forecast-text", "group_id": "default"}]},
                             {"name": "Air Quality Level Gauge", "key": "air-quality-level", "visual_type": "gauge", "description": "", "properties": {"showIcon": False, "label": "Level", "minValue": "0", "maxValue": "3.9",
                                                                                                                                                 "ringWidth": "25", "minWarning": "1", "maxWarning": "2", "decimalPlaces": "0"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                             {"name": "Air Quality Level Text", "key": "air-quality-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "48", "showIcon": False, "decimalPlaces": "-1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 3, "size_y": 3, "block_feeds": [{"feed_id": "air-quality-text", "group_id": "default"}]},
                             {"name": "PM2.5 Gauge", "key": "pm2-dot-5-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:smog", "label": "ug/m3", "minValue": "0", "maxValue": "53",
                                                                                                                                                 "ringWidth": "25", "minWarning": "11", "maxWarning": "35", "decimalPlaces": "0"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "pm2-dot-5", "group_id": "default"}]},
                             {"name": "Air Quality Level Chart", "key": "air-quality-level-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Level", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": True, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                             {"name": "Air Particles Chart", "key": "air-particles", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ug/m3", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "pm1", "group_id": "default"}, {"feed_id": "pm2-dot-5", "group_id": "default"},
                                                                                                                 {"feed_id": "pm10", "group_id": "default"}]},
                             {"name": "Reducing Gas Chart", "key": "reducing-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "reducing", "group_id": "default"}]},
                             {"name": "Oxidising Gas Chart", "key": "oxidising-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "oxidising", "group_id": "default"}]},
                             {"name": "Ammonia Gas Chart", "key": "ammonia-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "ammonia", "group_id": "default"}]},
                             {"name": "Temperature Chart", "key": "temperature", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Degrees C", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                             {"name": "Humidity Chart", "key": "humidity", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "%", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                             {"name": "Air Pressure Chart", "key": "air-pressure", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "hPa", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]},
                             {"name": "Light Level Chart", "key": "lux", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Lux", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "lux", "group_id": "default"}]},
                             {"name": "Version", "key": "version", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "12", "showIcon": False, "decimalPlaces": "-1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 3, "block_feeds": [{"feed_id": "version", "group_id": "default"}]}]
enviro_aio_premium_noise_blocks = [{"name": "Temperature Gauge", "key": "temperature-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "thermometer", "label": "\u00b0 C", "minValue": "0", "maxValue": "40",
                                                                                                                                                 "ringWidth": "25", "minWarning": "5", "maxWarning": "35", "decimalPlaces": "1"},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                                   {"name": "Humidity Gauge", "key": "humidity-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:humidity", "label": "%", "minValue": "0", "maxValue": "100",
                                                                                                                                                 "ringWidth": "25", "minWarning": "30", "maxWarning": "80", "decimalPlaces": "0"},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                                   {"name": "Air Pressure Gauge", "key": "air-pressure-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:barometer", "label": "hPa", "minValue": "980", "maxValue": "1040",
                                                                                                                                                 "ringWidth": "25", "minWarning": "990", "maxWarning": "1030", "decimalPlaces": "1"},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]},
                                   {"name": "Weather Forecast Icon", "key": "weather-forecast-icon", "visual_type": "icon", "description": "", "properties": {"static": False, "fontColor": "#1B9AF7"},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 5, "size_y": 3, "block_feeds": [{"feed_id": "weather-forecast-icon", "group_id": "default"}]},
                                   {"name": "Weather Forecast Text", "key": "weather-forecast-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "24", "showIcon": False, "decimalPlaces": "-1"},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 3, "block_feeds": [{"feed_id": "weather-forecast-text", "group_id": "default"}]},
                                   {"name": "Air Quality Level Gauge", "key": "air-quality-level", "visual_type": "gauge", "description": "", "properties": {"showIcon": False, "label": "Level", "minValue": "0", "maxValue": "3.9",
                                                                                                                                                             "ringWidth": "25", "minWarning": "1", "maxWarning": "2", "decimalPlaces": "0"},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                                   {"name": "Air Quality Level Text", "key": "air-quality-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "48", "showIcon": False, "decimalPlaces": "-1"},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 3, "size_y": 3, "block_feeds": [{"feed_id": "air-quality-text", "group_id": "default"}]},
                                   {"name": "PM2.5 Gauge", "key": "pm2-dot-5-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:smog", "label": "ug/m3", "minValue": "0", "maxValue": "53",
                                                                                                                                                 "ringWidth": "25", "minWarning": "11", "maxWarning": "35", "decimalPlaces": "0"},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "pm2-dot-5", "group_id": "default"}]},
                                   {"name": "Air Quality Level Chart", "key": "air-quality-level-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Level", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                                                        "rawDataOnly": False, "steppedLine": True, "historyHours": 24},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                                   {"name": "Air Particles Chart", "key": "air-particles", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ug/m3", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                                          "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "pm1", "group_id": "default"}, {"feed_id": "pm2-dot-5", "group_id": "default"},
                                                                                                                        {"feed_id": "pm10", "group_id": "default"}]},
                                   {"name": "Reducing Gas Chart", "key": "reducing-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                          "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "reducing", "group_id": "default"}]},
                                   {"name": "Oxidising Gas Chart", "key": "oxidising-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                            "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "oxidising", "group_id": "default"}]},
                                   {"name": "Ammonia Gas Chart", "key": "ammonia-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                        "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "ammonia", "group_id": "default"}]},
                                   {"name": "Temperature Chart", "key": "temperature", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Degrees C", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                      "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                                   {"name": "Humidity Chart", "key": "humidity", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "%", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                                   {"name": "Air Pressure Chart", "key": "air-pressure", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "hPa", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                        "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]},
                                   {"name": "Light Level Chart", "key": "lux", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Lux", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                              "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "lux", "group_id": "default"}]},
                                   {"name": "Noise Level Chart", "key": "noise", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "dB(A)", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "max-noise", "group_id": "default"}, {"feed_id": "min-noise", "group_id": "default"},
                                                                                                                        {"feed_id": "mean-noise", "group_id": "default"}]},
                                   {"name": "Version", "key": "version", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "12", "showIcon": False, "decimalPlaces": "-1"},
                                    "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 3, "block_feeds": [{"feed_id": "version", "group_id": "default"}]}]
enviro_aio_premium_plus_blocks = [{"name": "Temperature Gauge", "key": "temperature-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "thermometer", "label": "\u00b0 C", "minValue": "0", "maxValue": "40",
                                                                                                                                                 "ringWidth": "25", "minWarning": "5", "maxWarning": "35", "decimalPlaces": "1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                             {"name": "Humidity Gauge", "key": "humidity-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:humidity", "label": "%", "minValue": "0", "maxValue": "100",
                                                                                                                                                 "ringWidth": "25", "minWarning": "30", "maxWarning": "80", "decimalPlaces": "0"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                             {"name": "Air Pressure Gauge", "key": "air-pressure-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:barometer", "label": "hPa", "minValue": "980", "maxValue": "1040",
                                                                                                                                                 "ringWidth": "25", "minWarning": "990", "maxWarning": "1030", "decimalPlaces": "1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]},
                             {"name": "Weather Forecast Icon", "key": "weather-forecast-icon", "visual_type": "icon", "description": "", "properties": {"static": False, "fontColor": "#1B9AF7"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 5, "size_y": 3, "block_feeds": [{"feed_id": "weather-forecast-icon", "group_id": "default"}]},
                             {"name": "Weather Forecast Text", "key": "weather-forecast-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "24", "showIcon": False, "decimalPlaces": "-1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 3,
                             "block_feeds": [{"feed_id": "weather-forecast-text", "group_id": "default"}]},
                             {"name": "Air Quality Level Gauge", "key": "air-quality-level", "visual_type": "gauge", "description": "", "properties": {"showIcon": False, "label": "Level", "minValue": "0", "maxValue": "3.9",
                                                                                                                                                 "ringWidth": "25", "minWarning": "1", "maxWarning": "2", "decimalPlaces": "0"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                             {"name": "Air Quality Level Text", "key": "air-quality-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "48", "showIcon": False, "decimalPlaces": "-1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 3, "size_y": 3, "block_feeds": [{"feed_id": "air-quality-text", "group_id": "default"}]},
                             {"name": "PM2.5 Gauge", "key": "pm2-dot-5-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:smog", "label": "ug/m3", "minValue": "0", "maxValue": "53",
                                                                                                                                                 "ringWidth": "25", "minWarning": "11", "maxWarning": "35", "decimalPlaces": "0"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "pm2-dot-5", "group_id": "default"}]},
                             {"name": "Air Quality Level Chart", "key": "air-quality-level-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Level", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": True, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                                  {"name": "Air Particles Chart", "key": "air-particles", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ug/m3", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "pm1", "group_id": "default"}, {"feed_id": "pm2-dot-5", "group_id": "default"},
                                                                                                                 {"feed_id": "pm10", "group_id": "default"}]},
                             {"name": "eCarbon Dioxide Gauge", "key": "ecarbon-dioxide-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:smog", "label": "ppm", "minValue": "400", "maxValue": "2000",
                                                                                                                                                 "ringWidth": "25", "minWarning": "1000", "maxWarning": "1600", "decimalPlaces": "0"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "carbon-dioxide", "group_id": "default"}]},
                                  {"name": "TVOC Gauge", "key": "tvoc-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:smog", "label": "ppb", "minValue": "0", "maxValue": "2200",
                                                                                                                                                 "ringWidth": "25", "minWarning": "220", "maxWarning": "660", "decimalPlaces": "0"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "tvoc", "group_id": "default"}]},
                             {"name": "eCarbon Dioxide Chart", "key": "ecarbon-dioxide-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "carbon-dioxide", "group_id": "default"}]},
                                  {"name": "TVOC Chart", "key": "tvoc-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppb", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "tvoc", "group_id": "default"}]},
                             {"name": "Reducing Gas Chart", "key": "reducing-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "reducing", "group_id": "default"}]},
                             {"name": "Oxidising Gas Chart", "key": "oxidising-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "oxidising", "group_id": "default"}]},
                             {"name": "Ammonia Gas Chart", "key": "ammonia-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "ammonia", "group_id": "default"}]},
                             {"name": "Temperature Chart", "key": "temperature", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Degrees C", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                             {"name": "Humidity Chart", "key": "humidity", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "%", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                             {"name": "Air Pressure Chart", "key": "air-pressure", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "hPa", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]},
                             {"name": "Light Level Chart", "key": "lux", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Lux", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "lux", "group_id": "default"}]},
                             {"name": "Version", "key": "version", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "12", "showIcon": False, "decimalPlaces": "-1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 3, "block_feeds": [{"feed_id": "version", "group_id": "default"}]}]
enviro_aio_premium_plus_noise_blocks = [{"name": "Temperature Gauge", "key": "temperature-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "thermometer", "label": "\u00b0 C", "minValue": "0", "maxValue": "40",
                                                                                                                                                            "ringWidth": "25", "minWarning": "5", "maxWarning": "35", "decimalPlaces": "1"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                                        {"name": "Humidity Gauge", "key": "humidity-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:humidity", "label": "%", "minValue": "0", "maxValue": "100",
                                                                                                                                                      "ringWidth": "25", "minWarning": "30", "maxWarning": "80", "decimalPlaces": "0"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                                        {"name": "Air Pressure Gauge", "key": "air-pressure-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:barometer", "label": "hPa", "minValue": "980", "maxValue": "1040",
                                                                                                                                                              "ringWidth": "25", "minWarning": "990", "maxWarning": "1030", "decimalPlaces": "1"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]},
                                        {"name": "Weather Forecast Icon", "key": "weather-forecast-icon", "visual_type": "icon", "description": "", "properties": {"static": False, "fontColor": "#1B9AF7"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 5, "size_y": 3, "block_feeds": [{"feed_id": "weather-forecast-icon", "group_id": "default"}]},
                                        {"name": "Weather Forecast Text", "key": "weather-forecast-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "24", "showIcon": False, "decimalPlaces": "-1"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 3,"block_feeds": [{"feed_id": "weather-forecast-text", "group_id": "default"}]},
                                        {"name": "Air Quality Level Gauge", "key": "air-quality-level", "visual_type": "gauge", "description": "", "properties": {"showIcon": False, "label": "Level", "minValue": "0", "maxValue": "3.9",
                                                                                                                                                                  "ringWidth": "25", "minWarning": "1", "maxWarning": "2", "decimalPlaces": "0"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                                        {"name": "Air Quality Level Text", "key": "air-quality-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "48", "showIcon": False, "decimalPlaces": "-1"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 3, "size_y": 3, "block_feeds": [{"feed_id": "air-quality-text", "group_id": "default"}]},
                                        {"name": "PM2.5 Gauge", "key": "pm2-dot-5-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:smog", "label": "ug/m3", "minValue": "0", "maxValue": "53",
                                                                                                                                                    "ringWidth": "25", "minWarning": "11", "maxWarning": "35", "decimalPlaces": "0"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "pm2-dot-5", "group_id": "default"}]},
                                        {"name": "Air Quality Level Chart", "key": "air-quality-level-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Level", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                                                             "rawDataOnly": False, "steppedLine": True, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                                        {"name": "Air Particles Chart", "key": "air-particles", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ug/m3", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                                               "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "pm1", "group_id": "default"}, {"feed_id": "pm2-dot-5", "group_id": "default"},
                                                                                                                             {"feed_id": "pm10", "group_id": "default"}]},
                                        {"name": "eCarbon Dioxide Gauge", "key": "ecarbon-dioxide-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:smog", "label": "ppm", "minValue": "400", "maxValue": "2000",
                                                                                                                                                                    "ringWidth": "25", "minWarning": "1000", "maxWarning": "1600", "decimalPlaces": "0"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "carbon-dioxide", "group_id": "default"}]},
                                        {"name": "TVOC Gauge", "key": "tvoc-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:smog", "label": "ppb", "minValue": "0", "maxValue": "2200",
                                                                                                                                              "ringWidth": "25", "minWarning": "220", "maxWarning": "660", "decimalPlaces": "0"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "tvoc", "group_id": "default"}]},
                                        {"name": "eCarbon Dioxide Chart", "key": "ecarbon-dioxide-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                                                         "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "carbon-dioxide", "group_id": "default"}]},
                                        {"name": "TVOC Chart", "key": "tvoc-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppb", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                                   "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "tvoc", "group_id": "default"}]},
                                        {"name": "Reducing Gas Chart", "key": "reducing-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                               "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "reducing", "group_id": "default"}]},
                                        {"name": "Oxidising Gas Chart", "key": "oxidising-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                                 "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "oxidising", "group_id": "default"}]},
                                        {"name": "Ammonia Gas Chart", "key": "ammonia-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                             "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "ammonia", "group_id": "default"}]},
                                        {"name": "Temperature Chart", "key": "temperature", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Degrees C", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                           "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                                        {"name": "Humidity Chart", "key": "humidity", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "%", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                     "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                                        {"name": "Air Pressure Chart", "key": "air-pressure", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "hPa", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                             "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]},
                                        {"name": "Light Level Chart", "key": "lux", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Lux", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                                   "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "lux", "group_id": "default"}]},
                                        {"name": "Noise Level Chart", "key": "noise", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "dB(A)", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                                     "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "max-noise", "group_id": "default"}, {"feed_id": "min-noise", "group_id": "default"},
                                                                                                                        {"feed_id": "mean-noise", "group_id": "default"}]},
                                        {"name": "Version", "key": "version", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "12", "showIcon": False, "decimalPlaces": "-1"},
                                         "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 3, "block_feeds": [{"feed_id": "version", "group_id": "default"}]}]
enviro_aio_basic_air_blocks = [{"name": "Air Quality Level Gauge", "key": "air-quality-level", "visual_type": "gauge", "description": "", "properties": {"showIcon": False, "label": "Level", "minValue": "0", "maxValue": "3.9",
                                                                                                                                                 "ringWidth": "25", "minWarning": "1", "maxWarning": "2", "decimalPlaces": "0"},
                                "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                               {"name": "Air Quality Level Chart", "key": "air-quality-level-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Level", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": True, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                               {"name": "Air Quality Level Text", "key": "air-quality-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "48", "showIcon": False, "decimalPlaces": "-1"},
                                "row": 0, "column": 0, "dashboard_id": 0, "size_x": 3, "size_y": 3, "block_feeds": [{"feed_id": "air-quality-text", "group_id": "default"}]},
                               {"name": "PM2.5 Gauge", "key": "pm2-dot-5-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:smog", "label": "ug/m3", "minValue": "0", "maxValue": "53",
                                                                                                                                                 "ringWidth": "25", "minWarning": "11", "maxWarning": "35", "decimalPlaces": "0"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "pm2-dot-5", "group_id": "default"}]},
                               {"name": "Air Particles Chart", "key": "air-particles", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ug/m3", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "pm1", "group_id": "default"}, {"feed_id": "pm2-dot-5", "group_id": "default"},
                                                                                                                   {"feed_id": "pm10", "group_id": "default"}]}]
enviro_aio_basic_combo_blocks = [{"name": "Temperature Gauge", "key": "temperature-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "thermometer", "label": "\u00b0 C", "minValue": "0", "maxValue": "40",
                                                                                                                                                 "ringWidth": "25", "minWarning": "5", "maxWarning": "35", "decimalPlaces": "1"},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                                 {"name": "Humidity Gauge", "key": "humidity-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:humidity", "label": "%", "minValue": "0", "maxValue": "100",
                                                                                                                                                 "ringWidth": "25", "minWarning": "30", "maxWarning": "80", "decimalPlaces": "0"},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                                 {"name": "Air Pressure Gauge", "key": "air-pressure-gauge", "visual_type": "gauge", "description": "", "properties": {"showIcon": True, "icon": "w:barometer", "label": "hPa", "minValue": "980", "maxValue": "1040",
                                                                                                                                                 "ringWidth": "25", "minWarning": "990", "maxWarning": "1030", "decimalPlaces": "1"},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]},
                                 {"name": "Weather Forecast Icon", "key": "weather-forecast-icon", "visual_type": "icon", "description": "", "properties": {"static": False, "fontColor": "#1B9AF7"},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 5, "size_y": 3, "block_feeds": [{"feed_id": "weather-forecast-icon", "group_id": "default"}]},
                                 {"name": "Air Quality Level Gauge", "key": "air-quality-level", "visual_type": "gauge", "description": "", "properties": {"showIcon": False, "label": "Level", "minValue": "0", "maxValue": "3.9",
                                                                                                                                                 "ringWidth": "25", "minWarning": "1", "maxWarning": "2", "decimalPlaces": "0"},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                                 {"name": "Air Quality Level Chart", "key": "air-quality-level-chart", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Level", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": True, "historyHours": 24},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                                 {"name": "Temperature Chart", "key": "temperature", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Degrees C", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                                 {"name": "Humidity Chart", "key": "humidity", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "%", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                                 {"name": "Air Pressure Chart", "key": "air-pressure", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "hPa", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]}]

def create_aio_enviro_feeds():
    feed_json = {}
    create_feed_error = False
    print("Creating Adafruit IO Feeds")
    for household in aio_feed_prefix:
        enviro_aio_feeds = enviro_aio_feeds_map[aio_feed_prefix[household]['package']]
        for enviro_feed in enviro_aio_feeds:
            if enviro_feed == "Barometer" or enviro_feed == "Weather Forecast Text" or enviro_feed == "Weather Forecast Icon":
                feed_json["name"] = household + ' ' + enviro_feed
                feed_json["key"] = aio_feed_prefix[household]['key'] + "-" + enviro_aio_feeds[enviro_feed] # Only one barometer feed, forecast feed and forecast icon feed per household
                feed_json["description"] = ""
                feed_json["visibility"] = aio_feed_prefix[household]["visibility"]
                print(feed_json)
                response, resp_error, reason = _post('/feeds/', feed_json)
                #print(response, resp_error, reason)
                if resp_error:
                    create_feed_error = True
                    feed_error_name = feed_json["name"]
                    feed_error_reason = reason
                if create_feed_error:
                    print(feed_json["name"], 'Feed Creation Failed because of',feed_error_reason)
                else:
                    print(feed_json["name"], 'Feed Creation Successful')
            elif enviro_feed == "Carbon Dioxide" or enviro_feed == "TVOC":
                feed_json["name"] = household + ' Indoor ' + enviro_feed
                feed_json["key"] = aio_feed_prefix[household]['key'] + "-indoor-" + enviro_aio_feeds[enviro_feed] # Only indoor eCO2 and TVOC feeds per household
                feed_json["description"] = ""
                feed_json["visibility"] = aio_feed_prefix[household]["visibility"]
                print(feed_json)
                response, resp_error, reason = _post('/feeds/', feed_json)
                #print(response, resp_error, reason)
                if resp_error:
                    create_feed_error = True
                    feed_error_name = feed_json["name"]
                    feed_error_reason = reason
                if create_feed_error:
                    print(feed_json["name"], 'Feed Creation Failed because of',feed_error_reason)
                else:
                    print(feed_json["name"], 'Feed Creation Successful')
            else:
                for location in aio_feed_prefix[household]['locations']:
                    feed_json["name"] = household + ' ' + location + ' ' + enviro_feed
                    feed_json["key"] = aio_feed_prefix[household]['key'] + "-" + aio_feed_prefix[household]['locations'][location] + "-" + enviro_aio_feeds[enviro_feed]
                    feed_json["description"] = ""
                    feed_json["visibility"] = aio_feed_prefix[household]["visibility"]
                    print(feed_json)
                    response, resp_error, reason = _post('/feeds/', feed_json)
                    #print(response, resp_error, reason)
                    if resp_error:
                        create_feed_error = True
                        feed_error_name = feed_json["name"]
                        feed_error_reason = reason
                    if create_feed_error:
                        print(feed_json["name"], 'Feed Creation Failed because of',feed_error_reason)
                    else:
                        print(feed_json["name"], 'Feed Creation Successful')


def _post(path, data):
    resp_error = False
    reason = ''
    try:
        response = requests.post(aio_url + path,
                             headers={'X-AIO-Key': aio_key,
                                                    'Content-Type': 'application/json'},
                             data=json.dumps(data), timeout=10)
        status_code = response.status_code
    except requests.exceptions.ConnectionError as e:
        resp_error = True
        reason = 'aio Connection Error'
        print('aio Connection Error', e)
    except requests.exceptions.Timeout as e:
        resp_error = True
        reason = 'aio Timeout Error'
        print('aio Timeout Error', e)
    except requests.exceptions.HTTPError as e:
        resp_error = True
        reason = 'aio HTTP Error'
        print('aio HTTP Error', e)     
    except requests.exceptions.RequestException as e:
        resp_error = True
        reason = 'aio Request Error'
        print('aio Request Error', e)
    else:
        if response.status_code == 429:
            resp_error = True
            reason = 'Throttling Error'
            print('aio Throttling Error')
        elif response.status_code >= 400:
            resp_error = True
            reason = 'Response Error: ' + str(response.status_code)
            print('aio ', reason)
    return response, resp_error, reason
    
def create_aio_enviro_dashboards():
    dashboard_json = {}
    create_dashboard_error = False
    for household in aio_feed_prefix:
        dashboard_json["name"] = household
        dashboard_json["key"] = aio_feed_prefix[household]["key"]
        dashboard_json["description"] = ""
        dashboard_json["visibility"] = aio_feed_prefix[household]["visibility"]
        response, resp_error, reason = _post('/dashboards/', dashboard_json)
        #print(response, resp_error, reason)
        if resp_error:
            create_dashboard_error = True
            dashboard_error_name = household
            dashboard_error_reason = reason
        if create_dashboard_error:
            print(household, 'Dashboard Creation Failed because of', dashboard_error_reason)
        else:
            print(household, 'Dashboard Creation Successful')
        
def create_aio_enviro_blocks():
    create_block_error = False
    for household in aio_feed_prefix:
        block_json = {}
        dashboard_key = aio_feed_prefix[household]["key"]
        if aio_feed_prefix[household]["package"] == 'Premium':
            dashboard_blocks = enviro_aio_premium_blocks
        elif aio_feed_prefix[household]["package"] == 'Premium Noise':
            dashboard_blocks = enviro_aio_premium_noise_blocks
        elif aio_feed_prefix[household]["package"] == 'Premium Plus':
            dashboard_blocks = enviro_aio_premium_plus_blocks
        elif aio_feed_prefix[household]["package"] == 'Premium Plus Noise':
            dashboard_blocks = enviro_aio_premium_plus_noise_blocks
        elif aio_feed_prefix[household]["package"] == 'Basic Air':
            dashboard_blocks = enviro_aio_basic_air_blocks
        elif aio_feed_prefix[household]["package"] == 'Basic Combo':
            dashboard_blocks = enviro_aio_basic_combo_blocks
        else:
            print("Invalid AIO Package for", household)
        #print(household, "Dashboard Blocks", dashboard_blocks)
        for block in range(len(dashboard_blocks)):
            #print(block, dashboard_blocks[block])
            if (dashboard_blocks[block]["name"] == "Weather Forecast Icon" or dashboard_blocks[block]["name"] == "Weather Forecast Text" or
                dashboard_blocks[block]["name"] == "Air Pressure Chart" or dashboard_blocks[block]["name"] == "Air Pressure Gauge"): # Only one of these per property and they only have one block_feed each
                for key in dashboard_blocks[block]:
                    if key != "block_feeds":
                        block_json[key] = dashboard_blocks[block][key]
                    else:
                        block_json["block_feeds"] = [{"group_id": dashboard_blocks[block]["block_feeds"][0]["group_id"], "feed_id": dashboard_key + "-" + dashboard_blocks[block]["block_feeds"][0]["feed_id"]}]
                # Send Block Data
                #print("block_json", block_json)
                response, resp_error, reason = _post('/dashboards/' + dashboard_key + '/blocks', block_json)
                if resp_error:
                    create_block_error = True
                    block_error_name = block
                    block_error_reason = reason
                else:
                    print(household, dashboard_blocks[block]["name"], 'Block Creation Successful')
            elif (dashboard_blocks[block]["name"] == "Temperature Chart" or dashboard_blocks[block]["name"] == "Humidity Chart" or dashboard_blocks[block]["name"] == "Light Level Chart" or
                  dashboard_blocks[block]["name"] == "Air Quality Level Chart" or dashboard_blocks[block]["name"] == "Reducing Gas Chart" or
                  dashboard_blocks[block]["name"] == "Oxidising Gas Chart" or dashboard_blocks[block]["name"] == "Ammonia Gas Chart"):
                # Can be only one of these per property and they have more than one block_feed each
                for key in dashboard_blocks[block]:
                    if key != "block_feeds":
                        block_json[key] = dashboard_blocks[block][key]
                    else:
                        block_json["block_feeds"] = [{"group_id": dashboard_blocks[block]["block_feeds"][0]["group_id"], "feed_id": aio_feed_prefix[household]["key"] + "-"
                                                          + aio_feed_prefix[household]["locations"][location] + "-" + dashboard_blocks[block]["block_feeds"][0]["feed_id"]}
                                                         for location in aio_feed_prefix[household]["locations"]]
                # Send block data
                #print("block_json", block_json)
                response, resp_error, reason = _post('/dashboards/' + dashboard_key + '/blocks', block_json)
                if resp_error:
                    create_block_error = True
                    block_error_name = block
                    block_error_reason = reason
                else:
                    print(household, dashboard_blocks[block]["name"], 'Block Creation Successful')
            elif (dashboard_blocks[block]["name"] == "Temperature Gauge" or dashboard_blocks[block]["name"] == "Humidity Gauge" or
                  dashboard_blocks[block]["name"] == "Air Quality Level Gauge" or dashboard_blocks[block]["name"] == "Air Quality Level Text" or
                  dashboard_blocks[block]["name"] == "PM2.5 Gauge" or dashboard_blocks[block]["name"] == "Version"): # Can be more than one of these per property and they only have one block_feed each
                for location in aio_feed_prefix[household]["locations"]:
                    for key in dashboard_blocks[block]:
                        if key == "name":
                            block_json[key] = location + " " + dashboard_blocks[block]["name"]
                        elif key == "key":
                            block_json[key] = aio_feed_prefix[household]["locations"][location] + "-" + dashboard_blocks[block]["key"]
                        elif key == "block_feeds":
                            block_json["block_feeds"] = [{"group_id": dashboard_blocks[block]["block_feeds"][0]["group_id"],"feed_id": dashboard_key + "-" +aio_feed_prefix[household]["locations"][location] +
                                                          '-' + dashboard_blocks[block]["block_feeds"][0]["feed_id"]}]
                        else: 
                            block_json[key] = dashboard_blocks[block][key]
                    # Send Block Data
                    #print("block_json", block_json)
                    response, resp_error, reason = _post('/dashboards/' + dashboard_key + '/blocks', block_json)
                    if resp_error:
                        create_block_error = True
                        block_error_name = block
                        block_error_reason = reason
                    else:
                        print(household, location, dashboard_blocks[block]["name"], 'Block Creation Successful')
            elif (dashboard_blocks[block]["name"] == "eCarbon Dioxide Gauge" or dashboard_blocks[block]["name"] == "TVOC Gauge" or
                   dashboard_blocks[block]["name"] == "eCarbon Dioxide Chart" or dashboard_blocks[block]["name"] == "TVOC Chart"): # Can only be Indoor Blocks
                location = "Indoor"
                for key in dashboard_blocks[block]:
                    if key == "name":
                        block_json[key] = location + " " + dashboard_blocks[block]["name"]
                    elif key == "key":
                        block_json[key] = "indoor-" + dashboard_blocks[block]["key"]
                    elif key == "block_feeds":
                        block_json["block_feeds"] = [{"group_id": dashboard_blocks[block]["block_feeds"][0]["group_id"],"feed_id": dashboard_key + "-indoor-" +
                                                      dashboard_blocks[block]["block_feeds"][0]["feed_id"]}]
                    else: 
                        block_json[key] = dashboard_blocks[block][key]
                # Send Block Data
                #print("block_json", block_json)
                response, resp_error, reason = _post('/dashboards/' + dashboard_key + '/blocks', block_json)
                if resp_error:
                    create_block_error = True
                    block_error_name = block
                    block_error_reason = reason
                else:
                    print(household, location, dashboard_blocks[block]["name"], 'Block Creation Successful')
            elif dashboard_blocks[block]["name"] == "Dummy for Future": # Can only be indoor Block but more than one feed
                location = "Indoor"
                for key in dashboard_blocks[block]:
                    if key == "name":
                        block_json[key] = location + " " + dashboard_blocks[block]["name"]
                    elif key == "key":
                        block_json[key] = aio_feed_prefix[household]["locations"][location] + "-" + dashboard_blocks[block]["key"]
                    elif key == "block_feeds":
                            block_json["block_feeds"] = [{"group_id": dashboard_blocks[block]["block_feeds"][block_feed]["group_id"], "feed_id": aio_feed_prefix[household]["key"] + "-"
                                                          + aio_feed_prefix[household]["locations"][location] + "-" + dashboard_blocks[block]["block_feeds"][block_feed]["feed_id"]}
                                                         for block_feed in range(len(dashboard_blocks[block]["block_feeds"]))]
                    else: 
                        block_json[key] = dashboard_blocks[block][key]
                # Send Block Data
                #print("block_json", block_json)
                response, resp_error, reason = _post('/dashboards/' + dashboard_key + '/blocks', block_json)
                if resp_error:
                    create_block_error = True
                    block_error_name = block
                    block_error_reason = reason
                else:
                    print(household, location, dashboard_blocks[block]["name"], 'Block Creation Successful')
            else:  # Can be more than one of these per property and they have more than one block_feed each
                for location in aio_feed_prefix[household]["locations"]:
                    for key in dashboard_blocks[block]:
                        if key == "name":
                            block_json[key] = location + " " + dashboard_blocks[block]["name"]
                        elif key == "key":
                            block_json[key] = aio_feed_prefix[household]["locations"][location] + "-" + dashboard_blocks[block]["key"]
                        elif key == "block_feeds":
                            block_json["block_feeds"] = [{"group_id": dashboard_blocks[block]["block_feeds"][block_feed]["group_id"], "feed_id": aio_feed_prefix[household]["key"] + "-"
                                                          + aio_feed_prefix[household]["locations"][location] + "-" + dashboard_blocks[block]["block_feeds"][block_feed]["feed_id"]}
                                                         for block_feed in range(len(dashboard_blocks[block]["block_feeds"]))]
                        else: 
                            block_json[key] = dashboard_blocks[block][key]
                    # Send block data
                    #print("block_json", block_json)
                    response, resp_error, reason = _post('/dashboards/' + dashboard_key + '/blocks', block_json)
                    if resp_error:
                        create_block_error = True
                        block_error_name = block
                        block_error_reason = reason
                    else:
                        print(household, location, dashboard_blocks[block]["name"], 'Block Creation Successful')
        if create_block_error:
            print(household, 'Block Creation Failed because of', block_error_reason)

def add_version_state_blocks(): # Add Version State blocks for each property location, if it's a Premium or Premium Plus Package
    create_block_error = False
    block_json = {"visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "12", "showIcon": False, "decimalPlaces": "-1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 2, "size_y": 1} # Set up Version State block properties
    for household in aio_feed_prefix:
        if aio_feed_prefix[household]["package"] == 'Premium' or aio_feed_prefix[household]["package"] == 'Premium Plus': # Add blocks to the Version State Dashboard
            for location in aio_feed_prefix[household]["locations"]:
                block_json["name"] = household + " " +  location
                block_json["key"] = aio_feed_prefix[household]["key"] + "-" + aio_feed_prefix[household]["locations"][location]
                
                block_json["block_feeds"] = [{"group_id": "default", "feed_id": block_json["key"] + "-" + "version"}]
                # Send Block Data
                #print("block_json", block_json)
                response, resp_error, reason = _post('/dashboards/version-state/blocks', block_json)
                if resp_error:
                    print(household, location, 'Version Block Creation Failed', reason, response)
                    block_error_reason = reason
                else:
                    print(household, location, 'Version Block Creation Successful')


 
# Set up Adafruit IO
print('Setting up Adafruit IO')
aio_url = "https://io.adafruit.com/api/v2/" + aio_user_name

create_aio_enviro_feeds()
create_aio_enviro_dashboards()
create_aio_enviro_blocks()
add_version_state_blocks()


            
            
            
            


