#!/usr/bin/env python3
#Northcliff Environment Monitor Adafruit IO Feed Setup 5.0 - Gen Add Dashboard and Block Creation
# Supports aio feeds for Northcliff Enviro Monitor Versions >= 3.8

from Adafruit_IO import Client, Feed, Data, RequestError
import requests
import json


# The aio_feed_prefix dictionary sets up the feed name and key prefixes, as well as the dashboard visibility setting. Customise the dictionary based on the names and keys for each property to be monitored,
# and the names and keys of the Enviro Monitors at each property (can be one Indoor unit or one Outdoor unit or a pairing of an Indoor and an Outdoor unit).
# aio_package choices are either "Premium", "Basic Air" or "Basic Combo". All of this data needs to match the setup for each Enviro Monitor's config.json file (i.e. "aio_household_prefix", "aio_location_prefix" and "aio_package")
# Also enter your Adafruit IO User Name and Key
#Enter your data between the #### lines
#####################################################################################################################################################################################################################
aio_feed_prefix = {'Property 1 Name': {'key': 'property1key', 'package': '<aio_package>', 'locations': {'<Location1Name>': '<location1key', '<Location2Name>': '<location2key'}, 'dashboard_visibility': '<public or private>'},
                   'Property 2 Name': {'key': 'property2key', 'package': '<aio_package>', 'locations': {'<Location1Name>': '<location1key>'}, 'dashboard_visibility': '<public or private>'}}
aio_user_name = "<Your Adafruit IO User Name Here>"
aio_key = "<Your Adafruit IO Key Here>"
#####################################################################################################################################################################################################################

# These dictionaries set up the feed name and key suffixes to support the Enviro readings. Don't change these dictionaries.
enviro_aio_premium_feeds = {"Temperature": "temperature", "Humidity": "humidity", "Barometer": "barometer", "Lux": "lux", "PM1": "pm1", "PM2.5": "pm2-dot-5",
                    "PM10": "pm10", "Reducing": "reducing", "Oxidising": "oxidising", "Ammonia": "ammonia", "Air Quality Level": "air-quality-level", "Air Quality Text": "air-quality-text",
                    "Weather Forecast Text": "weather-forecast", "Weather Forecast Icon": "weather-forecast-icon"}
