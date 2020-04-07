#!/usr/bin/env python3
#Northcliff Environment Monitor Adafruit IO Feed Setup 2.0 - Gen
# Supports aio feeds for Northcliff Enviro Monitor Versions >= 3.77

from Adafruit_IO import Client, Feed, Data, RequestError

# This dictionary sets up the feed name and key prefixes
# Enter your data in aio_feed_prefix
aio_feed_prefix = {'<Property1Name>': {'key': '<property1key>', 'locations': {'<Location1Name>': '<location1key>', '<Location2Name>': '<location2key>'}},
                   '<Property2Name>': {'key': '<property2key>', 'locations': {'<Location1Name>': '<location1key>'}}}
# This dictionary sets up the feed name and key suffixes to support the Enviro readings. Don't change this dictionary.
enviro_aio_feeds = {"Temperature": "temperature", "Humidity": "humidity", "Barometer": "barometer", "Lux": "lux", "PM1": "pm1", "PM2.5": "pm2-dot-5",
                    "PM10": "pm10", "Reducing": "reducing", "Oxidising": "oxidising", "Ammonia": "ammonia", "Air Quality Level": "air-quality-level", "Air Quality Text": "air-quality-text",
                    "Weather Forecast Text": "weather-forecast", "Weather Forecast Icon": "weather-forecast-icon"}
    
def create_aio_enviro_feeds(aio_feed_prefix, enviro_aio_feeds):
    print("Creating Adafruit IO Feeds")
    request_error = False
    for household in aio_feed_prefix:
        for location in aio_feed_prefix[household]['locations']:
            for enviro_feed in enviro_aio_feeds:
                if enviro_feed != "Barometer" and enviro_feed != "Weather Forecast Text" and enviro_feed != "Weather Forecast Icon":
                    feed = Feed(name=household + ' ' + location + ' ' + enviro_feed, key=aio_feed_prefix[household]['key'] + "-" + aio_feed_prefix[household]['locations'][location] + "-" + enviro_aio_feeds[enviro_feed])
                else:
                    feed = Feed(name=household + ' ' + enviro_feed, key=aio_feed_prefix[household]['key'] + "-" + enviro_aio_feeds[enviro_feed]) # Only one barometer feed, forecast feed and forecast icon feed per household
                print(feed)
                try:
                    test = aio.create_feed(feed)
                except RequestError:
                    print('Adafruit IO Create Feed Request Error', feed)
                    request_error = True
  
                
# Set up Adafruit IO
print('Setting up Adafruit IO')
aio_user_name = "<your Adafruit IO user name>"
aio_key = "<your Adafruit IO key>"
aio = Client(aio_user_name, aio_key)


create_aio_enviro_feeds(aio_feed_prefix, enviro_aio_feeds)
            


