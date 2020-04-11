#!/usr/bin/env python3
#Northcliff Environment Monitor Adafruit IO Feed Setup 3.0 - Gen
# Supports aio feeds for Northcliff Enviro Monitor Versions >= 3.87

from Adafruit_IO import Client, Feed, Data, RequestError


# This aio_feed_prefix dictionary sets up the feed name and key prefixes. Customise the dictionary based on the names and keys for each property to be monitored,
# the names and keys of the Enviro Monitors at each property (can be one Indoor unit or one Outdoor unit or a pairing of an Indoor and an Outdoor unit),
# aio_package choices are either "Premium", "Basic Air" or "Basic Combo". Enter your data between the # lines
##############################################################################################################################################################################################################################################
aio_feed_prefix = {'<Property1Name>': {'key': '<property1key>', 'package': '<aio_package>', 'locations': {'<Location1Name>': '<location1key>', '<Location2Name>': '<location2key>'}},
                   '<Property2Name>': {'key': '<property2key>', 'package': '<aio_package>', 'locations': {'<Location1Name>': '<location1key>'}}}
##############################################################################################################################################################################################################################################

# These dictionaries set up the feed name and key suffixes to support the Enviro readings. Don't change these dictionaries.
enviro_aio_premium_feeds = {"Temperature": "temperature", "Humidity": "humidity", "Barometer": "barometer", "Lux": "lux", "PM1": "pm1", "PM2.5": "pm2-dot-5",
                    "PM10": "pm10", "Reducing": "reducing", "Oxidising": "oxidising", "Ammonia": "ammonia", "Air Quality Level": "air-quality-level", "Air Quality Text": "air-quality-text",
                    "Weather Forecast Text": "weather-forecast", "Weather Forecast Icon": "weather-forecast-icon"}
enviro_aio_basic_air_feeds = {"PM1": "pm1", "PM2.5": "pm2-dot-5", "PM10": "pm10", "Air Quality Level": "air-quality-level", "Air Quality Text": "air-quality-text"}
enviro_aio_basic_combo_feeds = {"Temperature": "temperature", "Humidity": "humidity", "Barometer": "barometer", "Air Quality Level": "air-quality-level", "Weather Forecast Icon": "weather-forecast-icon"}
enviro_aio_feeds_map = {'Premium': enviro_aio_premium_feeds, 'Basic Air': enviro_aio_basic_air_feeds, 'Basic Combo': enviro_aio_basic_combo_feeds}

    
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

       
# Set up Adafruit IO
print('Setting up Adafruit IO')
aio_user_name = "<your Adafruit IO user name>"
aio_key = "<your Adafruit IO key>"
aio = Client(aio_user_name, aio_key)

create_aio_enviro_feeds()

            
            
            
            