enviro_aio_basic_air_feeds = {"PM1": "pm1", "PM2.5": "pm2-dot-5", "PM10": "pm10", "Air Quality Level": "air-quality-level", "Air Quality Text": "air-quality-text"}
enviro_aio_basic_combo_feeds = {"Temperature": "temperature", "Humidity": "humidity", "Barometer": "barometer", "Air Quality Level": "air-quality-level", "Weather Forecast Icon": "weather-forecast-icon"}
enviro_aio_feeds_map = {'Premium': enviro_aio_premium_feeds, 'Basic Air': enviro_aio_basic_air_feeds, 'Basic Combo': enviro_aio_basic_combo_feeds}
enviro_aio_premium_blocks = [{"name": "Weather Forecast", "key": "weather-forecast-icon", "visual_type": "icon", "description": "", "properties": {"static": False, "fontColor": "#1B9AF7"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 5, "size_y": 3, "block_feeds": [{"feed_id": "weather-forecast-icon", "group_id": "default"}]},
                             {"name": "Weather Forecast Text", "key": "weather-forecast-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "24", "showIcon": False, "decimalPlaces": "-1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 3,
                             "block_feeds": [{"feed_id": "weather-forecast-text", "group_id": "default"}]},
                             {"name": "Air Quality Level", "key": "air-quality-level", "visual_type": "gauge", "description": "", "properties": {"showIcon": False, "label": "Level", "minValue": "0", "maxValue": "3.9",
                                                                                                                                                 "ringWidth": "25", "minWarning": "1", "maxWarning": "2", "decimalPlaces": "0"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                             {"name": "Air Quality", "key": "air-quality-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "48", "showIcon": False, "decimalPlaces": "-1"},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 3, "size_y": 3, "block_feeds": [{"feed_id": "air-quality-text", "group_id": "default"}]},
                             {"name": "Air Particles", "key": "air-particles", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ug/m3", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "pm1", "group_id": "default"}, {"feed_id": "pm2-dot-5", "group_id": "default"},
                                                                                                                 {"feed_id": "pm10", "group_id": "default"}]},
                             {"name": "Gas Levels", "key": "gas-levels", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ppm", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "reducing", "group_id": "default"}, {"feed_id": "oxidising", "group_id": "default"},
                                                                                                                 {"feed_id": "ammonia", "group_id": "default"}]},
                             {"name": "Temperature", "key": "temperature", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Degrees C", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                             {"name": "Humidity", "key": "humidity", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "%", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                             {"name": "Air Pressure", "key": "air-pressure", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "hPa", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                              "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]}] 
enviro_aio_basic_air_blocks = [{"name": "Air Quality Level", "key": "air-quality-level", "visual_type": "gauge", "description": "", "properties": {"showIcon": False, "label": "Level", "minValue": "0", "maxValue": "3.9",
                                                                                                                                                 "ringWidth": "25", "minWarning": "1", "maxWarning": "2", "decimalPlaces": "0"},
                                "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                               {"name": "Air Quality", "key": "air-quality-text", "visual_type": "text", "description": "", "properties": {"static": False, "fontSize": "48", "showIcon": False, "decimalPlaces": "-1"},
                                "row": 0, "column": 0, "dashboard_id": 0, "size_x": 3, "size_y": 3, "block_feeds": [{"feed_id": "air-quality-text", "group_id": "default"}]},
                               {"name": "Air Particles", "key": "air-particles", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "ug/m3", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "0",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "pm1", "group_id": "default"}, {"feed_id": "pm2-dot-5", "group_id": "default"},
                                                                                                                   {"feed_id": "pm10", "group_id": "default"}]}]
enviro_aio_basic_combo_blocks = [{"name": "Weather Forecast", "key": "weather-forecast-icon", "visual_type": "icon", "description": "", "properties": {"static": False, "fontColor": "#1B9AF7"},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 5, "size_y": 3, "block_feeds": [{"feed_id": "weather-forecast-icon", "group_id": "default"}]},
                                 {"name": "Air Quality Level", "key": "air-quality-level", "visual_type": "gauge", "description": "", "properties": {"showIcon": False, "label": "Level", "minValue": "0", "maxValue": "3.9",
                                                                                                                                                 "ringWidth": "25", "minWarning": "1", "maxWarning": "2", "decimalPlaces": "0"},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 4, "size_y": 4, "block_feeds": [{"feed_id": "air-quality-level", "group_id": "default"}]},
                                 {"name": "Temperature", "key": "temperature", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "Degrees C", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "temperature", "group_id": "default"}]},
                                 {"name": "Humidity", "key": "humidity", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "%", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "humidity", "group_id": "default"}]},
                                 {"name": "Air Pressure", "key": "air-pressure", "visual_type": "line_chart", "description": "", "properties": {"xAxisLabel": "X", "yAxisLabel": "hPa", "yAxisMin": "", "yAxisMax": "", "decimalPlaces": "1",
                                                                                                                                    "rawDataOnly": False, "steppedLine": False, "historyHours": 24},
                                  "row": 0, "column": 0, "dashboard_id": 0, "size_x": 8, "size_y": 5, "block_feeds": [{"feed_id": "barometer", "group_id": "default"}]}]

    
def create_aio_enviro_feeds():
    print("Creating Adafruit IO Feeds")
    request_error = False
    for household in aio_feed_prefix:
        enviro_aio_feeds = enviro_aio_feeds_map[aio_feed_prefix[household]['package']]
        for location in aio_feed_prefix[household]['locations']:
            for enviro_feed in enviro_aio_feeds:
                if enviro_feed != "Barometer" and enviro_feed != "Weather Forecast Text" and enviro_feed != "Weather Forecast Icon":
                    feed = Feed(name=household + ' ' + location + ' ' + enviro_feed, key=aio_feed_prefix[household]['key'] + "-" + aio_feed_prefix[household]['locations'][location] + "-" + enviro_aio_feeds[enviro_feed])
                else:
                    feed = Feed(name=household + ' ' + enviro_feed, key=aio_feed_prefix[household]['key'] + "-" + enviro_aio_feeds[enviro_feed]) # Only one barometer feed, forecast feed and forecast icon feed per household
                try:
                    test = aio.create_feed(feed)
                    print("Created Feed", test)
                except RequestError:
                    print('Adafruit IO Create Feed Request Error', feed)
                    request_error = True


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
        dashboard_json["visibility"] = aio_feed_prefix[household]["dashboard_visibility"]
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
    block_json = {}
    create_block_error = False
    for household in aio_feed_prefix:
        dashboard_key = aio_feed_prefix[household]["key"]
        if aio_feed_prefix[household]["package"] == 'Premium':
            dashboard_blocks = enviro_aio_premium_blocks
        elif aio_feed_prefix[household]["package"] == 'Basic Air':
            dashboard_blocks = enviro_aio_basic_air_blocks
        elif aio_feed_prefix[household]["package"] == 'Basic Combo':
            dashboard_blocks = enviro_aio_basic_combo_blocks
        else:
            print("Invalid AIO Package for", household)
        for block in range(len(dashboard_blocks)):
            #print(block, dashboard_blocks[block])
            if dashboard_blocks[block]["name"] == "Weather Forecast" or dashboard_blocks[block]["name"] == "Weather Forecast Text" or dashboard_blocks[block]["name"] == "Air Pressure": # Only one of these per property and they only have one block_feed each
                for key in dashboard_blocks[block]:
                    if key != "block_feeds":
                        block_json[key] = dashboard_blocks[block][key]
                    else:
                        block_json["block_feeds"] = dashboard_blocks[block]["block_feeds"]
                        block_json["block_feeds"][0]["feed_id"] = dashboard_key + "-" + dashboard_blocks[block]["block_feeds"][0]["feed_id"]
                # Send Block Data
                response, resp_error, reason = _post('/dashboards/' + dashboard_key + '/blocks', block_json)
                if resp_error:
                    create_block_error = True
                    block_error_name = block
                    block_error_reason = reason
                else:
                    print(dashboard_blocks[block]["name"], 'Block Creation Successful')
            else:
                for location in aio_feed_prefix[household]["locations"]:
                    for key in dashboard_blocks[block]:
                        if key == "name":
                            block_json[key] = location + " " + dashboard_blocks[block]["name"]
                        elif key == "key":
                            block_json[key] = aio_feed_prefix[household]["locations"][location] + "-" + dashboard_blocks[block]["key"]
                        elif key == "block_feeds":
                            block_json["block_feeds"] = dashboard_blocks[block]["block_feeds"]
                            for block_feed in range(len(dashboard_blocks[block]["block_feeds"])):
                                block_json["block_feeds"][block_feed]["feed_id"] = aio_feed_prefix[household]["key"] + "-" + aio_feed_prefix[household]["locations"][location] + "-" + dashboard_blocks[block]["block_feeds"][block_feed]["feed_id"]
                        else: 
                            block_json[key] = dashboard_blocks[block][key]
                # Send block data
                response, resp_error, reason = _post('/dashboards/' + dashboard_key + '/blocks', block_json)
                if resp_error:
                    create_block_error = True
                    block_error_name = block
                    block_error_reason = reason
                else:
                    print(dashboard_blocks[block]["name"], 'Block Creation Successful')              
    if create_block_error:
        print(household, 'Dashboard Creation Failed because of', block_error_reason) 
                
                
# Set up Adafruit IO
print('Setting up Adafruit IO')
aio_url = "https://io.adafruit.com/api/v2/" + aio_user_name
aio = Client(aio_user_name, aio_key)
create_aio_enviro_feeds()
create_aio_enviro_dashboards()
create_aio_enviro_blocks()


            
            
            
            


