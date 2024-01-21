#!/usr/bin/env python3
#Northcliff Environment Monitor
# Requires Home Manager >=8.54 with Enviro Monitor timeout

import paho.mqtt.client as mqtt
import colorsys
import math
import json
import requests
import ST7735
import os
import time
from datetime import datetime, timedelta
from fonts.ttf import RobotoMedium as UserFont
import pytz
from pytz import timezone
from astral.geocoder import database, lookup, add_locations
from astral.sun import sun
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559
from enviroplus import gas
from bme280 import BME280
from pms5003 import PMS5003, ReadTimeoutError, ChecksumMismatchError
from subprocess import check_output
from PIL import Image, ImageDraw, ImageFont, ImageFilter
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus
import logging

monitor_version = "7.2 - Gen"

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
logging.info("""Northcliff_Environment_Monitor.py - Pimoroni Enviro+ with noise measurement (and optional SGP30) sensor capture and display.
 Supports external sensor capture and Luftdaten, mqtt and Adafruit IO Updates
 Disclaimer: The noise measurement is not to be used for accurate sound level measurements.
 
#Note: you'll need to register with Luftdaten at:
#https://meine.luftdaten.info/ and enter your Raspberry Pi
#serial number that's displayed on the Enviro plus LCD along
#with the other details before the data appears on the
#Luftdaten map.

#""")
print(monitor_version)

bus = SMBus(1)

# Create a BME280 instance
bme280 = BME280(i2c_dev=bus)

# Create an LCD instance
disp = ST7735.ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    rotation=270,
    spi_speed_hz=10000000
)

# Initialize display
disp.begin()

def retrieve_config():
    try:
        with open('<Your config.json file location>', 'r') as f:
            parsed_config_parameters = json.loads(f.read())
            print('Retrieved Config', parsed_config_parameters)
    except IOError:
        print('Config Retrieval Failed')
    temp_offset = parsed_config_parameters['temp_offset']
    altitude = parsed_config_parameters['altitude']
    enable_display = parsed_config_parameters['enable_display'] # Enables the display and flags that the
    # weather protection cover is used with different temp/hum compensation
    enable_adafruit_io = parsed_config_parameters['enable_adafruit_io']
    aio_user_name = parsed_config_parameters['aio_user_name']
    aio_key = parsed_config_parameters['aio_key']
    aio_feed_window = parsed_config_parameters['aio_feed_window']
    aio_feed_sequence = parsed_config_parameters['aio_feed_sequence']
    aio_household_prefix = parsed_config_parameters['aio_household_prefix']
    aio_location_prefix = parsed_config_parameters['aio_location_prefix']
    aio_package = parsed_config_parameters['aio_package']
    enable_send_data_to_homemanager = parsed_config_parameters['enable_send_data_to_homemanager']
    enable_receive_data_from_homemanager = parsed_config_parameters['enable_receive_data_from_homemanager']
    enable_indoor_outdoor_functionality = parsed_config_parameters['enable_indoor_outdoor_functionality']
    mqtt_broker_name = parsed_config_parameters['mqtt_broker_name']
    enable_luftdaten = parsed_config_parameters['enable_luftdaten']
    enable_climate_and_gas_logging = parsed_config_parameters['enable_climate_and_gas_logging']
    enable_particle_sensor = parsed_config_parameters['enable_particle_sensor']
    if 'enable_eco2_tvoc' in parsed_config_parameters:
        enable_eco2_tvoc = parsed_config_parameters['enable_eco2_tvoc']
    else:
        enable_eco2_tvoc = False
    if 'gas_daily_r0_calibration_hour' in parsed_config_parameters:
        gas_daily_r0_calibration_hour = parsed_config_parameters['gas_daily_r0_calibration_hour']
    else:
        gas_daily_r0_calibration_hour = 3
    if 'reset_gas_sensor_calibration' in parsed_config_parameters:
        reset_gas_sensor_calibration = parsed_config_parameters['reset_gas_sensor_calibration']
    else:
        reset_gas_sensor_calibration = False
    if 'mqtt_username' in parsed_config_parameters:
        mqtt_username = parsed_config_parameters['mqtt_username']
    else:
        mqtt_username = None
    if 'mqtt_password' in parsed_config_parameters:
        mqtt_password = parsed_config_parameters['mqtt_password']
    else:
        mqtt_password = None
    if 'outdoor_source_type' in parsed_config_parameters:
        outdoor_source_type = parsed_config_parameters['outdoor_source_type']  # Can be "Enviro", "Luftdaten"
        # or "Adafruit IO"
    else:
        outdoor_source_type = 'Enviro'
    if 'outdoor_source_id' in parsed_config_parameters:
        outdoor_source_id = parsed_config_parameters['outdoor_source_id']  # Sets Luftdaten or Adafruit IO Sensor IDs
        # if using those sensors for outdoor readings, with the format: {"Climate": id, "PM": id} for Luftdaten or
        # {"User Name": "<aio_user_name>", "Key": "<aio_key>", "Household Name": "<aio_household_name>"} for Adafruit IO
    else:
        outdoor_source_id = {}
    if 'enable_noise' in parsed_config_parameters: # Enables Noise level sensing
        enable_noise = parsed_config_parameters['enable_noise']
    else:
        enable_noise = False
    if 'enable_luftdaten_noise' in parsed_config_parameters: # Enables Noise level uploads to Luftdaten. enable_noise must also be set to true for this to work
        enable_luftdaten_noise = parsed_config_parameters['enable_luftdaten_noise']
    else:
        enable_luftdaten_noise = False
    if 'disable_luftdaten_sensor_upload' in parsed_config_parameters: # Luftdaten currently only supports two sensors per node
        # When enable_luftdaten_noise is true, this must be set to either 'Climate' to disable climate reading uploads or 'PM' to disable air particle reading uploads
        # Set to 'None' when enable_luftdaten_noise is false
        disable_luftdaten_sensor_upload = parsed_config_parameters['disable_luftdaten_sensor_upload']
    else:
        disable_luftdaten_sensor_upload = 'None'
    # Correct any Luftdaten Noise misconfigurations
    if not enable_noise:
        disable_luftdaten_sensor_upload = 'None'
        if enable_luftdaten_noise:
            print('Noise sensor must be enabled in order to enable Luftdaten Noise. Disabling Luftdaten Noise')
            enable_luftdaten_noise = False
    else:
        if enable_luftdaten_noise and disable_luftdaten_sensor_upload == 'None':
            # Comment out next two lines once Luftdaten supports three sensors per node
            print('Luftdaten currently only supports two sensors and three have been enabled. Disabling Luftdaten Climate uploads')
            disable_luftdaten_sensor_upload = 'Climate'
            pass
    incoming_temp_hum_mqtt_topic = parsed_config_parameters['incoming_temp_hum_mqtt_topic']
    incoming_temp_hum_mqtt_sensor_name = parsed_config_parameters['incoming_temp_hum_mqtt_sensor_name']
    incoming_barometer_mqtt_topic = parsed_config_parameters['incoming_barometer_mqtt_topic']
    incoming_barometer_sensor_id = parsed_config_parameters['incoming_barometer_sensor_id']
    indoor_outdoor_function = parsed_config_parameters['indoor_outdoor_function']
    mqtt_client_name = parsed_config_parameters['mqtt_client_name']
    outdoor_mqtt_topic = parsed_config_parameters['outdoor_mqtt_topic']
    indoor_mqtt_topic = parsed_config_parameters['indoor_mqtt_topic']
    city_name = parsed_config_parameters['city_name']
    time_zone = parsed_config_parameters['time_zone']
    custom_locations = parsed_config_parameters['custom_locations']
    return (temp_offset, altitude, enable_display, enable_adafruit_io, aio_user_name, aio_key, aio_feed_window,
            aio_feed_sequence, aio_household_prefix, aio_location_prefix, aio_package, enable_send_data_to_homemanager,
            enable_receive_data_from_homemanager, enable_indoor_outdoor_functionality,
            mqtt_broker_name, mqtt_username, mqtt_password, outdoor_source_type, outdoor_source_id, enable_noise, enable_luftdaten,
            enable_luftdaten_noise, disable_luftdaten_sensor_upload, enable_climate_and_gas_logging, enable_particle_sensor,
            enable_eco2_tvoc, gas_daily_r0_calibration_hour, reset_gas_sensor_calibration, incoming_temp_hum_mqtt_topic,
            incoming_temp_hum_mqtt_sensor_name, incoming_barometer_mqtt_topic, incoming_barometer_sensor_id,
            indoor_outdoor_function, mqtt_client_name, outdoor_mqtt_topic, indoor_mqtt_topic, city_name, time_zone,
            custom_locations)

# Config Setup
(temp_offset, altitude, enable_display, enable_adafruit_io, aio_user_name, aio_key, aio_feed_window, aio_feed_sequence,
  aio_household_prefix, aio_location_prefix, aio_package, enable_send_data_to_homemanager,
  enable_receive_data_from_homemanager, enable_indoor_outdoor_functionality, mqtt_broker_name,
  mqtt_username, mqtt_password, outdoor_source_type, outdoor_source_id, enable_noise, enable_luftdaten,
  enable_luftdaten_noise, disable_luftdaten_sensor_upload, enable_climate_and_gas_logging,  enable_particle_sensor, enable_eco2_tvoc,
  gas_daily_r0_calibration_hour, reset_gas_sensor_calibration, incoming_temp_hum_mqtt_topic, incoming_temp_hum_mqtt_sensor_name,
  incoming_barometer_mqtt_topic, incoming_barometer_sensor_id, indoor_outdoor_function, mqtt_client_name,
  outdoor_mqtt_topic, indoor_mqtt_topic, city_name, time_zone, custom_locations) = retrieve_config()

# Add to city database
db = database()
add_locations(custom_locations, db)

if enable_particle_sensor:
    # Create a PMS5003 instance
    pms5003 = PMS5003()
    time.sleep(1)

if enable_noise:
    import sounddevice as sd
    import numpy as np
    from numpy import pi, log10
    from scipy.signal import zpk2tf, zpk2sos, freqs, sosfilt
    from waveform_analysis.weighting_filters._filter_design import _zpkbilinear
               
def read_pm_values(luft_values, mqtt_values, own_data, own_disp_values):
    if enable_particle_sensor:
        try:
            pm_values = pms5003.read()
            #print('PM Values:', pm_values)
            own_data["P2.5"][1] = pm_values.pm_ug_per_m3(2.5)
            mqtt_values["P2.5"] = own_data["P2.5"][1]
            own_disp_values["P2.5"] = own_disp_values["P2.5"][1:] + [[own_data["P2.5"][1], 1]]
            luft_values["P2"] = str(mqtt_values["P2.5"])
            own_data["P10"][1] = pm_values.pm_ug_per_m3(10)
            mqtt_values["P10"] = own_data["P10"][1]
            own_disp_values["P10"] = own_disp_values["P10"][1:] + [[own_data["P10"][1], 1]]
            luft_values["P1"] = str(own_data["P10"][1])
            own_data["P1"][1] = pm_values.pm_ug_per_m3(1.0)
            mqtt_values["P1"] = own_data["P1"][1]
            own_disp_values["P1"] = own_disp_values["P1"][1:] + [[own_data["P1"][1], 1]]
        except (ReadTimeoutError, ChecksumMismatchError):
            logging.info("Failed to read PMS5003")
            display_error('Particle Sensor Error')
            pms5003.reset()
            pm_values = pms5003.read()
            own_data["P2.5"][1] = pm_values.pm_ug_per_m3(2.5)
            mqtt_values["P2.5"] = own_data["P2.5"][1]
            own_disp_values["P2.5"] = own_disp_values["P2.5"][1:] + [[own_data["P2.5"][1], 1]]
            luft_values["P2"] = str(mqtt_values["P2.5"])
            own_data["P10"][1] = pm_values.pm_ug_per_m3(10)
            mqtt_values["P10"] = own_data["P10"][1]
            own_disp_values["P10"] = own_disp_values["P10"][1:] + [[own_data["P10"][1], 1]]
            luft_values["P1"] = str(own_data["P10"][1])
            own_data["P1"][1] = pm_values.pm_ug_per_m3(1.0)
            mqtt_values["P1"] = own_data["P1"][1]
            own_disp_values["P1"] = own_disp_values["P1"][1:] + [[own_data["P1"][1], 1]]
    return(luft_values, mqtt_values, own_data, own_disp_values)

def read_eco2_tvoc_values(mqtt_values, own_data, own_disp_values):
    eco2, tvoc = sgp30.command('measure_air_quality')
    #print(eco2, tvoc)
    own_data["CO2"][1] = eco2
    mqtt_values["CO2"] = eco2
    own_disp_values["CO2"] = own_disp_values["CO2"][1:] + [[own_data["CO2"][1], 1]]
    own_data["VOC"][1] = tvoc
    mqtt_values["VOC"] = tvoc
    own_disp_values["VOC"] = own_disp_values["VOC"][1:] + [[own_data["VOC"][1], 1]]
    return mqtt_values, own_data, own_disp_values

# Read gas and climate values from Home Manager and /or BME280 
def read_climate_gas_values(luft_values, mqtt_values, own_data, maxi_temp, mini_temp, own_disp_values, gas_sensors_warm,
                            gas_calib_temp, gas_calib_hum, gas_calib_bar, altitude, enable_eco2_tvoc):
    raw_temp, comp_temp = adjusted_temperature()
    raw_hum, comp_hum = adjusted_humidity()
    current_time = time.time()
    use_external_temp_hum = False
    use_external_barometer = False
    if enable_receive_data_from_homemanager:
        use_external_temp_hum, use_external_barometer = es.check_valid_readings(current_time)
    if use_external_temp_hum == False:
        print("Internal Temp/Hum Sensor")
        luft_values["temperature"] = "{:.2f}".format(comp_temp)
        own_data["Temp"][1] = round(comp_temp, 1)
        luft_values["humidity"] = "{:.2f}".format(comp_hum)
        own_data["Hum"][1] = round(comp_hum, 1)
    else: # Use external temp/hum sensor but still capture raw temp and raw hum for gas compensation and logging
        print("External Temp/Hum Sensor")
        luft_values["temperature"] = es.temperature
        own_data["Temp"][1] = float(luft_values["temperature"])
        luft_values["humidity"] = es.humidity
        own_data["Hum"][1] = float(luft_values["humidity"])
    own_data["Dew"][1] = round(calculate_dewpoint(own_data["Temp"][1], own_data["Hum"][1]),1)
    own_disp_values["Dew"] = own_disp_values["Dew"][1:] + [[own_data["Dew"][1], 1]]
    mqtt_values["Dew"]  = own_data["Dew"][1]
    own_disp_values["Temp"] = own_disp_values["Temp"][1:] + [[own_data["Temp"][1], 1]]
    mqtt_values["Temp"] = own_data["Temp"][1]
    own_disp_values["Hum"] = own_disp_values["Hum"][1:] + [[own_data["Hum"][1], 1]]
    mqtt_values["Hum"][0] = own_data["Hum"][1]
    mqtt_values["Hum"][1] = domoticz_hum_map[describe_humidity(own_data["Hum"][1])]
    if enable_eco2_tvoc: # Calculate and send the absolute humidity reading to the SGP30 for humidity compensation
        absolute_hum = int(1000 * 216.7 * (raw_hum/100 * 6.112 * math.exp(17.62 * raw_temp / (243.12 + raw_temp)))
                           /(273.15 + raw_temp))
        sgp30.command('set_humidity', [absolute_hum])
    else:
        absolute_hum = None
    # Determine max and min temps
    if first_climate_reading_done :
        if maxi_temp is None:
            maxi_temp = own_data["Temp"][1]
        elif own_data["Temp"][1] > maxi_temp:
            maxi_temp = own_data["Temp"][1]
        else:
            pass
        if mini_temp is None:
            mini_temp = own_data["Temp"][1]
        elif own_data["Temp"][1] < mini_temp:
            mini_temp = own_data["Temp"][1]
        else:
            pass
    mqtt_values["Min Temp"] = mini_temp
    mqtt_values["Max Temp"] = maxi_temp
    raw_barometer = bme280.get_pressure()
    if use_external_barometer == False:
        print("Internal Barometer")
        own_data["Bar"][1] = round(raw_barometer * barometer_altitude_comp_factor(altitude, own_data["Temp"][1]), 2)
        own_disp_values["Bar"] = own_disp_values["Bar"][1:] + [[own_data["Bar"][1], 1]]
        mqtt_values["Bar"][0] = own_data["Bar"][1]
        luft_values["pressure"] = "{:.2f}".format(raw_barometer * 100) # Send raw air pressure to Lufdaten,
        # since it does its own altitude air pressure compensation
        print("Raw Bar:", round(raw_barometer, 2), "Comp Bar:", own_data["Bar"][1])
    else:
        print("External Barometer")
        own_data["Bar"][1] = round(float(es.barometer), 2)
        own_disp_values["Bar"] = own_disp_values["Bar"][1:] + [[own_data["Bar"][1], 1]]
        mqtt_values["Bar"][0] = own_data["Bar"][1]
        # Remove altitude compensation from external barometer because Lufdaten does its own altitude air pressure
        # compensation
        luft_values["pressure"] = "{:.2f}".format(float(es.barometer) / barometer_altitude_comp_factor (
            altitude, own_data["Temp"][1]) * 100)
        print("Luft Bar:", luft_values["pressure"], "Comp Bar:", own_data["Bar"][1])
    red_in_ppm, oxi_in_ppm, nh3_in_ppm, comp_red_rs, comp_oxi_rs, comp_nh3_rs, raw_red_rs, raw_oxi_rs, raw_nh3_rs =\
        read_gas_in_ppm(gas_calib_temp, gas_calib_hum, gas_calib_bar, raw_temp, raw_hum, raw_barometer, gas_sensors_warm)
    own_data["Red"][1] = round(red_in_ppm, 2)
    own_disp_values["Red"] = own_disp_values["Red"][1:] + [[own_data["Red"][1], 1]]
    mqtt_values["Red"] = own_data["Red"][1]
    own_data["Oxi"][1] = round(oxi_in_ppm, 2)
    own_disp_values["Oxi"] = own_disp_values["Oxi"][1:] + [[own_data["Oxi"][1], 1]]
    mqtt_values["Oxi"] = own_data["Oxi"][1]
    own_data["NH3"][1] = round(nh3_in_ppm, 2)
    own_disp_values["NH3"] = own_disp_values["NH3"][1:] + [[own_data["NH3"][1], 1]]
    mqtt_values["NH3"] = own_data["NH3"][1]
    mqtt_values["Gas Calibrated"] = gas_sensors_warm
    proximity = ltr559.get_proximity()
    if proximity < 500:
        own_data["Lux"][1] = round(ltr559.get_lux(), 1)
    else:
        own_data["Lux"][1] = 1
    own_disp_values["Lux"] = own_disp_values["Lux"][1:] + [[own_data["Lux"][1], 1]]
    mqtt_values["Lux"] = own_data["Lux"][1]
    return luft_values, mqtt_values, own_data, maxi_temp, mini_temp, own_disp_values, raw_red_rs, raw_oxi_rs,\
           raw_nh3_rs, raw_temp, comp_temp, comp_hum, raw_hum, use_external_temp_hum, use_external_barometer,\
           raw_barometer, absolute_hum
    
def barometer_altitude_comp_factor(alt, temp):
    comp_factor = math.pow(1 - (0.0065 * altitude/(temp + 0.0065 * alt + 273.15)), -5.257)
    return comp_factor
    
def read_raw_gas():
    gas_data = gas.read_all()
    raw_red_rs = round(gas_data.reducing, 0)
    raw_oxi_rs = round(gas_data.oxidising, 0)
    raw_nh3_rs = round(gas_data.nh3, 0)
    return raw_red_rs, raw_oxi_rs, raw_nh3_rs
    
def read_gas_in_ppm(gas_calib_temp, gas_calib_hum, gas_calib_bar, raw_temp, raw_hum, raw_barometer, gas_sensors_warm):
    if gas_sensors_warm:
        comp_red_rs, comp_oxi_rs, comp_nh3_rs, raw_red_rs, raw_oxi_rs, raw_nh3_rs = comp_gas(gas_calib_temp,
                                                                                             gas_calib_hum,
                                                                                             gas_calib_bar,
                                                                                             raw_temp,
                                                                                             raw_hum, raw_barometer)
        print("Reading Compensated Gas sensors after warmup completed")
    else:
        raw_red_rs, raw_oxi_rs, raw_nh3_rs = read_raw_gas()
        comp_red_rs = raw_red_rs
        comp_oxi_rs = raw_oxi_rs
        comp_nh3_rs = raw_nh3_rs
        print("Reading Raw Gas sensors before warmup completed")
    print("Red Rs:", round(comp_red_rs, 0), "Oxi Rs:", round(comp_oxi_rs, 0), "NH3 Rs:", round(comp_nh3_rs, 0))
    if comp_red_rs/red_r0 > 0:
        red_ratio = comp_red_rs/red_r0
    else:
        red_ratio = 0.0001
    if comp_oxi_rs/oxi_r0 > 0:
        oxi_ratio = comp_oxi_rs/oxi_r0
    else:
        oxi_ratio = 0.0001
    if comp_nh3_rs/nh3_r0 > 0:
        nh3_ratio = comp_nh3_rs/nh3_r0
    else:
        nh3_ratio = 0.0001
    red_in_ppm = math.pow(10, -1.25 * math.log10(red_ratio) + 0.64)
    oxi_in_ppm = math.pow(10, math.log10(oxi_ratio) - 0.8129)
    nh3_in_ppm = math.pow(10, -1.8 * math.log10(nh3_ratio) - 0.163)
    return red_in_ppm, oxi_in_ppm, nh3_in_ppm, comp_red_rs, comp_oxi_rs, comp_nh3_rs, raw_red_rs, raw_oxi_rs, raw_nh3_rs

def comp_gas(gas_calib_temp, gas_calib_hum, gas_calib_bar, raw_temp, raw_hum, raw_barometer):
    gas_data = gas.read_all()
    gas_temp_diff = raw_temp - gas_calib_temp
    gas_hum_diff = raw_hum - gas_calib_hum
    gas_bar_diff = raw_barometer - gas_calib_bar
    raw_red_rs = round(gas_data.reducing, 0)
    comp_red_rs = round(raw_red_rs - (red_temp_comp_factor * raw_red_rs * gas_temp_diff +
                                      red_hum_comp_factor * raw_red_rs * gas_hum_diff +
                                      red_bar_comp_factor * raw_red_rs * gas_bar_diff), 0)
    raw_oxi_rs = round(gas_data.oxidising, 0)
    comp_oxi_rs = round(raw_oxi_rs - (oxi_temp_comp_factor * raw_oxi_rs * gas_temp_diff +
                                      oxi_hum_comp_factor * raw_oxi_rs * gas_hum_diff +
                                      oxi_bar_comp_factor * raw_oxi_rs * gas_bar_diff), 0)
    raw_nh3_rs = round(gas_data.nh3, 0)
    comp_nh3_rs = round(raw_nh3_rs - (nh3_temp_comp_factor * raw_nh3_rs * gas_temp_diff +
                                      nh3_hum_comp_factor * raw_nh3_rs * gas_hum_diff +
                                      nh3_bar_comp_factor * raw_nh3_rs * gas_bar_diff), 0)
    print("Gas Compensation. Raw Red Rs:", raw_red_rs, "Comp Red Rs:", comp_red_rs, "Raw Oxi Rs:",
          raw_oxi_rs, "Comp Oxi Rs:", comp_oxi_rs,
          "Raw NH3 Rs:", raw_nh3_rs, "Comp NH3 Rs:", comp_nh3_rs)
    return comp_red_rs, comp_oxi_rs, comp_nh3_rs, raw_red_rs, raw_oxi_rs, raw_nh3_rs   
    
def adjusted_temperature():
    raw_temp = bme280.get_temperature()
    #comp_temp = comp_temp_slope * raw_temp + comp_temp_intercept
    comp_temp = (comp_temp_cub_a * math.pow(raw_temp, 3) + comp_temp_cub_b * math.pow(raw_temp, 2) +
                 comp_temp_cub_c * raw_temp + comp_temp_cub_d)
    return raw_temp, comp_temp

def adjusted_humidity():
    raw_hum = bme280.get_humidity()
    #comp_hum = comp_hum_slope * raw_hum + comp_hum_intercept
    comp_hum = comp_hum_quad_a * math.pow(raw_hum, 2) + comp_hum_quad_b * raw_hum + comp_hum_quad_c
    return raw_hum, min(100, comp_hum)

def calculate_dewpoint(dew_temp, dew_hum):
    dewpoint = (237.7 * (math.log(dew_hum/100)+17.271*dew_temp/(237.7+dew_temp))/(17.271 - math.log(dew_hum/100) - 17.271*dew_temp/(237.7 + dew_temp)))
    return dewpoint

def log_climate_and_gas(run_time, own_data, raw_red_rs, raw_oxi_rs, raw_nh3_rs, raw_temp, comp_temp, comp_hum,
                        raw_hum, use_external_temp_hum, use_external_barometer, raw_barometer):
    # Used to log climate and gas data to create compensation algorithms
    raw_temp = round(raw_temp, 2)
    raw_hum = round(raw_hum, 2)
    comp_temp = round(comp_temp, 2)
    comp_hum = round(comp_hum, 2)
    raw_barometer = round(raw_barometer, 1)
    raw_red_rs = round(raw_red_rs, 0)
    raw_oxi_rs = round(raw_oxi_rs, 0)
    raw_nh3_rs = round(raw_nh3_rs, 0)
    today = datetime.now()
    time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
    if use_external_temp_hum and use_external_barometer:
        environment_log_data = {'Time': time_stamp, 'Run Time': run_time, 'Raw Temperature': raw_temp,
                                'Output Temp': comp_temp, 'Real Temperature': own_data["Temp"][1],
                                'Raw Humidity': raw_hum, 'Output Humidity': comp_hum,
                                'Real Humidity': own_data["Hum"][1], 'Real Bar': own_data["Bar"][1],
                                'Raw Bar': raw_barometer, 'Oxi': own_data["Oxi"][1], 'Red': own_data["Red"][1],
                                'NH3': own_data["NH3"][1], 'Raw OxiRS': raw_oxi_rs, 'Raw RedRS': raw_red_rs,
                                'Raw NH3RS': raw_nh3_rs}
    elif use_external_temp_hum and not(use_external_barometer):
        environment_log_data = {'Time': time_stamp, 'Run Time': run_time, 'Raw Temperature': raw_temp,
                                'Output Temp': comp_temp, 'Real Temperature': own_data["Temp"][1],
                                'Raw Humidity': raw_hum, 'Output Humidity': comp_hum,
                                'Real Humidity': own_data["Hum"][1], 'Output Bar': own_data["Bar"][1],
                                'Raw Bar': raw_barometer, 'Oxi': own_data["Oxi"][1], 'Red': own_data["Red"][1],
                                'NH3': own_data["NH3"][1], 'Raw OxiRS': raw_oxi_rs, 'Raw RedRS': raw_red_rs,
                                'Raw NH3RS': raw_nh3_rs}
    elif not(use_external_temp_hum) and use_external_barometer:
        environment_log_data = {'Time': time_stamp, 'Run Time': run_time, 'Raw Temperature': raw_temp,
                                'Output Temp': comp_temp, 'Raw Humidity': raw_hum, 'Output Humidity': comp_hum,
                                'Real Bar': own_data["Bar"][1], 'Raw Bar': raw_barometer, 'Oxi': own_data["Oxi"][1],
                                'Red': own_data["Red"][1], 'NH3': own_data["NH3"][1], 'Raw OxiRS': raw_oxi_rs,
                                'Raw RedRS': raw_red_rs, 'Raw NH3RS': raw_nh3_rs}
    else:
        environment_log_data = {'Time': time_stamp, 'Run Time': run_time, 'Raw Temperature': raw_temp,
                                'Output Temp': comp_temp,  'Raw Humidity': raw_hum, 'Output Humidity': comp_hum,
                                'Output Bar': own_data["Bar"][1], 'Raw Bar': raw_barometer, 'Oxi': own_data["Oxi"][1],
                                'Red': own_data["Red"][1], 'NH3': own_data["NH3"][1], 'Raw OxiRS': raw_oxi_rs,
                                'Raw RedRS': raw_red_rs, 'Raw NH3RS': raw_nh3_rs}
    print('Logging Environment Data.', environment_log_data)
    with open('<Your Environment Log File Location Here>', 'a') as f:
        f.write(',\n' + json.dumps(environment_log_data))
    
# Calculate Air Quality Level
def max_aqi_level_factor(gas_sensors_warm, air_quality_data, air_quality_data_no_gas, data):
    max_aqi_level = 0
    max_aqi_factor = 'All'
    max_aqi = [max_aqi_factor, max_aqi_level]
    if gas_sensors_warm:
        aqi_data = air_quality_data
    else:
        aqi_data = air_quality_data_no_gas
    for aqi_factor in aqi_data:
        aqi_factor_level = 0
        thresholds = data[aqi_factor][2]
        for level in range(len(thresholds)):
            if data[aqi_factor][1] != None:
                if data[aqi_factor][1] > thresholds[level]:
                    aqi_factor_level = level + 1
        if aqi_factor_level > max_aqi[1]:
            max_aqi = [aqi_factor, aqi_factor_level]
    return max_aqi
        
# Get Raspberry Pi serial number to use as ID
def get_serial_number():
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if line[0:6] == 'Serial':
                return line.split(":")[1].strip()

# Check for Wi-Fi connection
def check_wifi():
    if check_output(['hostname', '-I']):
        return True
    else:
        return False

# Display Startup Message on LCD when using the SGP30 sensor
def display_startup(message):
    text_colour = (255, 255, 255)
    back_colour = (85, 15, 15)
    error_message = "{}".format(message)
    img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    size_x, size_y = draw.textsize(message, mediumfont)
    x = (WIDTH - size_x) / 2
    y = (HEIGHT / 2) - (size_y / 2)
    draw.rectangle((0, 0, 160, 80), back_colour)
    draw.text((x, y), error_message, font=mediumfont, fill=text_colour)
    disp.display(img)

# Display Error Message on LCD
def display_error(message):
    text_colour = (255, 255, 255)
    back_colour = (85, 15, 15)
    error_message = "System Error\n{}".format(message)
    img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    size_x, size_y = draw.textsize(message, mediumfont)
    x = (WIDTH - size_x) / 2
    y = (HEIGHT / 2) - (size_y / 2)
    draw.rectangle((0, 0, 160, 80), back_colour)
    draw.text((x, y), error_message, font=mediumfont, fill=text_colour)
    disp.display(img)

# Display the Raspberry Pi serial number and Adafruit IO Dashboard URL (if enabled) on a background colour
# based on the air quality level
def disabled_display(gas_sensors_warm, air_quality_data, air_quality_data_no_gas, data, palette, enable_adafruit_io,
                     aio_user_name, aio_household_prefix):
    max_aqi = max_aqi_level_factor(gas_sensors_warm, air_quality_data, air_quality_data_no_gas, data)
    back_colour = palette[max_aqi[1]]
    text_colour = (0, 0, 0)
    id = get_serial_number()
    if enable_adafruit_io:
        message = "{}\nhttp://io.adafruit.com\n/{}/dashboards\n/{}".format(id, aio_user_name, aio_household_prefix)
    else:
        message = "{}".format(id)
    img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    size_x, size_y = draw.textsize(message, font_smm)
    x = (WIDTH - size_x) / 2
    y = (HEIGHT / 2) - (size_y / 2)
    draw.rectangle((0, 0, 160, 80), back_colour)
    draw.text((x, y), message, font=font_smm, fill=text_colour)
    disp.display(img)
    
# Display Raspberry Pi serial and Adafruit IO Dashboard URL (if enabled)
def display_status(enable_adafruit_io, aio_user_name, aio_household_prefix):
    wifi_status = "connected" if check_wifi() else "disconnected"
    text_colour = (255, 255, 255)
    back_colour = (0, 170, 170) if check_wifi() else (85, 15, 15)
    id = get_serial_number()
    if enable_adafruit_io:
        message = "{}\nhttp://io.adafruit.com\n/{}/dashboards\n/{}".format(id, aio_user_name, aio_household_prefix)
    else:
        message = "Northcliff\nEnviro Monitor\n{}\nwifi: {}".format(id, wifi_status)
    img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    size_x, size_y = draw.textsize(message, font_smm)
    x = (WIDTH - size_x) / 2
    y = (HEIGHT / 2) - (size_y / 2)
    draw.rectangle((0, 0, 160, 80), back_colour)
    draw.text((x, y), message, font=font_smm, fill=text_colour)
    disp.display(img)
    
def send_data_to_aio(feed_key, data):
    aio_json = {"value": data}
    resp_error = False
    reason = ''
    response = ''
    try:
        response = requests.post(aio_url + '/feeds/' + feed_key + '/data',
                                 headers={'X-AIO-Key': aio_key,
                                          'Content-Type': 'application/json'},
                                 data=json.dumps(aio_json), timeout=5)
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
        if status_code == 429:
            resp_error = True
            reason = 'Throttling Error'
            print('aio Throttling Error')
        elif status_code >= 400:
            resp_error = True
            reason = 'Response Error: ' + str(response.status_code)
            print('aio ', reason)
    return not resp_error

def send_to_luftdaten(luft_values, id, enable_particle_sensor, enable_noise, luft_noise_values, disable_luftdaten_sensor_upload):
    print("Sending Data to Luftdaten")
    pm_send_attempt = False
    climate_send_attempt = False
    noise_send_attempt = False
    all_responses_ok = True
    resp_1_exception = False
    resp_2_exception = False
    resp_3_exception = False

    if enable_particle_sensor and disable_luftdaten_sensor_upload != 'PM':
        pm_values = dict(i for i in luft_values.items() if i[0].startswith("P"))
        pm_send_attempt = True
        try:
            resp_1 = requests.post("https://api.luftdaten.info/v1/push-sensor-data/",
                     json={
                         "software_version": "northclff_enviro_monitor " + monitor_version,
                         "sensordatavalues": [{"value_type": key, "value": val} for
                                              key, val in pm_values.items()]
                     },
                     headers={
                         "X-PIN":   "1",
                         "X-Sensor": id,
                         "Content-Type": "application/json",
                         "cache-control": "no-cache"
                     },
                    timeout=5
            )
        except requests.exceptions.ConnectionError as e:
            resp_1_exception = True
            print('Luftdaten PM Connection Error', e)
        except requests.exceptions.Timeout as e:
            resp_1_exception = True
            print('Luftdaten PM Timeout Error', e)
        except requests.exceptions.RequestException as e:
            resp_1_exception = True
            print('Luftdaten PM Request Error', e)

    if disable_luftdaten_sensor_upload != 'Climate':
        temp_values = dict(i for i in luft_values.items() if not i[0].startswith("P"))
        climate_send_attempt = True
        try:
            resp_2 = requests.post("https://api.luftdaten.info/v1/push-sensor-data/",
                     json={
                         "software_version": "northclff_enviro_monitor " + monitor_version,
                         "sensordatavalues": [{"value_type": key, "value": val} for
                                              key, val in temp_values.items()]
                     },
                     headers={
                         "X-PIN":   "11",
                         "X-Sensor": id,
                         "Content-Type": "application/json",
                         "cache-control": "no-cache"
                     },
                    timeout=5
            )
        except requests.exceptions.ConnectionError as e:
            resp_2_exception = True
            print('Luftdaten Climate Connection Error', e)
        except requests.exceptions.Timeout as e:
            resp_2_exception = True
            print('Luftdaten Climate Timeout Error', e)
        except requests.exceptions.RequestException as e:
            resp_2_exception = True
            print('Luftdaten Climate Request Error', e)

    if enable_noise and enable_luftdaten_noise and luft_noise_values != []:
        noise_values = [{"value_type": "noise_LAeq", "value": "{:.2f}".format(sum(luft_noise_values)/len(luft_noise_values))},
                         {"value_type": "noise_LA_min", "value": "{:.2f}".format(min(luft_noise_values))},
                          {"value_type": "noise_LA_max", "value": "{:.2f}".format(max(luft_noise_values))}]
        print("Sending Luftdaten Noise Data", noise_values)
        noise_send_attempt = True
        try:
            resp_3 = requests.post("https://api.luftdaten.info/v1/push-sensor-data/",
                     json={
                         "software_version": "northclff_enviro_monitor " + monitor_version,
                         "sensordatavalues": noise_values
                     },
                     headers={
                         "X-PIN":   "15",
                         "X-Sensor": id,
                         "Content-Type": "application/json",
                         "cache-control": "no-cache"
                     },
                    timeout=5
            )
        except requests.exceptions.ConnectionError as e:
            resp_3_exception = True
            print('Luftdaten Noise Connection Error', e)
        except requests.exceptions.Timeout as e:
            resp_3_exception = True
            print('Luftdaten Noise Timeout Error', e)
        except requests.exceptions.RequestException as e:
            resp_3_exception = True
            print('Luftdaten Noise Request Error', e)
        #print(resp_3)
            
    if not (resp_1_exception or resp_2_exception or resp_3_exception):
        if pm_send_attempt:
            if not resp_1.ok:
                all_responses_ok = False
        if climate_send_attempt:
            if not resp_2.ok:
                all_responses_ok = False
        if noise_send_attempt:
            if not resp_3.ok:
                all_responses_ok = False
    else:
        all_responses_ok = False
    return all_responses_ok
    
def on_connect(client, userdata, flags, rc):
    es.print_update('Northcliff Environment Monitor Connected with result code ' + str(rc))
    if enable_receive_data_from_homemanager:
        client.subscribe(incoming_temp_hum_mqtt_topic) # Subscribe to the topic for the external temp/hum data
        client.subscribe(incoming_barometer_mqtt_topic) # Subscribe to the topic for the external barometer data
    if enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor' and outdoor_source_type == "Enviro":
        client.subscribe(outdoor_mqtt_topic)

def on_message(client, userdata, msg):
    decoded_payload = str(msg.payload.decode("utf-8"))
    parsed_json = json.loads(decoded_payload)
    # Identify external temp/hum sensor
    if msg.topic == incoming_temp_hum_mqtt_topic and parsed_json['name'] == incoming_temp_hum_mqtt_sensor_name:
        es.capture_temp_humidity(parsed_json)
    # Identify external barometer
    if msg.topic == incoming_barometer_mqtt_topic and parsed_json['idx'] == incoming_barometer_sensor_id:
        es.capture_barometer(parsed_json['svalue'])
    if enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor' and msg.topic == outdoor_mqtt_topic:
        capture_outdoor_data(parsed_json)
            
def capture_outdoor_data(parsed_json):
    global captured_outdoor_data
    captured_outdoor_data = parsed_json
    
# Displays graphed data and text on the 0.96" LCD
def display_graphed_data(location, disp_values, variable, data, WIDTH):
    # Scale the received disp_values for the variable between 0 and 1
    #print ("Display Values", disp_values)
    received_disp_values = [disp_values[variable][v][0]*disp_values[variable][v][1]
                            for v in range(len(disp_values[variable]))]
    graph_range = [(v - min(received_disp_values)) / (max(received_disp_values) - min(received_disp_values))
                   if ((max(received_disp_values) - min(received_disp_values)) != 0)
                   else 0 for v in received_disp_values]           
    # Format the variable name and value
    if variable == "Oxi":
        message = "{} {}: {:.2f} {}".format(location, variable[:4], data[1], data[0])
    elif variable == "Bar":
        message = "{}: {:.1f} {}".format(variable[:4], data[1], data[0])
    elif (variable[:1] == "P" or variable == "Red" or variable == "NH3" or variable == "CO2" or variable == "VOC" or
          variable == "Hum" or variable == "Lux"):
        message = "{} {}: {:.0f} {}".format(location, variable[:4], round(data[1], 0), data[0])
    else:
        message = "{} {}: {:.1f} {}".format(location, variable[:4], data[1], data[0])
    #logging.info(message)
    draw.rectangle((0, 0, WIDTH, HEIGHT), (255, 255, 255))
    # Determine the backgound colour for received data, based on level thresholds. Black for data not received.
    for i in range(len(disp_values[variable])):
        if disp_values[variable][i][1] == 1:
            lim = data[2]
            rgb = palette[0]
            for j in range(len(lim)):
                if disp_values[variable][i][0] > lim[j]:
                    rgb = palette[j+1]
        else:
            rgb = (0,0,0)
        # Draw a 2-pixel wide rectangle of colour based on reading levels relative to level thresholds
        draw.rectangle((i*2, top_pos, i*2+2, HEIGHT), rgb)
        # Draw a 2 pixel by 2 pixel line graph in black based on the reading levels
        line_y = (HEIGHT-2) - ((top_pos + 1) + (graph_range[i] * ((HEIGHT-2) - (top_pos + 1)))) + (top_pos + 1)
        draw.rectangle((i*2, line_y, i*2+2, line_y+2), (0, 0, 0))
    # Write the text at the top in black
    draw.text((0, 0), message, font=font_ml, fill=(0, 0, 0))
    disp.display(img)

# Displays the weather forecast on the 0.96" LCD
def display_forecast(valid_barometer_history, forecast, barometer_available_time, barometer, barometer_change):
    text_colour = (255, 255, 255)
    back_colour = (0, 0, 0)
    if valid_barometer_history:
        message = "Barometer {:.0f} hPa\n3Hr Change {:.0f} hPa\n{}".format(round(barometer, 0),
                                                                           round(barometer_change, 0), forecast)
    else:
        minutes_to_forecast = (barometer_available_time - time.time()) / 60
        if minutes_to_forecast >= 2:
            message = "WEATHER FORECAST\nReady in {:.0f} minutes".format(minutes_to_forecast)
        elif minutes_to_forecast > 0 and minutes_to_forecast < 2:
            message = "WEATHER FORECAST\nReady in a minute"
        else:
            message = "WEATHER FORECAST\nPreparing Summary\nPlease Wait..."
    img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    size_x, size_y = draw.textsize(message, mediumfont)
    x = (WIDTH - size_x) / 2
    y = (HEIGHT / 2) - (size_y / 2)
    draw.rectangle((0, 0, 160, 80), back_colour)
    draw.text((x, y), message, font=mediumfont, fill=text_colour)
    disp.display(img)
    
# Displays all the air quality text on the 0.96" LCD
def display_all_aq(location, data, data_in_display_all_aq, enable_eco2_tvoc):
    draw.rectangle((0, 0, WIDTH, HEIGHT), (0, 0, 0))
    column_count = 2
    if enable_eco2_tvoc:
        font=font_smm
    else:
        font=font_ml
    draw.text((2, 2), location + ' AIR QUALITY', font=font, fill=(255, 255, 255))
    row_count = round((len(data_in_display_all_aq) / column_count), 0)
    for i in data_in_display_all_aq:
        data_value = data[i][1]
        unit = data[i][0]
        column = int(data[i][3] / row_count)
        row = data[i][3] % row_count
        x = x_offset + ((WIDTH/column_count) * column)
        y = y_offset + ((HEIGHT/(row_count + 1) * (row +1)))
        if (i == "CO2" or i == "VOC") and location == "OUT" or data_value == None:
            message = "{}: N/A".format(i) # No CO2 or TVOC data comes from an outdoor unit
            # and no gas or P1 readings when Luftdaten is the source of outdoor readings
            # (used on display of indoor unit when displaying outdoor readings)
        elif i == "Oxi" and data_value != None:
            message = "{}: {:.2f}".format(i, data_value)
        else:
            message = "{}: {:.0f}".format(i, round(data_value, 0))
        lim = data[i][2]
        rgb = palette[0]
        if data_value != None:
            for j in range(len(lim)):
                if data_value > lim[j]:
                    rgb = palette[j+1]
        draw.text((x, y), message, font=font, fill=rgb)
    disp.display(img)
        
def display_noise(location, selected_display_mode, noise_level, noise_max, noise_max_datetime, display_changed, last_page, noise_values, freq_values):
    draw.rectangle((0, 0, WIDTH, HEIGHT), noise_back_colour)
    if noise_level<=noise_thresholds[0]:
        message_colour = (0, 255, 0)
    elif noise_thresholds[0]<noise_level<=noise_thresholds[1]:
        message_colour=(255, 255, 0)
    else:
        message_colour = (255, 0, 0)
    if selected_display_mode == "Noise Reading":
        draw.text((5,0), location + " Noise Level", font=noise_smallfont, fill=message_colour)
        draw.text((5, 32), f"{noise_level:.1f} dB(A)", font=noise_largefont, fill=message_colour)
        disp.display(img)
    elif selected_display_mode == "Noise Level":
        if noise_max<=noise_thresholds[0]:
            max_graph_colour = (0, 255, 0)
        elif noise_thresholds[0]<noise_max<=noise_thresholds[1]:
            max_graph_colour = (255, 255, 0)
        else:
            max_graph_colour = (255, 0, 0)
        for i in range(len(noise_values)):
            if noise_values[i][1] == 1:
                if noise_values[i][0]<=noise_thresholds[0]:
                    graph_colour = (0, 255, 0)
                elif noise_thresholds[0]<noise_max<=noise_thresholds[1]:
                    graph_colour=(255, 255, 0)
                else:
                    graph_colour = (255, 0, 0)
                draw.line((5+i*6, HEIGHT, 5+i*6, HEIGHT - (noise_values[i][0]-35)), fill=graph_colour, width=5)   
        draw.text((5,0), location + " Noise Level", font=noise_smallfont, fill=message_colour)
        if noise_max != 0 and (time.time() - last_page) > 2:
            draw.line((0, HEIGHT - (noise_max-35), WIDTH, HEIGHT - (noise_max-35)), fill=max_graph_colour, width=1) #Display Max Line
            if noise_max > 85:
                text_height = HEIGHT - (noise_max-37)
            else:
                text_height = HEIGHT - (noise_max-20)
            draw.text((0, text_height), f"Max {noise_max:.1f} dB {noise_max_datetime['Time']} {noise_max_datetime['Date']}", font=noise_vsmallfont, fill=max_graph_colour)
        disp.display(img)
    else:
        for i in range(len(freq_values)):
            if freq_values[i][3] == 1:
                draw.line((15+i*20, HEIGHT, 15+i*20, HEIGHT - (freq_values[i][2]*0.747-45)), fill=(0, 0, 255), width=5)
                draw.line((10+i*20, HEIGHT, 10+i*20, HEIGHT - (freq_values[i][1]*0.844-59)), fill=(0, 255, 0), width=5)
                draw.line((5+i*20, HEIGHT, 5+i*20, HEIGHT - (freq_values[i][0]*1.14-103)), fill=(255, 0, 0), width=5)
        draw.text((0,0), location + " Noise Bands", font=noise_smallfont, fill=message_colour)
        disp.display(img) 

def display_results(start_current_display, current_display_is_own, display_modes,
                                indoor_outdoor_display_duration, own_data, data_in_display_all_aq, outdoor_data,
                                outdoor_reading_captured, own_disp_values, outdoor_disp_values, delay, last_page, mode,
                                WIDTH, valid_barometer_history, forecast, barometer_available_time, barometer_change,
                                barometer_trend, icon_forecast, maxi_temp, mini_temp, air_quality_data,
                                air_quality_data_no_gas, gas_sensors_warm, outdoor_gas_sensors_warm, enable_display,
                                palette, enable_adafruit_io, aio_user_name, aio_household_prefix, enable_eco2_tvoc,
                                outdoor_source_type, own_noise_level, own_noise_max, own_noise_max_datetime,
                                own_noise_values, own_noise_freq_values, outdoor_noise_level, outdoor_noise_max,
                                outdoor_noise_max_datetime, outdoor_noise_values, outdoor_noise_freq_values):
    # Allow for display selection if display is enabled,
    # else only display the serial number on a background colour based on max_aqi
    if enable_display:
        proximity = ltr559.get_proximity()
        # If the proximity crosses the threshold, toggle the mode
        if proximity > 1500 and time.time() - last_page > delay:
            mode += 1
            mode %= len(display_modes)
            print('Mode', mode)
            last_page = time.time()
            display_changed = True
        else:
            display_changed = False
        selected_display_mode = display_modes[mode]
        if enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor':
            if outdoor_reading_captured:
                if ((time.time() -  start_current_display) > indoor_outdoor_display_duration):
                    current_display_is_own = not current_display_is_own
                    start_current_display = time.time()
            else:
                current_display_is_own = True
        if selected_display_mode in own_data:
            if current_display_is_own and indoor_outdoor_function == 'Indoor' or selected_display_mode == "Bar":
                display_graphed_data('IN', own_disp_values, selected_display_mode, own_data[selected_display_mode],
                                     WIDTH)
            elif current_display_is_own and indoor_outdoor_function == 'Outdoor':
                display_graphed_data('OUT', own_disp_values, selected_display_mode, own_data[selected_display_mode],
                                     WIDTH)
            elif not current_display_is_own and (indoor_outdoor_function == 'Indoor'
                                                 and (selected_display_mode == "CO2"
                                                      or selected_display_mode == "VOC"
                                                      or outdoor_source_type == "Luftdaten"
                                                      and (selected_display_mode == "Oxi"
                                                           or selected_display_mode == "Red"
                                                           or selected_display_mode == "NH3"
                                                           or selected_display_mode == "P1"
                                                           or selected_display_mode == "Lux")
                                                      or outdoor_source_type == "Adafruit IO"
                                                      and selected_display_mode == "Lux")):
                # No outdoor gas, P1, Lux graphs when outdoor source is Luftdaten.
                # No outdoor Lux graphs when the outdoor source is Adafruit IO
                # and no outdoor CO2 or TVOC graphs,
                # so always display indoor graph
                display_graphed_data('IN', own_disp_values, selected_display_mode, own_data[selected_display_mode],
                                     WIDTH)
            else:
                display_graphed_data('OUT', outdoor_disp_values, selected_display_mode,
                                     outdoor_data[selected_display_mode], WIDTH)
        elif selected_display_mode == "Forecast":
            display_forecast(valid_barometer_history, forecast, barometer_available_time, own_data["Bar"][1],
                             barometer_change)
        elif selected_display_mode == "Status":
            display_status(enable_adafruit_io, aio_user_name, aio_household_prefix)
        elif selected_display_mode == "All Air":
            # Display everything on one screen
            if current_display_is_own and indoor_outdoor_function == 'Indoor':
                display_all_aq('IN', own_data, data_in_display_all_aq, enable_eco2_tvoc)
            elif current_display_is_own and indoor_outdoor_function == 'Outdoor':
                display_all_aq('OUT', own_data, data_in_display_all_aq, enable_eco2_tvoc)
            else:
                display_all_aq('OUT', outdoor_data, data_in_display_all_aq, enable_eco2_tvoc)
        elif selected_display_mode == "Icon Weather":
            # Display icon weather/aqi
            if current_display_is_own and indoor_outdoor_function == 'Indoor':
                display_icon_weather_aqi('IN', own_data, barometer_trend, icon_forecast, maxi_temp, mini_temp,
                                         air_quality_data,
                                         air_quality_data_no_gas, icon_air_quality_levels, gas_sensors_warm, own_noise_level, own_noise_max)
            elif current_display_is_own and indoor_outdoor_function == 'Outdoor':
                display_icon_weather_aqi('OUT', own_data, barometer_trend, icon_forecast, maxi_temp, mini_temp,
                                         air_quality_data,
                                         air_quality_data_no_gas, icon_air_quality_levels, gas_sensors_warm, own_noise_level, own_noise_max)
            else:
                display_icon_weather_aqi('OUT', outdoor_data, barometer_trend, icon_forecast, outdoor_maxi_temp,
                                         outdoor_mini_temp,
                                         air_quality_data, air_quality_data_no_gas, icon_air_quality_levels,
                                         outdoor_gas_sensors_warm, outdoor_noise_level, outdoor_noise_max)
        elif "Noise" in selected_display_mode:
            if selected_display_mode == "Noise Level" and display_changed:
                own_noise_max = 0 # Reset Max Noise Reading when first entering "Noise Level Mode"
            if current_display_is_own:
                display_noise(indoor_outdoor_function, selected_display_mode, own_noise_level, own_noise_max, own_noise_max_datetime, display_changed, last_page, own_noise_values, own_noise_freq_values)
            elif not current_display_is_own and indoor_outdoor_function == 'Indoor' and outdoor_noise_level == 0: # Don't display outdoor noise levels on indoor unit when there are no outdoor noise readings
                display_noise("Indoor", selected_display_mode, own_noise_level, own_noise_max, own_noise_max_datetime, display_changed, last_page, own_noise_values, own_noise_freq_values)
            else:
                display_noise("Outdoor", selected_display_mode, outdoor_noise_level, outdoor_noise_max, outdoor_noise_max_datetime, display_changed, last_page, outdoor_noise_values, outdoor_noise_freq_values)
        else:
            pass
    else:
        disabled_display(gas_sensors_warm, air_quality_data, air_quality_data_no_gas, own_data, palette,
                         enable_adafruit_io, aio_user_name, aio_household_prefix)
    return last_page, mode, start_current_display, current_display_is_own, own_noise_max

class ExternalSensors(object): # Handles the external temp/hum/bar sensors
    def __init__(self):
        self.barometer_update_time = 0
        self.temp_humidity_update_time = 0
        #self.print_update('Instantiated External Sensors')
        
    def capture_barometer(self, value):
        self.barometer = value[:-2] # Remove forecast data
        self.barometer_update_time = time.time()
        #self.print_update('External Barometer ' + self.barometer + ' Pa')

    def capture_temp_humidity(self, parsed_json):
        self.temperature = parsed_json['svalue1']+'0'
        #self.print_update('External Temperature ' + self.temperature + ' degrees C')
        self.humidity = parsed_json['svalue2']+'.00'
        #self.print_update('External Humidity ' + self.humidity + '%')
        self.temp_humidity_update_time = time.time()
        
    def check_valid_readings(self, check_time):
        if check_time - self.barometer_update_time < 500:
            valid_barometer_reading = True
        else:
            valid_barometer_reading = False
        if check_time - self.temp_humidity_update_time < 500:
            valid_temp_humidity_reading = True
        else:
            valid_temp_humidity_reading = False
        return valid_temp_humidity_reading, valid_barometer_reading

    def print_update(self, message):
        today = datetime.now()
        print('')
        print(message + ' on ' + today.strftime('%A %d %B %Y @ %H:%M:%S'))
        
def log_barometer(barometer, barometer_history): # Logs 3 hours of barometer readings, taken every 20 minutes
    barometer_log_time = time.time()
    three_hour_barometer=barometer_history[8] # Capture barometer reading from 3 hours ago
    for pointer in range (8, 0, -1): # Move previous temperatures one position in the list to prepare
        # for new temperature to be recorded
        barometer_history[pointer] = barometer_history[pointer - 1]
    barometer_history[0] = barometer # Log latest reading
    if three_hour_barometer!=0:
        valid_barometer_history = True
        barometer_change = barometer - three_hour_barometer
        if barometer_change > -1.1 and barometer_change < 1.1:
            barometer_trend = '-'
        elif barometer_change <= -1.1 and barometer_change > -4:
            barometer_trend = '<'
        elif barometer_change <= -4 and barometer_change > -10:
            barometer_trend = '<<'
        elif barometer_change <= -10:
            barometer_trend = '<!'
        elif barometer_change >= 1.1 and barometer_change < 6:
            barometer_trend = '>'
        elif barometer_change >= 6 and barometer_change < 10:
            barometer_trend = '>>'
        elif barometer_change >= 10:
            barometer_trend = '>!'
        else:
            pass
        forecast, icon_forecast, domoticz_forecast, aio_forecast = analyse_barometer(barometer_change, barometer)
    else:
        valid_barometer_history=False
        forecast = 'Insufficient Data'
        icon_forecast = 'Wait'
        aio_forecast = 'question'
        domoticz_forecast = '0'
        barometer_change = 0
        barometer_trend = ''
    #print("Log Barometer")
    #print("Result", barometer_history, "Valid Barometer History is", valid_barometer_history,
    # "3 Hour Barometer Change is", round(barometer_change,2), "millibars")
    return barometer_history, barometer_change, valid_barometer_history, barometer_log_time, forecast, barometer_trend,\
           icon_forecast, domoticz_forecast, aio_forecast

def analyse_barometer(barometer_change, barometer):
    if barometer<1009:
        if barometer_change>-1.1 and barometer_change<6:
            forecast = 'Clearing and Colder'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
            aio_forecast = 'thermometer-quarter'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
            domoticz_forecast = '3'
            aio_forecast = 'w:wind-beaufort-7'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
            domoticz_forecast = '4'
            aio_forecast = 'w:wind-beaufort-9'
        elif barometer_change<=-1.1 and barometer_change>=-4:
            forecast = 'Rain and Wind'
            icon_forecast = 'Rain'
            domoticz_forecast = '4'
            aio_forecast = 'w:rain-wind'
        elif barometer_change<-4 and barometer_change>-10:
            forecast = 'Storm'
            icon_forecast = 'Storm'
            domoticz_forecast = '4'
            aio_forecast = 'w:thunderstorm'
        else:
            forecast = 'Storm and Gale'
            icon_forecast = 'Gale'
            domoticz_forecast = '4'
            aio_forecast = 'w:thunderstorm'
    elif barometer>=1009 and barometer <=1018:
        if barometer_change>-4 and barometer_change<1.1:
            forecast = 'No Change'
            icon_forecast = 'Stable'
            domoticz_forecast = '0'
            aio_forecast = 'balance-scale'
        elif barometer_change>=1.1 and barometer_change<=6 and barometer<=1015:
            forecast = 'No Change'
            icon_forecast = 'Stable'
            domoticz_forecast = '0'
            aio_forecast = 'balance-scale'
        elif barometer_change>=1.1 and barometer_change<=6 and barometer>1015:
            forecast = 'Poorer Weather'
            icon_forecast = 'Poorer'
            domoticz_forecast = '3'
            aio_forecast = 'w:cloud'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
            domoticz_forecast = '3'
            aio_forecast = 'w:wind-beaufort-7'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
            domoticz_forecast = '4'
            aio_forecast = 'w:wind-beaufort-9'
        else:
            forecast = 'Rain and Wind'
            icon_forecast = 'Rain'
            domoticz_forecast = '4'
            aio_forecast = 'w:rain-wind'
    elif barometer>1018 and barometer <=1023:
        if barometer_change>0 and barometer_change<1.1:
            forecast = 'No Change'
            icon_forecast = 'Stable'
            domoticz_forecast = '0'
            aio_forecast = 'balance-scale'
        elif barometer_change>=1.1 and barometer_change<6:
            forecast = 'Poorer Weather'
            icon_forecast = 'Poorer'
            domoticz_forecast = '3'
            aio_forecast = 'w:cloud'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
            domoticz_forecast = '3'
            aio_forecast = 'w:wind-beaufort-7'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
            domoticz_forecast = '4'
            aio_forecast = 'w:wind-beaufort-9'
        elif barometer_change>-1.1 and barometer_change<=0:
            forecast = 'Fair Weather with\nSlight Temp Change'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
            aio_forecast = 'w:day-sunny'
        elif barometer_change<=-1.1 and barometer_change>-4:
            forecast = 'No Change but\nRain in 24 Hours'
            icon_forecast = 'Stable'
            domoticz_forecast = '0'
            aio_forecast = 'balance-scale'
        else:
            forecast = 'Rain, Wind and\n Higher Temp'
            icon_forecast = 'Rain'
            domoticz_forecast = '4'
            aio_forecast = 'w:rain-wind'
    else: # barometer>1023
        if barometer_change>0 and barometer_change<1.1:
            forecast = 'Fair Weather'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
            aio_forecast = 'w:day-sunny'
        elif barometer_change>-1.1 and barometer_change<=0:
            forecast = 'Fair Weather with\nLittle Temp Change'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
            aio_forecast = 'w:day-sunny'
        elif barometer_change>=1.1 and barometer_change<6:
            forecast = 'Poorer Weather'
            icon_forecast = 'Poorer'
            domoticz_forecast = '3'
            aio_forecast = 'w:cloud'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
            domoticz_forecast = '3'
            aio_forecast = 'w:wind-beaufort-7'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
            domoticz_forecast = '4'
            aio_forecast = 'w:wind-beaufort-9'
        elif barometer_change<=-1.1 and barometer_change>-4:
            forecast = 'Fair Weather and\nSlowly Rising Temp'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
            aio_forecast = 'w:day-sunny'
        else:
            forecast = 'Warming Trend'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
            aio_forecast = 'thermometer-three-quarters'
    print('3 hour barometer change is '+str(round(barometer_change,1))+' millibars with a current reading of '+
          str(round(barometer,1))+' millibars. The weather forecast is '+forecast)
    return forecast, icon_forecast, domoticz_forecast, aio_forecast

# Icon Display Methods
def calculate_y_pos(x, centre):
    """Calculates the y-coordinate on a parabolic curve, given x."""
    centre = 80
    y = 1 / centre * (x - centre) ** 2 + sun_radius
    return int(y)
def circle_coordinates(x, y, radius):
    """Calculates the bounds of a circle, given centre and radius."""
    x1 = x - radius  # Left
    x2 = x + radius  # Right
    y1 = y - radius  # Bottom
    y2 = y + radius  # Top
    return (x1, y1, x2, y2)
def map_colour(x, centre, icon_aqi_level, day):
    """Given an x coordinate and a centre point, an aqi hue (in degrees),
       and a Boolean for day or night (day is True, night False), calculate a colour
       hue representing the 'colour' of that aqi level."""
    sat = 1.0
    # Dim the brightness as you move from the centre to the edges
    val = 0.8 - 0.6 * (abs(centre - x) / (2 * centre))
    # Select the hue based on the max aqi level and rescale between 0 and 1
    hue = icon_background_hue[icon_aqi_level]/360
    # Reverse dimming at night
    if not day:
        val = 1 - val
    #print(day, x, hue, sat, val)
    r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, sat, val)]
    return (r, g, b)
def x_from_sun_moon_time(progress, period, x_range):
    """Recalculate/rescale an amount of progress through a time period."""
    x = int((progress / period) * x_range)
    return x
def sun_moon_time(city_name, time_zone):
    """Calculate the progress through the current sun/moon period (i.e day or
       night) from the last sunrise or sunset, given a datetime object 't'."""
    city = lookup(city_name, db)
    # Datetime objects for yesterday, today, tomorrow
    utc = pytz.utc
    utc_dt = datetime.now(tz=utc)
    local_dt = utc_dt.astimezone(pytz.timezone(time_zone))
    today = local_dt.date()
    yesterday = today - timedelta(1)
    tomorrow = today + timedelta(1)
    # Sun objects for yesterday, today, tomorrow
    sun_yesterday = sun(city.observer, date=yesterday)
    sun_today = sun(city.observer, date=today)
    sun_tomorrow = sun(city.observer, date=tomorrow)
    # Work out sunset yesterday, sunrise/sunset today, and sunrise tomorrow
    sunset_yesterday = sun_yesterday["sunset"]
    sunrise_today = sun_today["sunrise"]
    sunset_today = sun_today["sunset"]
    sunrise_tomorrow = sun_tomorrow["sunrise"]
    # Work out lengths of day or night period and progress through period
    if sunrise_today < local_dt < sunset_today:
        day = True
        period = sunset_today - sunrise_today
        mid = sunrise_today + (period / 2)
        progress = local_dt - sunrise_today
    elif local_dt > sunset_today:
        day = False
        period = sunrise_tomorrow - sunset_today
        mid = sunset_today + (period / 2)
        progress = local_dt - sunset_today
    else:
        day = False
        period = sunrise_today - sunset_yesterday
        mid = sunset_yesterday + (period / 2)
        progress = local_dt - sunset_yesterday
    # Convert time deltas to seconds
    progress = progress.total_seconds()
    period = period.total_seconds()
    return (progress, period, day, local_dt)
def draw_background(progress, period, day, icon_aqi_level):
    """Given an amount of progress through the day or night, draw the
       background colour and overlay a blurred sun/moon."""
    # x-coordinate for sun
    x = x_from_sun_moon_time(progress, period, WIDTH)
    # If it's day, then move right to left
    if day:
        x = WIDTH - x
    # Calculate position on sun's curve
    centre = WIDTH / 2
    y = calculate_y_pos(x, centre)
    # Background colour
    background = map_colour(x, 80, icon_aqi_level, day)
    # New image for background colour
    img = Image.new('RGBA', (WIDTH, HEIGHT), color=background)
    draw = ImageDraw.Draw(img)
    # New image for sun overlay
    overlay = Image.new('RGBA', (WIDTH, HEIGHT), color=(0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    # Draw the sun/moon
    circle = circle_coordinates(x, y, sun_radius)
    if day:
        if icon_aqi_level != 2 or icon_aqi_level != 3: # Yellow sun if background is not yellow or orange
            overlay_draw.ellipse(circle, fill=(180, 180, 0, opacity), outline = (0, 0, 0))
        else: # Red Sun to have contrast against yellow or orange background
            overlay_draw.ellipse(circle, fill=(180, 0, 0, opacity), outline = (0, 0, 0))
    # Overlay the sun on the background
    composite = Image.alpha_composite(img, overlay).filter(ImageFilter.GaussianBlur(radius=blur))
    return composite
def overlay_text(img, position, text, font, align_right=False, rectangle=False):
    draw = ImageDraw.Draw(img)
    w, h = font.getsize(text)
    if align_right:
        x, y = position
        x -= w
        position = (x, y)
    if rectangle:
        x += 1
        y += 1
        position = (x, y)
        border = 1
        rect = (x - border, y, x + w, y + h + border)
        rect_img = Image.new('RGBA', (WIDTH, HEIGHT), color=(0, 0, 0, 0))
        rect_draw = ImageDraw.Draw(rect_img)
        rect_draw.rectangle(rect, (255, 255, 255))
        rect_draw.text(position, text, font=font, fill=(0, 0, 0, 0))
        img = Image.alpha_composite(img, rect_img)
    else:
        draw.text(position, text, font=font, fill=(255, 255, 255))
    return img

def describe_humidity(humidity):
    """Convert relative humidity into wet/good/dry description."""
    if 30 < humidity <= 75:
        description = "good"
    elif humidity > 75:
        description = "wet"
    else:
        description = "dry"
    return description

def describe_dewpoint(dp):
    """Convert dewpoint reading to comfort level"""
    if dp <= 10:
        description = "dry"
    elif dp > 10 and dp <= 20:
        description = "good"
    else:
        description = "wet"
    return description

def display_icon_weather_aqi(location, data, barometer_trend, icon_forecast, maxi_temp, mini_temp, air_quality_data,
                             air_quality_data_no_gas, icon_air_quality_levels, gas_sensors_warm, noise_level, noise_max):
    progress, period, day, local_dt = sun_moon_time(city_name, time_zone)
    # Calculate AQI
    max_aqi = max_aqi_level_factor(gas_sensors_warm, air_quality_data, air_quality_data_no_gas, data)
    # Background
    background = draw_background(progress, period, day, max_aqi[1])
    # Time.
    date_string = local_dt.strftime("%d %b %y").lstrip('0')
    time_string = local_dt.strftime("%H:%M") + '  ' + location
    img = overlay_text(background, (0 + margin, 0 + margin), time_string, font_smm)
    img = overlay_text(img, (WIDTH - margin, 0 + margin), date_string, font_smm, align_right=True)
    temp_string = f"{data['Temp'][1]:.1f}°C"
    img = overlay_text(img, (78, 18), temp_string, font_smm, align_right=True)
    spacing = font_smm.getsize(temp_string)[1] + 1
    if mini_temp is not None and maxi_temp is not None:
        if maxi_temp >= 0:
            range_string = f"{round(mini_temp, 0):.0f} to {round(maxi_temp, 0):.0f}"
        else:
            range_string = f"{round(mini_temp, 0):.0f} to{round(maxi_temp, 0):.0f}"
    else:
        range_string = "------"
    img = overlay_text(img, (78, 18 + spacing), range_string, font_sm, align_right=True, rectangle=True)
    temp_icon = Image.open(path + "/icons/temperature.png")
    img.paste(temp_icon, (margin, 23), mask=temp_icon)
    # Humidity
    corr_humidity = data["Hum"][1]
    humidity_string = f"{corr_humidity:.1f}%"
    img = overlay_text(img, (73, 48), humidity_string, font_smm, align_right=True)
    # Dewpoint
    spacing = font_smm.getsize(humidity_string)[1] + 1
    dewpoint_data = data["Dew"][1]
    dewpoint_string = f"{dewpoint_data:.1f}°C"
    comfort_desc = describe_dewpoint(data["Dew"][1]).upper()
    img = overlay_text(img, (68, 48 + spacing), dewpoint_string, font_sm, align_right=True, rectangle=True)
    comfort_icon = Image.open(path + "/icons/humidity-" + comfort_desc.lower() + ".png")
    img.paste(comfort_icon, (margin, 53), mask=comfort_icon)
    # AQI
    aqi_string = f"{max_aqi[1]}: {max_aqi[0]}"
    img = overlay_text(img, (WIDTH - margin, 18), aqi_string, font_smm, align_right=True)
    spacing = font_smm.getsize(aqi_string)[1] + 1
    aqi_desc = icon_air_quality_levels[max_aqi[1]].upper()
    img = overlay_text(img, (WIDTH - margin - 1, 18 + spacing), aqi_desc, font_sm, align_right=True, rectangle=True)
    aqi_icon = Image.open(path + "/icons/aqi.png")
    img.paste(aqi_icon, (85, 23), mask=aqi_icon)
    # Pressure
    pressure = data["Bar"][1]
    pressure_string = f"{int(pressure)} {barometer_trend}"
    img = overlay_text(img, (WIDTH - margin, 48), pressure_string, font_smm, align_right=True)
    pressure_desc = icon_forecast.upper()
    spacing = font_smm.getsize(pressure_string)[1] + 1
    img = overlay_text(img, (WIDTH - margin - 1, 48 + spacing), pressure_desc, font_sm, align_right=True, rectangle=True)
    pressure_icon = Image.open(path + "/icons/weather-" + pressure_desc.lower() +  ".png")
    img.paste(pressure_icon, (80, 53), mask=pressure_icon)
    # Noise Level
    if enable_noise:
        if noise_level<=noise_thresholds[0]:
            noise_colour = (0, 255, 0)
        elif noise_thresholds[0]<noise_level<=noise_thresholds[1]:
            noise_colour=(255, 255, 0)
        else:
            noise_colour = (255, 0, 0)
        if noise_level != 0:
            draw = ImageDraw.Draw(img)
            draw.line((0, HEIGHT, 0, HEIGHT - (noise_level-35)), fill=noise_colour, width=5)
            if noise_max<=noise_thresholds[0]:
                max_spl_colour = (0, 255, 0)
            elif noise_thresholds[0]<noise_max<=noise_thresholds[1]:
                max_spl_colour=(255, 255, 0)
            else:
                max_spl_colour = (255, 0, 0)
            draw.line((0, HEIGHT - (noise_max-35), 4, HEIGHT - (noise_max-35)), fill=max_spl_colour, width=2) #Display Max Noise Level Line
    # Display image
    disp.display(img)
    
# Send Adafruit IO Feed Data
def update_aio(mqtt_values, forecast, aio_format, aio_forecast_text_format,
               aio_air_quality_level_format, aio_air_quality_text_format, own_data, icon_air_quality_levels,
               aio_package, gas_sensors_warm, air_quality_data, air_quality_data_no_gas,
               aio_noise_values, aio_version_text_format, version_text):
    aio_resp = False # Set to True when there is at least one successful aio feed response
    aio_json = {}
    aio_path = '/feeds/'
    if gas_sensors_warm and (aio_package == "Premium" or aio_package == "Premium Plus" or aio_package == "Premium Noise" or aio_package == "Premium Plus Noise"):
        print("Sending", aio_package, "feeds to Adafruit IO with Gas Data")
    elif gas_sensors_warm == False and (aio_package == "Premium" or aio_package == "Premium Plus" or aio_package == "Premium Noise" or aio_package == "Premium Plus Noise"):
        print("Sending", aio_package, "feeds to Adafruit IO without Gas Data")
    else:
        print("Sending", aio_package, "package feeds to Adafruit IO")
    # Analyse air quality levels and combine into an overall air quality level based on own_data thesholds
    max_aqi = max_aqi_level_factor(gas_sensors_warm, air_quality_data, air_quality_data_no_gas, own_data)
    combined_air_quality_level_factor = max_aqi[0]
    combined_air_quality_level = max_aqi[1]
    combined_air_quality_text = icon_air_quality_levels[combined_air_quality_level] + ": " +\
                                combined_air_quality_level_factor
    #print('Sending Air Quality Level Feed')
    aio_json['value'] = combined_air_quality_level
    feed_resp = send_data_to_aio(aio_air_quality_level_format, combined_air_quality_level) # Used by all aio packages
    if feed_resp:
        aio_resp = True
    if (aio_package == 'Premium Plus' or aio_package == 'Premium' or aio_package == 'Basic Air' or aio_package == "Premium Noise" or aio_package == "Premium Plus Noise"):
        #print('Sending Air Quality Text Feed')
        feed_resp = send_data_to_aio(aio_air_quality_text_format, combined_air_quality_text)
        if feed_resp:
            aio_resp = True
    if not enable_indoor_outdoor_functionality or enable_indoor_outdoor_functionality and\
            indoor_outdoor_function == "Outdoor" or enable_indoor_outdoor_functionality and\
            indoor_outdoor_function == "Indoor" and outdoor_source_type != "Enviro":
        # If indoor_outdoor_functionality is enabled, only send an updated weather forecast from the outdoor unit
        # unless the outdoor source type in not an Enviro Monitor
        aio_forecast_text = forecast.replace("\n", " ")
        if (aio_package == 'Premium' or aio_package == 'Premium Plus' or aio_package == "Premium Noise" or aio_package == "Premium Plus Noise"):
            #print('Sending Weather Forecast Text Feed')
            feed_resp = send_data_to_aio(aio_forecast_text_format, aio_forecast_text)
            if feed_resp:
                aio_resp = True
    if (aio_package == 'Premium' or aio_package == 'Premium Plus' or aio_package == "Premium Noise" or aio_package == "Premium Plus Noise"):
        #print('Sending Version Text Feed')
        feed_resp = send_data_to_aio(aio_version_text_format, version_text)
        if feed_resp:
            aio_resp = True
    # Send other feeds
    for feed in aio_format: # aio_format varies, based on the relevant aio_package
        if aio_format[feed][1]: # Send the first value of the list if sending humidity or barometer data
            if (feed == "Hum" or
                feed == "Bar" and not enable_indoor_outdoor_functionality or
                feed == "Bar" and enable_indoor_outdoor_functionality and indoor_outdoor_function == "Outdoor" or
                feed == "Bar" and enable_indoor_outdoor_functionality and indoor_outdoor_function == "Indoor" and
                outdoor_source_type != "Enviro"):
                # If indoor_outdoor_functionality is enabled, only send outdoor barometer feed unless
                # the outdoor source type in not an Enviro Monitor
                #print('Sending', feed, 'Feed')
                feed_resp = send_data_to_aio(aio_format[feed][0], mqtt_values[feed][0])
                if feed_resp:
                    aio_resp = True
        elif feed == "Max Noise":
            aio_noise_max = round(max(aio_noise_values), 1)
            #print('Sending', feed, 'Feed')
            feed_resp = send_data_to_aio(aio_format[feed][0], aio_noise_max)
            if feed_resp:
                aio_resp = True
        elif feed == "Min Noise":
            aio_noise_min = round(min(aio_noise_values), 1)
            #print('Sending', feed, 'Feed')
            feed_resp = send_data_to_aio(aio_format[feed][0], aio_noise_min)
            if feed_resp:
                aio_resp = True
        elif feed == "Mean Noise":
            aio_noise_mean = round(sum(aio_noise_values)/len(aio_noise_values), 1)
            #print('Sending', feed, 'Feed')
            feed_resp = send_data_to_aio(aio_format[feed][0], aio_noise_mean)
            if feed_resp:
                aio_resp = True       
        else: # Send the value if sending data other than noise, humidity or barometer
            # Only send gas data if the gas sensors are warm and calibrated
            if (feed != "Red" and feed != "Oxi" and feed != "NH3") or mqtt_values['Gas Calibrated']:
                #print('Sending', feed, 'Feed')
                feed_resp = send_data_to_aio(aio_format[feed][0], mqtt_values[feed])
                if feed_resp:
                    aio_resp = True
    return aio_resp


def capture_external_outdoor_data(outdoor_source_type, outdoor_source_id, outdoor_aio_readings):
    external_outdoor_data = {}
    if outdoor_source_type == "Adafruit IO":
        for aio_feed in outdoor_aio_readings:
            aio_error = False
            url = 'https://io.adafruit.com/api/v2/{}/feeds/{}-outdoor{}/data/last'.format(
                outdoor_source_id["User Name"], outdoor_source_id["Household Name"], outdoor_aio_readings[aio_feed])
            #print (url)
            try:
                outdoor_aio_data = external_outdoor_data_session.get(url, headers={'X-AIO-Key':
                                                                                       outdoor_source_id["Key"]},
                                                                     timeout=5).json()
                #print(outdoor_aio_data)
            except requests.exceptions.ConnectionError as outdoor_aio_comms_error:
                aio_error = True
                print('Outdoor aio Connection Error', outdoor_aio_comms_error)
            except requests.exceptions.Timeout as outdoor_aio_comms_error:
                aio_error = True
                print('Outdoor aio Timeout Error', outdoor_aio_comms_error)
            except requests.exceptions.RequestException as outdoor_aio_comms_error:
                aio_error = True
                print('Outdoor aio Request Error', outdoor_aio_comms_error)
            except ValueError as outdoor_aio_comms_error:
                aio_error = True
                print('Outdoor aio Value Error', outdoor_aio_comms_error)
            if not aio_error:
                if "value" in outdoor_aio_data:
                    external_outdoor_data[aio_feed] = float(outdoor_aio_data["value"])
    elif outdoor_source_type == 'Luftdaten':
        urls = {"Climate": 'http://api.luftdaten.info/v1/sensor/{}/'.format(outdoor_source_id["Climate"]),
                "PM": 'http://api.luftdaten.info/v1/sensor/{}/'.format(outdoor_source_id["PM"])}
        for url in urls:
            luft_error = False
            try:
                outdoor_luft_data = external_outdoor_data_session.get(urls[url], timeout=5).json()
                #print(outdoor_luft_data)
            except requests.exceptions.ConnectionError as outdoor_comms_error:
                luft_error = True
                print('Outdoor Luftdaten Connection Error', outdoor_comms_error)
            except requests.exceptions.Timeout as outdoor_comms_error:
                luft_error = True
                print('Outdoor Luftdaten Timeout Error', outdoor_comms_error)
            except requests.exceptions.RequestException as outdoor_comms_error:
                luft_error = True
                print('Outdoor Luftdaten Request Error', outdoor_comms_error)
            except ValueError as outdoor_comms_error:
                luft_error = True
                print('Outdoor Luftdaten Value Error', outdoor_comms_error)
            if not luft_error:
                if "sensordatavalues" in outdoor_luft_data[0]:
                    for i in range(len(outdoor_luft_data[0]["sensordatavalues"])):
                        if url == "Climate":
                            if outdoor_luft_data[0]["sensordatavalues"][i]["value_type"] == "temperature":
                                external_outdoor_data["Temp"] = float(outdoor_luft_data[0]
                                                                      ["sensordatavalues"][i]["value"])
                            elif outdoor_luft_data[0]["sensordatavalues"][i]["value_type"] == "humidity":
                                external_outdoor_data["Hum"] = float(outdoor_luft_data[0]
                                                                     ["sensordatavalues"][i]["value"])
                        elif url == "PM":
                            if outdoor_luft_data[0]["sensordatavalues"][i]["value_type"] == "P2":
                                external_outdoor_data["P2.5"] = float(outdoor_luft_data[0]
                                                                      ["sensordatavalues"][i]["value"])
                            elif outdoor_luft_data[0]["sensordatavalues"][i]["value_type"] == "P1":
                                external_outdoor_data["P10"] = float(outdoor_luft_data[0]
                                                                     ["sensordatavalues"][i]["value"])
    return external_outdoor_data
        
def process_noise_frames(captured_recording, frames, time, status):
    global recording
    global noise_sample_counter
    recording = captured_recording
    noise_sample_counter += 1
      
def ABC_weighting(curve='A'):
    """
    Design of an analog weighting filter with A, B, or C curve.
    Returns zeros, poles, gain of the filter.
    """
    if curve not in 'ABC':
        raise ValueError('Curve type not understood')

    # ANSI S1.4-1983 C weighting
    #    2 poles on the real axis at "20.6 Hz" HPF
    #    2 poles on the real axis at "12.2 kHz" LPF
    #    -3 dB down points at "10^1.5 (or 31.62) Hz"
    #                         "10^3.9 (or 7943) Hz"
    #
    # IEC 61672 specifies "10^1.5 Hz" and "10^3.9 Hz" points and formulas for
    # derivation.  See _derive_coefficients()

    z = [0, 0]
    p = [-2*pi*20.598997057568145,
         -2*pi*20.598997057568145,
         -2*pi*12194.21714799801,
         -2*pi*12194.21714799801]
    k = 1

    if curve == 'A':
        # ANSI S1.4-1983 A weighting =
        #    Same as C weighting +
        #    2 poles on real axis at "107.7 and 737.9 Hz"
        #
        # IEC 61672 specifies cutoff of "10^2.45 Hz" and formulas for
        # derivation.  See _derive_coefficients()

        p.append(-2*pi*107.65264864304628)
        p.append(-2*pi*737.8622307362899)
        z.append(0)
        z.append(0)

    elif curve == 'B':
        # ANSI S1.4-1983 B weighting
        #    Same as C weighting +
        #    1 pole on real axis at "10^2.2 (or 158.5) Hz"

        p.append(-2*pi*10**2.2)  # exact
        z.append(0)
    b, a = zpk2tf(z, p, k)
    k /= abs(freqs(b, a, [2*pi*1000])[1][0])

    return np.array(z), np.array(p), k



def A_weighting(fs, output='ba'):
    """
    Design of a digital A-weighting filter.
    Designs a digital A-weighting filter for
    sampling frequency `fs`.
    Warning: fs should normally be higher than 20 kHz. For example,
    fs = 48000 yields a class 1-compliant filter.
    Parameters
    ----------
    fs : float
        Sampling frequency
    output : {'ba', 'zpk', 'sos'}, optional
        Type of output:  numerator/denominator ('ba'), pole-zero ('zpk'), or
        second-order sections ('sos'). Default is 'ba'.
    Since this uses the bilinear transform, frequency response around fs/2 will
    be inaccurate at lower sampling rates.
    """
    z, p, k = ABC_weighting('A')

    # Use the bilinear transformation to get the digital filter.
    z_d, p_d, k_d = _zpkbilinear(z, p, k, fs)

    if output == 'zpk':
        return z_d, p_d, k_d
    elif output in {'ba', 'tf'}:
        return zpk2tf(z_d, p_d, k_d)
    elif output == 'sos':
        return zpk2sos(z_d, p_d, k_d)
    else:
        raise ValueError("'%s' is not a valid output form." % output)

def A_weight(signal, fs):
    sos = A_weighting(fs, output='sos')
    return sosfilt(sos, signal)

def get_rms_at_frequency_ranges(recording, ranges, noise_sample_rate):
    """Return the RMS levels of frequencies in the given ranges.

    :param ranges: List of ranges including a start and end range

    """
    magnitude = np.square(np.abs(np.fft.rfft(recording[:, 0], n=noise_sample_rate)))
    result = []
    for r in ranges:
        start, end = r
        result.append(np.sqrt(np.mean(magnitude[start:end])))
    return result

class NullContextManager(object): # Dummy context manager that's used when noise is disabled
    def __init__(self, dummy_resource=None):
        self.dummy_resource = dummy_resource
    def __enter__(self):
        return self.dummy_resource
    def __exit__(self, *args):
        pass

# Display setup
delay = 0.5 # Debounce the proximity tap when choosing the data to be displayed
mode = 0 # The starting mode for the data display
last_page = 0
light = 1
# Width and height to calculate text position
WIDTH = disp.width
HEIGHT = disp.height
# The position of the top bar
top_pos = 25
# Set up canvas and fonts
img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
draw = ImageDraw.Draw(img)
x_offset = 2
y_offset = 2
# Set up fonts
font_size_small = 10
font_size_sm = 12
font_size_smm = 14
font_size_medium = 16
font_size_ml = 18
font_size_large = 20
smallfont = ImageFont.truetype(UserFont, font_size_small)
font_sm = ImageFont.truetype(UserFont, font_size_sm)
font_smm = ImageFont.truetype(UserFont, font_size_smm)
mediumfont = ImageFont.truetype(UserFont, font_size_medium)
font_ml = ImageFont.truetype(UserFont, font_size_ml)
largefont = ImageFont.truetype(UserFont, font_size_large)
message = ""

# Set up icon display
# Set up air quality levels for icon display
icon_air_quality_levels = ['Great', 'OK', 'Alert', 'Poor', 'Bad']
# Values that alter the look of the background
blur = 5
opacity = 255
icon_background_hue = [240, 120, 60, 39, 0]
sun_radius = 20
# Margins
margin = 3

# Create own_data dict to store the data to be displayed in Display Everything
# Format: {Display Item: [Units, Current Value, [Level Thresholds], display_all_aq position]}
if enable_eco2_tvoc: # eCO2 and TVOC added when enabling the SGP30 sensor
    own_data = {"P1": ["ug/m3", 0, [6,17,27,35], 0], "P2.5": ["ug/m3", 0, [11,35,53,70], 1],
                "P10": ["ug/m3", 0, [16,50,75,100], 2], "Oxi": ["ppm", 0, [0.2, 0.4, 0.8, 1], 3],
                "Red": ["ppm", 0, [6, 10, 50, 75], 4], "NH3": ["ppm", 0, [1, 2, 10, 15], 5],
                "CO2": ["ppm", 0, [500, 1000, 1600, 2000], 6], "VOC": ["ppb", 0, [120, 220, 660, 2200], 7],
                "Temp": ["C", 0, [10,18,25,32], 8], "Hum": ["%", 0, [30,50,75,90], 9],
                "Dew": ["C", 0, [10,15,20,24], 10], "Bar": ["hPa", 0, [980,990,1030,1040], 11],
                "Lux": ["Lux", 1, [100,1000,12000,30000], 12]}
    data_in_display_all_aq =  ["P1", "P2.5", "P10", "Oxi", "Red", "NH3", "CO2", "VOC"]
    # Defines the order in which display modes are chosen
    if enable_noise:
        display_modes = ["Icon Weather", "All Air", "P1", "P2.5", "P10", "Oxi", "Red", "NH3", "CO2", "VOC",
                     "Forecast", "Temp", "Hum", "Dew", "Bar", "Lux", "Noise Reading", "Noise Level", "Noise Frequencies", "Status"]
    else:
        display_modes = ["Icon Weather", "All Air", "P1", "P2.5", "P10", "Oxi", "Red", "NH3", "CO2", "VOC",
                     "Forecast", "Temp", "Hum", "Dew", "Bar", "Lux", "Status"]
else:
    own_data = {"P1": ["ug/m3", 0, [6,17,27,35], 0], "P2.5": ["ug/m3", 0, [11,35,53,70], 1],
                "P10": ["ug/m3", 0, [16,50,75,100], 2], "Oxi": ["ppm", 0, [0.2, 0.4, 0.8, 1], 3],
                "Red": ["ppm", 0, [6, 10, 50, 75], 4], "NH3": ["ppm", 0, [1, 2, 10, 15], 5],
                "Temp": ["C", 0, [10,18,25,32], 6], "Hum": ["%", 0, [30,50,75,90], 7],
                "Dew": ["C", 0, [10,15,20,24], 8], "Bar": ["hPa", 0, [980,990,1030,1040], 9],
                "Lux": ["Lux", 1, [100,1000,12000,30000], 10]}
    data_in_display_all_aq =  ["P1", "P2.5", "P10", "Oxi", "Red", "NH3"]
    # Defines the order in which display modes are chosen
    if enable_noise:
        display_modes = ["Icon Weather", "All Air", "P1", "P2.5", "P10", "Oxi", "Red", "NH3", "Forecast", "Temp", "Hum",
                     "Dew", "Bar", "Lux", "Noise Reading", "Noise Level", "Noise Frequencies", "Status"]
    else:
        display_modes = ["Icon Weather", "All Air", "P1", "P2.5", "P10", "Oxi", "Red", "NH3", "CO2", "VOC",
                     "Forecast", "Temp", "Hum", "Dew", "Bar", "Lux", "Status"]

# Set up display graph data
own_disp_values = {}
for v in own_data:
    own_disp_values[v] = [[1, 0]] * int(WIDTH/2)
                   
if enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor': # Prepare outdoor data, if it's required
    captured_outdoor_data = {}
    if enable_eco2_tvoc:
        outdoor_data = {"P1": ["ug/m3", 0, [6,17,27,35], 0], "P2.5": ["ug/m3", 0, [11,35,53,70], 1],
                        "P10": ["ug/m3", 0, [16,50,75,100], 2], "Oxi": ["ppm", 0, [0.2, 0.4, 0.8, 1], 3],
                        "Red": ["ppm", 0, [6, 10, 50, 75], 4], "NH3": ["ppm", 0, [1, 2, 10, 15], 5],
                        "CO2": ["ppm", 0, [500, 1000, 1600, 2000], 6], "VOC": ["ppb", 0, [120, 220, 660, 2200], 7],
                        "Temp": ["C", 0, [10,18,25,32], 8], "Hum": ["%", 0, [30,50,75,90], 9],
                        "Dew": ["C", 0, [10,15,20,24], 10], "Bar": ["hPa", 0, [980,990,1030,1040], 10],
                        "Lux": ["Lux", 1, [100,1000,12000,30000], 11]}
    else:
        outdoor_data = {"P1": ["ug/m3", 0, [6,17,27,35], 0], "P2.5": ["ug/m3", 0, [11,35,53,70], 1],
                        "P10": ["ug/m3", 0, [16,50,75,100], 2], "Oxi": ["ppm", 0, [0.2, 0.4, 0.8, 1], 3],
                        "Red": ["ppm", 0, [6, 10, 50, 75], 4], "NH3": ["ppm", 0, [1, 2, 10, 15], 5],
                        "Temp": ["C", 0, [10,18,25,32], 6], "Hum": ["%", 0, [30,50,75,90], 7],
                        "Dew": ["C", 0, [10,15,20,24], 10], "Bar": ["hPa", 0, [980,990,1030,1040], 8],
                        "Lux": ["Lux", 1, [100,1000,12000,30000], 9]}
    # For graphing outdoor display data
    outdoor_disp_values = {}
    for v in outdoor_data:
        outdoor_disp_values[v] = [[1, 0]] * int(WIDTH/2)
else:
    outdoor_data = {}
    outdoor_disp_values = {}

# Used to define air quality level components and their priority for the icon display,
# Adafruit IO and the disabled display mode.
if enable_eco2_tvoc:
    air_quality_data = ["P1", "P2.5", "CO2", "VOC", "P10", "Oxi", "Red", "NH3"]
    air_quality_data_no_gas = ["P1", "P2.5", "CO2", "VOC", "P10"]
else:
    air_quality_data = ["P1", "P2.5", "P10", "Oxi", "Red", "NH3"]
    air_quality_data_no_gas = ["P1", "P2.5", "P10"]
current_display_is_own = True # Start with own display
start_current_display = time.time()
indoor_outdoor_display_duration = 5 # Seconds for duration of indoor or outdoor display
outdoor_reading_captured = False # Used to determine whether the outdoor display is ready
outdoor_reading_captured_time = 0 # Used to determine the last time that an mqtt message was received from
# the outdoor sensor

# Define your own threshold limits for Display Everything
# The limits definition follows the order of the variables array
# Example limits explanation for temperature:
# [4,18,28,35] means
# [-273.15 .. 4] -> Very Low
# (4 .. 18]   -> Low
# (18 .. 28]     -> Moderate
# (28 .. 35]     -> High
# (35 .. MAX]   -> Very High
# DISCLAIMER: The limits provided here are just examples and come
# with NO WARRANTY. The authors of this example code claim
# NO RESPONSIBILITY if reliance on the following values or this
# code in general leads to ANY DAMAGES or DEATH.

# RGB palette for values on the combined screen
palette = [(128,128,255),   # Very Low
           (0,255,0),       # Low
           (255,255,0),     # Moderate
           (255,165,0),     # High
           (255,0,0)]       # Very High
     
# Compensation factors for temperature, humidity and air pressure
if enable_display and not enable_eco2_tvoc: # Set temp and hum compensation when display is enabled (no weather
    # protection cover in place) and no ECO2 or TVOC sensor is in place
    # Cubic polynomial temp comp coefficients adjusted by config's temp_offset
    comp_temp_cub_a = -0.0001
    comp_temp_cub_b = 0.0037
    comp_temp_cub_c = 1.00568
    comp_temp_cub_d = -6.78291
    comp_temp_cub_d = comp_temp_cub_d + temp_offset
    # Quadratic polynomial hum comp coefficients
    comp_hum_quad_a = -0.0032
    comp_hum_quad_b = 1.6931
    comp_hum_quad_c = 0.9391
elif enable_display and enable_eco2_tvoc: # Set temp and hum compensation when display is enabled (no weather
    # protection cover in place) and ECO2 or TVOC sensor is in place
    comp_temp_cub_a = -0.00005
    comp_temp_cub_b = 0.00563
    comp_temp_cub_c = 0.76548
    comp_temp_cub_d = -5.2795
    comp_temp_cub_d = comp_temp_cub_d + temp_offset
    # Quadratic polynomial hum comp coefficients
    comp_hum_quad_a = -0.0047
    comp_hum_quad_b = 2.1582
    comp_hum_quad_c = -3.8446
else: # Set temp and hum compensation when display is disabled (weather protection cover in place)
    # Cubic polynomial temp comp coefficients adjusted by config's temp_offset
    comp_temp_cub_a = 0.00033
    comp_temp_cub_b = -0.03129
    comp_temp_cub_c = 1.8736
    comp_temp_cub_d = -14.82131
    comp_temp_cub_d = comp_temp_cub_d + temp_offset
    # Quadratic polynomial hum comp coefficients
    comp_hum_quad_a = -0.0221
    comp_hum_quad_b = 3.3824
    comp_hum_quad_c = -25.8102

# New Gas Comp Factors based on long term regression testing and proportion of RS
red_temp_comp_factor = -0.015
red_hum_comp_factor = 0.0125
red_bar_comp_factor = -0.0053
oxi_temp_comp_factor = -0.017
oxi_hum_comp_factor = 0.0115
oxi_bar_comp_factor = -0.0072
nh3_temp_comp_factor = -0.02695
nh3_hum_comp_factor = 0.0094
nh3_bar_comp_factor = 0.003254

luft_values = {} # To be sent to Luftdaten
mqtt_values = {} # To be sent to Home Manager, outdoor to indoor unit communications and used for the Adafruit IO Feeds
data_sent_to_luftdaten_or_aio = False # Used to flag that the main loop delay is not required when data is sent to
# Luftdaten or Adafruit IO
maxi_temp = None
mini_temp = None
# When using an external outdoor sensor via Luftdaten or Adafruit IO
outdoor_maxi_temp = None
outdoor_mini_temp = None

# Raspberry Pi ID to send to Luftdaten
id = "raspi-" + get_serial_number()

# Print Raspberry Pi serial and Wi-Fi status
logging.info("Raspberry Pi serial: {}".format(get_serial_number()))
logging.info("Wi-Fi: {}\n".format("connected" if check_wifi() else "disconnected"))

# Set up mqtt if required
if enable_send_data_to_homemanager or enable_receive_data_from_homemanager or (enable_indoor_outdoor_functionality and
        outdoor_source_type == 'Enviro'):
    es = ExternalSensors()
    client = mqtt.Client(mqtt_client_name)
    client.on_connect = on_connect
    client.on_message = on_message
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)
    try:
        client.connect(mqtt_broker_name, 1883, 60)
    except:
        print('No mqtt Broker Connection')   
    client.loop_start()
  
if enable_adafruit_io:
    # Set up Adafruit IO. aio_format{'measurement':[feed, is value in list format?]}
    # Barometer and Weather Forecast Feeds only have one feed per household (i.e. no location prefix)
    # Six aio_packages: Basic Air (Air Quality Level, Air Quality Text, PM1,  PM2.5, PM10), Basic Combo
    # (Air Quality Level, Temp, Hum, Dewpoint, Bar Feeds), Premium (All Feeds except Noise, eCO2 and TVOC)
    # Premium Plus (All Feeds except Noise), Premium Noise (All Feeds eCO2 and TVOC)
    # Premium Plus Noise(All Feeds)
    print('Setting up', aio_package, 'Adafruit IO')
    aio_url = "https://io.adafruit.com/api/v2/" + aio_user_name
    aio_feed_prefix = aio_household_prefix + '-' + aio_location_prefix
    aio_format = {}
    aio_forecast_text_format = None
    #aio_forecast_icon_format = None
    aio_air_quality_level_format = None
    aio_air_quality_text_format = None
    if aio_package == "Premium":
        aio_format = {'Temp': [aio_feed_prefix + "-temperature", False], 'Hum': [aio_feed_prefix + "-humidity", True],
                      'Dew': [aio_feed_prefix + "-dewpoint", False], 'Bar': [aio_household_prefix + "-barometer", True], 'Lux': [aio_feed_prefix + "-lux", False],
                      'P1': [aio_feed_prefix + "-pm1", False],'P2.5': [aio_feed_prefix + "-pm2-dot-5", False],
                      'P10': [aio_feed_prefix + "-pm10", False], 'Red': [aio_feed_prefix + "-reducing", False],
                      'Oxi': [aio_feed_prefix + "-oxidising", False], 'NH3': [aio_feed_prefix + "-ammonia", False]}
        aio_forecast_text_format = aio_household_prefix + "-weather-forecast-text"
        #aio_forecast_icon_format = aio_household_prefix + "-weather-forecast-icon"
        aio_air_quality_level_format = aio_feed_prefix + "-air-quality-level"
        aio_air_quality_text_format = aio_feed_prefix + "-air-quality-text"
        aio_version_text_format = aio_feed_prefix + "-version"
    elif aio_package == "Premium Noise" and enable_noise:
        aio_format = {'Temp': [aio_feed_prefix + "-temperature", False], 'Hum': [aio_feed_prefix + "-humidity", True],
                      'Dew': [aio_feed_prefix + "-dewpoint", False], 'Bar': [aio_household_prefix + "-barometer", True], 'Lux': [aio_feed_prefix + "-lux", False],
                      'P1': [aio_feed_prefix + "-pm1", False],'P2.5': [aio_feed_prefix + "-pm2-dot-5", False],
                      'P10': [aio_feed_prefix + "-pm10", False], 'Red': [aio_feed_prefix + "-reducing", False],
                      'Oxi': [aio_feed_prefix + "-oxidising", False], 'NH3': [aio_feed_prefix + "-ammonia", False],
                      'Mean Noise': [aio_feed_prefix + "-mean-noise", False], 'Max Noise': [aio_feed_prefix + "-max-noise", False],
                      'Min Noise': [aio_feed_prefix + "-min-noise", False]}
        aio_forecast_text_format = aio_household_prefix + "-weather-forecast-text"
        aio_air_quality_level_format = aio_feed_prefix + "-air-quality-level"
        aio_air_quality_text_format = aio_feed_prefix + "-air-quality-text"
        aio_version_text_format = aio_feed_prefix + "-version"
    elif aio_package == "Premium Plus" and enable_eco2_tvoc:
        aio_format = {'Temp': [aio_feed_prefix + "-temperature", False], 'Hum': [aio_feed_prefix + "-humidity", True],
                      'Dew': [aio_feed_prefix + "-dewpoint", False], 'Bar': [aio_household_prefix + "-barometer", True], 'Lux': [aio_feed_prefix + "-lux", False],
                      'P1': [aio_feed_prefix + "-pm1", False],'P2.5': [aio_feed_prefix + "-pm2-dot-5", False],
                      'P10': [aio_feed_prefix + "-pm10", False], 'Red': [aio_feed_prefix + "-reducing", False],
                      'Oxi': [aio_feed_prefix + "-oxidising", False], 'NH3': [aio_feed_prefix + "-ammonia", False],
                      'CO2': [aio_feed_prefix + "-carbon-dioxide", False], 'VOC': [aio_feed_prefix + "-tvoc", False]}
        aio_forecast_text_format = aio_household_prefix + "-weather-forecast-text"
        #aio_forecast_icon_format = aio_household_prefix + "-weather-forecast-icon"
        aio_air_quality_level_format = aio_feed_prefix + "-air-quality-level"
        aio_air_quality_text_format = aio_feed_prefix + "-air-quality-text"
        aio_version_text_format = aio_feed_prefix + "-version"
    elif aio_package == "Premium Plus Noise" and enable_eco2_tvoc and enable_noise:
        aio_format = {'Temp': [aio_feed_prefix + "-temperature", False], 'Hum': [aio_feed_prefix + "-humidity", True],
                      'Dew': [aio_feed_prefix + "-dewpoint", False], 'Bar': [aio_household_prefix + "-barometer", True], 'Lux': [aio_feed_prefix + "-lux", False],
                      'P1': [aio_feed_prefix + "-pm1", False],'P2.5': [aio_feed_prefix + "-pm2-dot-5", False],
                      'P10': [aio_feed_prefix + "-pm10", False], 'Red': [aio_feed_prefix + "-reducing", False],
                      'Oxi': [aio_feed_prefix + "-oxidising", False], 'NH3': [aio_feed_prefix + "-ammonia", False],
                      'CO2': [aio_feed_prefix + "-carbon-dioxide", False], 'VOC': [aio_feed_prefix + "-tvoc", False],
                      'Mean Noise': [aio_feed_prefix + "-mean-noise", False], 'Max Noise': [aio_feed_prefix + "-max-noise", False],
                      'Min Noise': [aio_feed_prefix + "-min-noise", False]}
        aio_forecast_text_format = aio_household_prefix + "-weather-forecast-text"
        #aio_forecast_icon_format = aio_household_prefix + "-weather-forecast-icon"
        aio_air_quality_level_format = aio_feed_prefix + "-air-quality-level"
        aio_air_quality_text_format = aio_feed_prefix + "-air-quality-text"
        aio_version_text_format = aio_feed_prefix + "-version"
    elif aio_package == "Basic Air":
        aio_format = {'P1': [aio_feed_prefix + "-pm1", False],'P2.5': [aio_feed_prefix + "-pm2-dot-5", False],
                      'P10': [aio_feed_prefix + "-pm10", False]}
        aio_air_quality_level_format = aio_feed_prefix + "-air-quality-level"
        aio_air_quality_text_format = aio_feed_prefix + "-air-quality-text"
    elif aio_package == "Basic Combo":
        aio_format = {'Temp': [aio_feed_prefix + "-temperature", False], 'Hum': [aio_feed_prefix + "-humidity", True],
                      'Dew': [aio_feed_prefix + "-dewpoint", False], 'Bar': [aio_household_prefix + "-barometer", True]}
        #aio_forecast_icon_format = aio_household_prefix + "-weather-forecast-icon"
        aio_air_quality_level_format = aio_feed_prefix + "-air-quality-level"
    else:
        print('Invalid Adafruit IO Package')

# Set up comms error and failure flags
luft_resp = True # Set to False when there is a Luftdaten comms error
aio_resp = True # Set to False when there is an comms error on all Adafruit IO feeds
successful_comms_time = time.time() # Used to record the latest time that comms was successful
comms_failure_tolerance = 3600 # Adjust this to set the comms failure duration before a reboot via the watchdog
# is triggered
comms_failure = False # Set to True when there has been a comms failure on either Luftdaten and/or Adafruit IO,
# depending on the enabled combination
    
# Take one reading from each climate and gas sensor on start up to stabilise readings
first_temperature_reading = bme280.get_temperature()
first_humidity_reading = bme280.get_humidity()
first_pressure_reading = bme280.get_pressure() * barometer_altitude_comp_factor(altitude, first_temperature_reading)
use_external_temp_hum = False
use_external_barometer = False
first_light_reading = ltr559.get_lux()
first_proximity_reading = ltr559.get_proximity()
raw_red_rs, raw_oxi_rs, raw_nh3_rs = read_raw_gas()

# Set up startup gas sensors' R0 with no compensation (Compensation will be set up after warm up time)
red_r0, oxi_r0, nh3_r0 = read_raw_gas()
# Set up daily gas sensor calibration lists
reds_r0 = []
oxis_r0 = []
nh3s_r0 = []
gas_calib_temps = []
gas_calib_hums = []
gas_calib_bars = []
print("Startup R0. Red R0:", round(red_r0, 0), "Oxi R0:", round(oxi_r0, 0), "NH3 R0:", round(nh3_r0, 0))
# Capture temp/hum/bar to define variables
gas_calib_temp = round(first_temperature_reading, 1)
gas_calib_hum = round(first_humidity_reading, 1)
gas_calib_bar = round(first_pressure_reading, 1)
gas_sensors_warm = False
outdoor_gas_sensors_warm = False # Only used for an indoor unit when indoor/outdoor functionality is enabled
mqtt_values["Gas Calibrated"] = False # Only set to true after the gas sensor warmup time has been completed
gas_sensors_warmup_time = 6000
gas_daily_r0_calibration_completed = False

# Set up weather forecast
first_climate_reading_done = False
barometer_history = [0.00 for x in range (9)]
barometer_change = 0
barometer_trend = ''
barometer_log_time = 0
valid_barometer_history = False
forecast = 'Insufficient Data'
icon_forecast = 'Wait'
domoticz_forecast = '0'
aio_forecast = 'question'

# Set up times
eco2_tvoc_update_time = 0 # Set the eCO2 and TVOC update time baseline
eco2_tvoc_get_baseline_update_time = 0 # Set the eCO2 and TVOC get_baseline update time 
short_update_time = 0 # Set the short update time baseline (for watchdog alive file and Luftdaten updates)
short_update_delay = 150 # Time between short updates
previous_aio_update_minute = None # Used to record the last minute that the aio feeds were updated
long_update_time = 0 # Set the long update time baseline (for all other updates)
long_update_delay = 300 # Time between long updates
long_update_toggle = False # Allows external outdoor Luftdaten or Adafruit updates to be undertaken every second long-update cycle
startup_stabilisation_time = 300 # Time to allow sensor stabilisation before sending external updates
start_time = time.time()
barometer_available_time = start_time + 10945 # Initialise the time until a forecast is available (3 hours + the time
# taken before the first climate reading)
mqtt_values["Bar"] = [gas_calib_bar, domoticz_forecast]
domoticz_hum_map = {"good": "1", "dry": "2", "wet": "3"}
mqtt_values["Hum"] = [gas_calib_hum, domoticz_hum_map["good"]]
path = os.path.dirname(os.path.realpath(__file__))

# Set up outdoor aio readings dictionary and requests session
outdoor_aio_readings = {"Temp": "-temperature", "Hum": "-humidity", "Dew": "-dewpoint", "P1": "-pm1", "P10": "-pm10", "P2.5": "-pm2-dot-5",
                        "Oxi": "-oxidising", "Red": "-reducing", "NH3": "-ammonia"}
external_outdoor_data_session = requests.Session()

if enable_eco2_tvoc: # Set up SGP30 if it's enabled
    eco2_tvoc_baseline = [] # Initialise tvoc_co2_baseline format: get - [eco2 value, tvoc value, time set] set
    # - [tvoc value, eco2 value]
    valid_eco2_tvoc_baseline = False
    from sgp30 import SGP30
    import sys
    def crude_progress_bar():
        sys.stdout.write('.')
        sys.stdout.flush()
    # Create an SGP30 instance
    sgp30 = SGP30()
    display_startup("Northcliff\nEnviro Monitor\nSensor Warmup\nPlease Wait")
    print("SGP30 Sensor warming up, please wait...")
    sgp30.start_measurement(crude_progress_bar)
    sys.stdout.write('\n')

# Set up Noise Monitor
own_noise_level = 0
luft_noise_values = []
aio_noise_values = []
own_noise_max = 0
own_noise_max_datetime = None
own_noise_freq = [0, 0, 0] # Set up spl by frequency list
noise_thresholds = (70, 90)
own_noise_values = [[0,0] for i in range(26)]
own_noise_freq_values = [[0,0,0,0] for i in range(8)]
noise_vsmallfont = ImageFont.truetype(UserFont, 11)
noise_smallfont = ImageFont.truetype(UserFont, 16)
noise_mediumfont = ImageFont.truetype(UserFont, 24)
noise_largefont = ImageFont.truetype(UserFont, 32)
noise_back_colour = (0, 0, 0)
outdoor_noise_level = 0
outdoor_noise_max = 0
outdoor_noise_max_datetime = None
outdoor_noise_freq = [0, 0, 0] # Set up spl by frequency list
outdoor_noise_values = [[0,0] for i in range(26)]
outdoor_noise_freq_values = [[0,0,0,0] for i in range(8)]
if enable_noise:
    mqtt_values["Noise"] = 0
    mqtt_values["Noise Freq"] = 0
    noise_ref_level = 0.000001 # Sets quiet level reference baseline for dB(A) measurements. Can be used for sound level baseline calibration
    global recording
    recording = []
    global noise_sample_counter
    noise_sample_counter = 0
    noise_previous_sample_count = 0
    noise_sample_rate = 48000
    noise_block_size = 12000
    noise_stream = sd.InputStream(samplerate=noise_sample_rate, channels=1, blocksize = noise_block_size, device = "dmic_sv", callback=process_noise_frames)
else:
    noise_stream = NullContextManager() # Dummy Context Manager when noise is disabled

# Capture software and config versions. Used to determine if a mender code or config update has been sent.
try:
    with open('<Your Mender Software Version File Location Here>', 'r') as f:
        startup_mender_software_version = f.read()
except IOError:
    print('No Mender Software Version Available. Using Default')
    startup_mender_software_version = monitor_version
try:
    with open('<Your Mender Config Version File Location Here>', 'r') as f:
        startup_mender_config_version = f.read()
except IOError:
    print('No Mender Config Version Available. Using Default')
    startup_mender_config_version = "Base Config"
# Check for a persistence data log and use it if it exists and was < 10 minutes ago
persistent_data_log = {}
try:
    with open('<Your Persistent Data Log File Name Here>', 'r') as f:
        persistent_data_log = json.loads(f.read())
except IOError:
    print('No Persistent Data Log Available. Using Defaults')
except json.decoder.JSONDecodeError:
    print('Invalid Persistent Data Log File Format. Using Defaults') 
if "Update Time" in persistent_data_log and "Gas Calib Temp List" in persistent_data_log: # Check that the log has
    # been updated and has a format >= 3.87
    if (start_time - persistent_data_log["Update Time"]) < 1200: # Only update non eCO2/TVOC variables if the log was
        # updated < 20 minutes before start-up
        long_update_time = persistent_data_log["Update Time"]
        barometer_log_time = persistent_data_log["Barometer Log Time"]
        forecast = persistent_data_log["Forecast"]
        barometer_available_time = persistent_data_log["Barometer Available Time"]
        valid_barometer_history = persistent_data_log["Valid Barometer History"]
        barometer_history = persistent_data_log["Barometer History"]
        barometer_change = persistent_data_log["Barometer Change"]
        barometer_trend = persistent_data_log["Barometer Trend"]
        icon_forecast = persistent_data_log["Icon Forecast"]
        domoticz_forecast = persistent_data_log["Domoticz Forecast"]
        aio_forecast = persistent_data_log["AIO Forecast"]
        gas_sensors_warm = persistent_data_log["Gas Sensors Warm"]
        gas_calib_temp = persistent_data_log["Gas Temp"]
        gas_calib_hum = persistent_data_log["Gas Hum"]
        gas_calib_bar = persistent_data_log["Gas Bar"]
        gas_calib_temps = persistent_data_log["Gas Calib Temp List"]
        gas_calib_hums = persistent_data_log["Gas Calib Hum List"]
        gas_calib_bars = persistent_data_log["Gas Calib Bar List"]
        red_r0 = persistent_data_log["Red R0"]
        oxi_r0 = persistent_data_log["Oxi R0"]
        nh3_r0 = persistent_data_log["NH3 R0"]
        reds_r0 = persistent_data_log["Red R0 List"]
        oxis_r0 = persistent_data_log["Oxi R0 List"]
        nh3s_r0 = persistent_data_log["NH3 R0 List"]
        if "Dew" in persistent_data_log["Own Disp Values"]: # Only capture display values if dewpoint data is present
            own_disp_values = persistent_data_log["Own Disp Values"]
        if "Dew" in persistent_data_log["Outdoor Disp Values"]: # Only capture display values if dewpoint data is present
            outdoor_disp_values = persistent_data_log["Outdoor Disp Values"]
        maxi_temp = persistent_data_log["Maxi Temp"]
        mini_temp = persistent_data_log["Mini Temp"]
        last_page = persistent_data_log["Last Page"]
        mode = persistent_data_log["Mode"]
        if "Own Noise Values" in persistent_data_log: # Capture Noise data if available
            own_noise_values = persistent_data_log["Own Noise Values"]
            outdoor_noise_values = persistent_data_log["Outdoor Noise Values"]
            own_noise_freq_values = persistent_data_log["Own Noise Freq Values"]
            outdoor_noise_freq_values = persistent_data_log["Outdoor Noise Freq Values"]
            own_noise_max = persistent_data_log["Own Noise Max"]
            outdoor_noise_max = persistent_data_log["Outdoor Noise Max"]
            own_noise_max_datetime = persistent_data_log["Own Noise Max Date Time"]
            outdoor_noise_max_datetime = persistent_data_log["Outdoor Noise Max Date Time"]
        print('Persistent Data Log retrieved and used')
        print("Recovered R0. Red R0:", round(red_r0, 0), "Oxi R0:", round(oxi_r0, 0), "NH3 R0:", round(nh3_r0, 0))
    else:
        print('Persistent Data Log Too Old. Using Defaults')
else:
    print('Invalid Persistent Data Log. Using Defaults')
if "eCO2 TVOC Baseline" in persistent_data_log and enable_eco2_tvoc: # Capture the SGP30 baseline, if it's available
    # and eCO2 and TVOC are enabled
    eco2_tvoc_baseline = persistent_data_log["eCO2 TVOC Baseline"]
    if eco2_tvoc_baseline != []:
        if time.time() - eco2_tvoc_baseline[2] < 6048000: # Only use the baseline if it has been populated in the
            # persistent data file and was updated less than a week ago
            valid_eco2_tvoc_baseline = True
            print('Setting eCO2 and TVOC baseline. get_baseline:', eco2_tvoc_baseline[0:2], 'set_baseline:',
                  eco2_tvoc_baseline[::-1][1:3])
            sgp30.command('set_baseline', eco2_tvoc_baseline[::-1][1:3]) # Reverse the order. get_baseline is in
            # the order of CO2, TVOC. set_baseline is TVOC, CO2 !Arghh!
if reset_gas_sensor_calibration: # Uses reset_gas_sensor_calibration in config to reset gas sensor calibration.
    #Assume that the gas sensors don't need a warmup time (but need to be stable) in this situation.
    print("Reset Gas Sensor Calibration")
    gas_sensors_warm = False
    gas_sensors_warmup_time = startup_stabilisation_time

if enable_adafruit_io: # Send Version info to Adafruit IO
    if aio_package == "Premium Plus" or aio_package == "Premium" or aio_package == "Premium Plus Noise" or aio_package == "Premium Noise":
        version_text = "Code: " + startup_mender_software_version + " Config: " + startup_mender_config_version
        print("Sending Startup Versions to Adafruit IO", version_text)
        feed_resp = send_data_to_aio(aio_version_text_format, version_text)

# Update the weather forecast, based on the data retrieved from the persistent data log
mqtt_values["Forecast"] = {"Valid": valid_barometer_history, "3 Hour Change": round(barometer_change, 1),
                           "Forecast": forecast}

# Main loop
try:
    with noise_stream:
        while True:
            if enable_noise:# Take noise sample on every loop if noise is enabled
                if noise_sample_counter != noise_previous_sample_count: # Only process new sample
                    noise_previous_sample_count = noise_sample_counter
                    if noise_sample_counter > 10: # Wait for microphone stability
                        recording_offset = np.mean(recording)
                        recording = recording - recording_offset # Remove remaining microphone DC Offset
                        weighted_recording = A_weight(recording, noise_sample_rate)
                        weighted_rms = np.sqrt(np.mean(np.square(weighted_recording)))
                        own_noise_ratio = (weighted_rms)/noise_ref_level
                        new_noise_mqtt_value = False
                        if own_noise_ratio > 0:
                            noise_level = 20*math.log10(own_noise_ratio)
                            own_noise_level = round(noise_level, 1)
                            own_noise_values = own_noise_values[1:] + [[own_noise_level, 1]]
                            # Capture Max, Luftdaten and Adafruit IO sound levels and once display has been changed for > 2 seconds
                            if (time.time() - last_page) > 2:
                                if enable_luftdaten and enable_luftdaten_noise:
                                    luft_noise_values.append(round(noise_level, 2)) # Capture Luftdaten Noise Level
                                if own_noise_level >= own_noise_max:
                                    own_noise_max = own_noise_level
                                    own_noise_max_event = datetime.now()
                                    date_string = own_noise_max_event.strftime("%d %b %y").lstrip('0')
                                    time_string = own_noise_max_event.strftime("%H:%M")
                                    own_noise_max_datetime = {"Date": date_string, "Time": time_string}
                                    mqtt_values["Max Noise"] = round(own_noise_max, 1)
                                    mqtt_values["Max Noise Date Time"] = own_noise_max_datetime
                                aio_noise_values.append(own_noise_level) # Capture Adafruit IO Noise Level
                                if own_noise_level >= mqtt_values["Noise"]:
                                    mqtt_values["Noise"] = round(own_noise_level, 1)
                                    new_noise_mqtt_value = True
                        amps = get_rms_at_frequency_ranges(weighted_recording, [(20, 500), (500, 2000), (2000, 20000)], noise_sample_rate)
                        own_noise_ratio_freq = [n/noise_ref_level for n in amps]
                        all_noise_ratio_freq_ok = True
                        for noise_ratio in own_noise_ratio_freq: # Ensure that ratios are > 0
                            if noise_ratio <= 0:
                                all_noise_ratio_freq_ok = False
                        if all_noise_ratio_freq_ok:
                            for item in range(len(own_noise_ratio_freq)):
                                own_noise_freq[item] = round(20*math.log10(own_noise_ratio_freq[item]), 1)
                            if new_noise_mqtt_value:
                                mqtt_values["Noise Freq"] = own_noise_freq
                            own_noise_freq_values = own_noise_freq_values[1:] + [[own_noise_freq[0], own_noise_freq[1], own_noise_freq[2], 1]]
            # Read air particle values on every loop
            luft_values, mqtt_values, own_data, own_disp_values = read_pm_values(luft_values, mqtt_values, own_data,
                                                                                 own_disp_values)
            
            # Read climate values, update Luftdaten and write to watchdog file every 2.5 minutes
            # (set by short_update_time).
            run_time = round((time.time() - start_time), 0)
            time_since_short_update = time.time() - short_update_time
            if time_since_short_update >= short_update_delay:
                short_update_time = time.time()
                # Calibrate gas sensors once after warmup
                if ((time.time() - start_time) >= gas_sensors_warmup_time) and gas_sensors_warm == False and\
                        first_climate_reading_done:
                    gas_calib_temp = round(raw_temp, 1)
                    gas_calib_hum = round(raw_hum, 1)
                    gas_calib_bar = round(raw_barometer, 1)
                    red_r0, oxi_r0, nh3_r0 = read_raw_gas()
                    print("Gas Sensor Calibration after Warmup. Red R0:", red_r0, "Oxi R0:", oxi_r0, "NH3 R0:", nh3_r0)
                    print("Gas Calibration Baseline. Temp:", gas_calib_temp, "Hum:", gas_calib_hum,
                          "Barometer:", gas_calib_bar)
                    reds_r0 = [red_r0] * 7
                    oxis_r0 = [oxi_r0] * 7
                    nh3s_r0 = [nh3_r0] * 7
                    gas_calib_temps = [gas_calib_temp] * 7
                    gas_calib_hums = [gas_calib_hum] * 7
                    gas_calib_bars = [gas_calib_bar] * 7
                    gas_sensors_warm = True               
                (luft_values, mqtt_values, own_data, maxi_temp, mini_temp, own_disp_values, raw_red_rs, raw_oxi_rs,
                 raw_nh3_rs, raw_temp, comp_temp, comp_hum, raw_hum, use_external_temp_hum, use_external_barometer,
                 raw_barometer, absolute_hum) = read_climate_gas_values(luft_values, mqtt_values, own_data, maxi_temp,
                                                                        mini_temp, own_disp_values, gas_sensors_warm,
                                                                        gas_calib_temp, gas_calib_hum, gas_calib_bar,
                                                                        altitude, enable_eco2_tvoc)
                first_climate_reading_done = True
                print('Luftdaten Values', luft_values)
                print('mqtt Values', mqtt_values)
                # Write to the watchdog file unless there is a comms failure for >= comms_failure_tolerance
                # when both Luftdaten and Adafruit IO arenabled
                if comms_failure == False:
                    with open('<Your Watchdog File Name Here>', 'w') as f:
                        f.write('Enviro Script Alive')
                if enable_luftdaten: # Send data to Luftdaten if enabled
                    luft_resp = send_to_luftdaten(luft_values, id, enable_particle_sensor, enable_noise, luft_noise_values, disable_luftdaten_sensor_upload)
                    luft_noise_values = [] #Reset Luftdaten Noise Values List after each attempted transmission
                    #logging.info("Luftdaten Response: {}\n".format("ok" if luft_resp else "failed"))
                    data_sent_to_luftdaten_or_aio = True
                    if luft_resp:
                        print("Luftdaten update successful. Waiting for next capture cycle")
                    else:
                        print("Luftdaten update unsuccessful. Waiting for next capture cycle")
                else:
                    print('Waiting for next capture cycle')

            # Read TVOC and eCO2 every second
            if enable_eco2_tvoc:
                time_since_eco2_tvoc = time.time() - eco2_tvoc_update_time
                if time_since_eco2_tvoc >= 1:
                    eco2_tvoc_update_time = time.time()
                    mqtt_values, own_data, own_disp_values = read_eco2_tvoc_values(mqtt_values, own_data, own_disp_values)    

            # Read and update the barometer log if the first climate reading has been done and the last update was >=
            # 20 minutes ago
            if first_climate_reading_done and (time.time() - barometer_log_time) >= 1200:
                if barometer_log_time == 0: # If this is the first barometer log, record the time that a forecast will be
                    # available (3 hours)
                    barometer_available_time = time.time() + 10800
                barometer_history, barometer_change, valid_barometer_history, barometer_log_time, forecast,\
                barometer_trend, icon_forecast, domoticz_forecast, aio_forecast = log_barometer(own_data['Bar'][1],
                                                                                                barometer_history)
                mqtt_values["Forecast"] = {"Valid": valid_barometer_history, "3 Hour Change": round(barometer_change, 1),
                                           "Forecast": forecast.replace("\n", " ")}
                mqtt_values["Bar"][1] = domoticz_forecast # Add Domoticz Weather Forecast
                print('Barometer Logged. Waiting for next capture cycle')

            # Process paired outdoor unit, if enabled
            if (enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor'
                    and outdoor_source_type == 'Enviro'):
                if captured_outdoor_data != {}: #If there's new data
                    for reading in outdoor_data: # Only capture data that's been sent
                        if reading in captured_outdoor_data:
                            if reading == "Bar" or reading == "Hum": # Barometer and Humidity readings have their
                                # data in lists
                                outdoor_data[reading][1] = captured_outdoor_data[reading][0]
                            else:
                                outdoor_data[reading][1] = captured_outdoor_data[reading]
                            outdoor_disp_values[reading] = outdoor_disp_values[reading][1:] +\
                                                           [[outdoor_data[reading][1], 1]]
                    outdoor_maxi_temp = captured_outdoor_data["Max Temp"]
                    outdoor_mini_temp = captured_outdoor_data["Min Temp"]
                    outdoor_gas_sensors_warm = captured_outdoor_data["Gas Calibrated"]
                    if "Noise" in captured_outdoor_data:
                        outdoor_noise_level = captured_outdoor_data["Noise"]
                        outdoor_noise_values = outdoor_noise_values[1:] + [[outdoor_noise_level, 1]]
                    if "Max Noise" in captured_outdoor_data:
                        outdoor_noise_max = captured_outdoor_data["Max Noise"]
                    if "Max Noise Date Time" in captured_outdoor_data:
                        outdoor_noise_max_datetime = captured_outdoor_data["Max Noise Date Time"]
                    if "Noise Freq" in captured_outdoor_data:
                        outdoor_noise_freq = captured_outdoor_data["Noise Freq"]
                        outdoor_noise_freq_values = outdoor_noise_freq_values[1:] + [[outdoor_noise_freq[0], outdoor_noise_freq[1], outdoor_noise_freq[2], 1]]
                    outdoor_reading_captured = True
                    outdoor_reading_captured_time = time.time()
                    captured_outdoor_data = {}
                    
            # Update Display on every loop
            last_page, mode, start_current_display, current_display_is_own, own_noise_max =\
                display_results(start_current_display, current_display_is_own, display_modes,
                                indoor_outdoor_display_duration, own_data, data_in_display_all_aq, outdoor_data,
                                outdoor_reading_captured, own_disp_values, outdoor_disp_values, delay, last_page, mode,
                                WIDTH, valid_barometer_history, forecast, barometer_available_time, barometer_change,
                                barometer_trend, icon_forecast, maxi_temp, mini_temp, air_quality_data,
                                air_quality_data_no_gas, gas_sensors_warm, outdoor_gas_sensors_warm, enable_display,
                                palette, enable_adafruit_io, aio_user_name, aio_household_prefix, enable_eco2_tvoc,
                                outdoor_source_type, own_noise_level, own_noise_max, own_noise_max_datetime,
                                own_noise_values, own_noise_freq_values, outdoor_noise_level, outdoor_noise_max,
                                outdoor_noise_max_datetime, outdoor_noise_values, outdoor_noise_freq_values)

            # Provide external updates and update persistent data log
            if run_time > startup_stabilisation_time: # Wait until the gas sensors have stabilised before providing
                # external updates or updating the persistent data log
                # Send data to Adafruit IO if enabled, set up and the time is now within the configured window and sequence
                if enable_adafruit_io and aio_format != {}:
                    today=datetime.now()
                    window_minute = int(today.strftime('%M'))
                    window_second = int(today.strftime('%S'))
                    if window_minute % 10 == aio_feed_window and window_second // 15 == aio_feed_sequence and\
                            window_minute != previous_aio_update_minute:
                        aio_resp = update_aio(mqtt_values, forecast, aio_format, aio_forecast_text_format,
                                              aio_air_quality_level_format, aio_air_quality_text_format,
                                              own_data, icon_air_quality_levels, aio_package, gas_sensors_warm,
                                              air_quality_data, air_quality_data_no_gas, aio_noise_values,
                                             aio_version_text_format, version_text)
                        aio_noise_values = [] # Reset noise Adafruit IO Noise Levels after each transmission
                        data_sent_to_luftdaten_or_aio = True
                        previous_aio_update_minute = window_minute
                        if aio_resp:
                            print("At least one Adafruit IO feed successful. Waiting for next capture cycle")
                        else:
                            print("No Adafruit IO feeds successful. Waiting for next capture cycle")
                time_since_long_update = time.time() - long_update_time
                
                # Provide/capture other external updates and update persistent data log every 5 minutes
                # (Set by long_update_delay)
                if time_since_long_update >= long_update_delay:
                    long_update_time = time.time()
                    if (indoor_outdoor_function == 'Indoor' and enable_send_data_to_homemanager):
                        client.publish(indoor_mqtt_topic, json.dumps(mqtt_values)) # Send indoor mqtt data
                    elif (indoor_outdoor_function == 'Outdoor' and (enable_indoor_outdoor_functionality or
                                                                    enable_send_data_to_homemanager)):
                        client.publish(outdoor_mqtt_topic, json.dumps(mqtt_values)) # Send outdoor mqtt data
                    if enable_noise:
                        mqtt_values["Noise"] = 0 # Reset noise mqtt reading after each transmission to capture new max level
                    if enable_climate_and_gas_logging: # Log data
                        log_climate_and_gas(run_time, own_data, raw_red_rs, raw_oxi_rs, raw_nh3_rs, raw_temp,
                                            comp_temp, comp_hum, raw_hum, use_external_temp_hum, use_external_barometer,
                                            raw_barometer)
                    if (enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor'
                            and (outdoor_source_type == 'Luftdaten' or outdoor_source_type == 'Adafruit IO')): # Capture
                        # outdoor data via Luftdaten or Adafruit IO
                        long_update_toggle = not long_update_toggle
                        if long_update_toggle: # Only capture outdoor data via Luftdaten or Adafruit IO on every second cycle
                            outdoor_reading_captured = False
                            external_outdoor_data = capture_external_outdoor_data(outdoor_source_type, outdoor_source_id,
                                                                                  outdoor_aio_readings)
                            if external_outdoor_data != {}:
                                print('External Outdoor Data', external_outdoor_data)
                                if outdoor_source_type == 'Luftdaten':
                                    if "Temp" in external_outdoor_data:
                                        outdoor_data["Temp"][1] = external_outdoor_data["Temp"]
                                        outdoor_disp_values["Temp"] = outdoor_disp_values["Temp"][1:] +\
                                                                      [[outdoor_data["Temp"][1], 1]]
                                        if outdoor_maxi_temp == None:
                                            outdoor_maxi_temp = outdoor_data["Temp"][1]
                                        elif outdoor_data["Temp"][1] > outdoor_maxi_temp:
                                            outdoor_maxi_temp = outdoor_data["Temp"][1]
                                        if outdoor_mini_temp == None:
                                            outdoor_mini_temp = outdoor_data["Temp"][1]
                                        elif outdoor_data["Temp"][1] < outdoor_mini_temp:
                                            outdoor_mini_temp = outdoor_data["Temp"][1]
                                    if "Hum" in external_outdoor_data:
                                        outdoor_data["Hum"][1] = external_outdoor_data["Hum"]
                                        outdoor_disp_values["Hum"] = outdoor_disp_values["Hum"][1:] +\
                                                                     [[outdoor_data["Hum"][1], 1]]
                                    if "P10" in external_outdoor_data:
                                        outdoor_data["P10"][1] = external_outdoor_data["P10"]
                                        outdoor_disp_values["P10"] = outdoor_disp_values["P10"][1:] +\
                                                                     [[outdoor_data["P10"][1], 1]]
                                    if "P2.5" in external_outdoor_data:
                                        outdoor_data["P2.5"][1] = external_outdoor_data["P2.5"]
                                        outdoor_disp_values["P2.5"] = outdoor_disp_values["P2.5"][1:] +\
                                                                      [[outdoor_data["P2.5"][1], 1]]
                                    outdoor_data["Dew"][1] = round(calculate_dewpoint(outdoor_data["Temp"][1], outdoor_data["Hum"][1]),1)
                                    outdoor_disp_values["Dew"] = outdoor_disp_values["Dew"][1:] +\
                                                                 [[outdoor_data["Dew"][1], 1]]
                                    outdoor_data["Bar"][1] = own_data["Bar"][1] # Use internal air pressure data
                                    outdoor_data["P1"][1] = None
                                    outdoor_data["Oxi"][1] = None
                                    outdoor_data["Red"][1] = None
                                    outdoor_data["NH3"][1] = None
                                    outdoor_data["Lux"][1] = None
                                    outdoor_gas_sensors_warm = False
                                    outdoor_reading_captured = True
                                    outdoor_reading_captured_time = time.time()
                                elif outdoor_source_type == 'Adafruit IO':
                                    for reading in outdoor_aio_readings:
                                        if reading in external_outdoor_data:
                                            outdoor_reading_captured = True
                                            outdoor_reading_captured_time = time.time()
                                            outdoor_data[reading][1] = external_outdoor_data[reading]
                                            outdoor_disp_values[reading] = outdoor_disp_values[reading][1:] + [
                                                [outdoor_data[reading][1], 1]]
                                    if outdoor_maxi_temp == None:
                                        outdoor_maxi_temp = outdoor_data["Temp"][1]
                                    elif outdoor_data["Temp"][1] > outdoor_maxi_temp:
                                        outdoor_maxi_temp = outdoor_data["Temp"][1]
                                    if outdoor_mini_temp == None:
                                        outdoor_mini_temp = outdoor_data["Temp"][1]
                                    elif outdoor_data["Temp"][1] < outdoor_mini_temp:
                                        outdoor_mini_temp = outdoor_data["Temp"][1]
                                    outdoor_data["Lux"][1] = None
                                    outdoor_data["Bar"][1] = own_data["Bar"][1] # Use internal air pressure data
                                    outdoor_gas_sensors_warm = True
                            else:
                                print("No external outdoor data captured")
                                
                    # Write to the persistent data log
                    if enable_eco2_tvoc: # Update and add eco2_tvoc_baseline if CO2/TVOC is enabled and the SGP30 sensor
                        # has been active for more than 12 hours, or there's a valid baseline
                        if run_time > 43200 or valid_eco2_tvoc_baseline:
                            time_since_eco2_tvoc_get_baseline = time.time() - eco2_tvoc_get_baseline_update_time
                            if time_since_eco2_tvoc_get_baseline >= 3600: # Update every hour
                                eco2_tvoc_get_baseline_update_time = time.time()
                                eco2_tvoc_baseline = sgp30.command('get_baseline')
                                eco2_tvoc_baseline.append(eco2_tvoc_get_baseline_update_time)
                                print('Storing eCO2/TVOC Baseline', eco2_tvoc_baseline)
                        persistent_data_log = {"Update Time": long_update_time, "Barometer Log Time": barometer_log_time,
                                               "Forecast": forecast, "Barometer Available Time": barometer_available_time,
                                               "Valid Barometer History": valid_barometer_history,
                                               "Barometer History": barometer_history, "Barometer Change": barometer_change,
                                               "Barometer Trend": barometer_trend, "Icon Forecast": icon_forecast,
                                               "Domoticz Forecast": domoticz_forecast, "AIO Forecast": aio_forecast,
                                               "Gas Sensors Warm": gas_sensors_warm, "Gas Temp": gas_calib_temp,
                                               "Gas Hum": gas_calib_hum, "Gas Bar": gas_calib_bar, "Red R0": red_r0,
                                               "Oxi R0": oxi_r0, "NH3 R0": nh3_r0, "Red R0 List": reds_r0,
                                               "Oxi R0 List": oxis_r0, "NH3 R0 List": nh3s_r0,
                                               "Gas Calib Temp List": gas_calib_temps, "Gas Calib Hum List": gas_calib_hums,
                                               "Gas Calib Bar List": gas_calib_bars, "Own Disp Values": own_disp_values,
                                               "Outdoor Disp Values": outdoor_disp_values, "Maxi Temp": maxi_temp,
                                               "Mini Temp": mini_temp, "Last Page": last_page, "Mode": mode,
                                               "eCO2 TVOC Baseline": eco2_tvoc_baseline}
                    else: # Don't add eco2_tvoc_baseline if eCO2/TVOC is not enabled or the SGP30 sensor
                          # has not been active for more than 12 hours, or there isn't a valid baseline
                        persistent_data_log = {"Update Time": long_update_time, "Barometer Log Time": barometer_log_time,
                                               "Forecast": forecast, "Barometer Available Time": barometer_available_time,
                                               "Valid Barometer History": valid_barometer_history,
                                               "Barometer History": barometer_history, "Barometer Change": barometer_change,
                                               "Barometer Trend": barometer_trend, "Icon Forecast": icon_forecast,
                                               "Domoticz Forecast": domoticz_forecast, "AIO Forecast": aio_forecast,
                                               "Gas Sensors Warm": gas_sensors_warm, "Gas Temp": gas_calib_temp,
                                               "Gas Hum": gas_calib_hum, "Gas Bar": gas_calib_bar, "Red R0": red_r0,
                                               "Oxi R0": oxi_r0, "NH3 R0": nh3_r0, "Red R0 List": reds_r0,
                                               "Oxi R0 List": oxis_r0, "NH3 R0 List": nh3s_r0,
                                               "Gas Calib Temp List": gas_calib_temps, "Gas Calib Hum List": gas_calib_hums,
                                               "Gas Calib Bar List": gas_calib_bars, "Own Disp Values": own_disp_values,
                                               "Outdoor Disp Values": outdoor_disp_values,
                                               "Maxi Temp": maxi_temp, "Mini Temp": mini_temp, "Last Page": last_page,
                                               "Mode": mode}
                    # Add Noise data
                    persistent_data_log["Own Noise Values"] = own_noise_values
                    persistent_data_log["Outdoor Noise Values"] = outdoor_noise_values
                    persistent_data_log["Own Noise Freq Values"] = own_noise_freq_values
                    persistent_data_log["Outdoor Noise Freq Values"] = outdoor_noise_freq_values
                    persistent_data_log["Own Noise Max"] = own_noise_max
                    persistent_data_log["Outdoor Noise Max"] = outdoor_noise_max
                    persistent_data_log["Own Noise Max Date Time"] = own_noise_max_datetime
                    persistent_data_log["Outdoor Noise Max Date Time"] = outdoor_noise_max_datetime
                    print('Logging Barometer, Forecast, Gas Calibration and Display Data')
                    with open('<Your Persistent Data Log File Name Here>', 'w') as f:
                        f.write(json.dumps(persistent_data_log))
                    if "Forecast" in mqtt_values:
                        mqtt_values.pop("Forecast") # Remove Forecast after sending it to home manager so that
                        # forecast data is only sent when updated
                    # Check if there has been software or config update and restart code if either has been updated
                    try:
                        with open('<Your Mender Software Version File Location Here>', 'r') as f:
                            latest_mender_software_version = f.read()
                    except IOError:
                        print('No Mender Software Version Available')
                        latest_mender_software_version = startup_mender_software_version
                    print("Startup Mender Software Version:", startup_mender_software_version,
                          "Latest Mender Software Version:", latest_mender_software_version)
                    try:
                        with open('<Your Mender Config Version File Location Here>', 'r') as f:
                            latest_mender_config_version = f.read()
                    except IOError:
                        print('No Mender Config Version Available')
                        latest_mender_config_version = startup_mender_config_version
                    print("Startup Mender Config Version:", startup_mender_config_version, "Latest Mender Config Version:", latest_mender_config_version)
                    if latest_mender_software_version != startup_mender_software_version or\
                            latest_mender_config_version != startup_mender_config_version:
                        print('Software or Config Update Received. Restarting aqimonitor')
                        if enable_send_data_to_homemanager or enable_receive_data_from_homemanager:
                            client.loop_stop()
                        time.sleep(10)
                        os.system('sudo systemctl restart aqimonitor')
                    print('Waiting for next capture cycle')

            # Luftdaten and/or Adafruit IO Communications Check. Note that aio_resp and luft_resp are both TRUE on startup,
            # so there has to be a comms error for either of them to be set to FALSE
            # Either aio_resp and luft_resp is set to TRUE if there's a subsequent error-free comms to their
            # respective platform
            if enable_adafruit_io and enable_luftdaten:
                if aio_resp or luft_resp: # Set time when a successful Luftdaten or Adafruit IO response is received,
                    # if both Luftdaten and Adafruit IO are enabled
                    successful_comms_time = time.time()
            elif enable_adafruit_io and not enable_luftdaten: # Set time when a successful Adafruit IO response is received,
                # if only Adafruit IO is enabled
                if aio_resp:
                    successful_comms_time = time.time()
            elif enable_luftdaten and not enable_adafruit_io: # Set time when a successful Luftdaten response is received,
                # if only Luftdaten is enabled
                if luft_resp:
                    successful_comms_time = time.time()
            else: # Set time if both Adafruit IO and Luftdaten are disabled so that comms failure is never triggered
                successful_comms_time = time.time()
            if time.time() - successful_comms_time >= comms_failure_tolerance:
                comms_failure = True
                print("Communications has been lost for more than " + str(int(comms_failure_tolerance/60)) +
                      " minutes. System will reboot via watchdog")
            # Outdoor Sensor Comms Check
            if time.time() - outdoor_reading_captured_time > long_update_delay * 4:
                outdoor_reading_captured = False # Reset outdoor reading captured flag if comms with the
                # outdoor sensor is lost for more than 20 minutes so that old outdoor data is not displayed
                
            # Calibrate gas sensors daily at time set by gas_daily_r0_calibration_hour,
            # using average of daily readings over a week if not already done in the current day and if warmup
            # calibration is completed
            # Compensates for gas sensor drift over time
            today=datetime.now()
            if int(today.strftime('%H')) == gas_daily_r0_calibration_hour and gas_daily_r0_calibration_completed == False\
                    and gas_sensors_warm and first_climate_reading_done:
                print("Daily Gas Sensor Calibration. Old R0s. Red R0:", red_r0, "Oxi R0:", oxi_r0, "NH3 R0:", nh3_r0)
                print("Old Calibration Baseline. Temp:", gas_calib_temp, "Hum:", gas_calib_hum,
                      "Barometer:", gas_calib_bar)
                # Set new calibration baseline using 7 day rolling average
                gas_calib_temps = gas_calib_temps[1:] + [round(raw_temp, 1)]
                #print("Calib Temps", gas_calib_temps)
                gas_calib_temp = round(sum(gas_calib_temps)/float(len(gas_calib_temps)), 1)
                gas_calib_hums = gas_calib_hums[1:] + [round(raw_hum, 1)]
                #print("Calib Hums", gas_calib_hums)
                gas_calib_hum = round(sum(gas_calib_hums)/float(len(gas_calib_hums)), 0)
                gas_calib_bars = gas_calib_bars[1:] + [round(raw_barometer, 1)]
                #print("Calib Bars", gas_calib_bars)
                gas_calib_bar = round(sum(gas_calib_bars)/float(len(gas_calib_bars)), 1)
                # Update R0s and create new calibration baseline
                # spot_red_r0, spot_oxi_r0, spot_nh3_r0, raw_red_r0, raw_oxi_r0, raw_nh3_r0 = comp_gas(gas_calib_temp,
                # gas_calib_hum, gas_calib_bar, raw_temp, raw_hum, raw_barometer)
                spot_red_r0, spot_oxi_r0, spot_nh3_r0 = read_raw_gas()
                # Convert R0s to 7 day rolling average
                reds_r0 = reds_r0[1:] + [round(spot_red_r0, 0)]
                #print("Reds R0", reds_r0)
                red_r0 = round(sum(reds_r0)/float(len(reds_r0)), 0)
                oxis_r0 = oxis_r0[1:] + [round(spot_oxi_r0, 0)]
                #print("Oxis R0", oxis_r0)
                oxi_r0 = round(sum(oxis_r0)/float(len(oxis_r0)), 0)
                nh3s_r0 = nh3s_r0[1:] + [round(spot_nh3_r0, 0)]
                #print("NH3s R0", nh3s_r0)
                nh3_r0 = round(sum(nh3s_r0)/float(len(nh3s_r0)), 0)
                print('New R0s. Red R0:', red_r0, 'Oxi R0:', oxi_r0, 'NH3 R0:', nh3_r0)
                print("New Calibration Baseline. Temp:", gas_calib_temp, "Hum:", gas_calib_hum,
                      "Barometer:", gas_calib_bar)
                gas_daily_r0_calibration_completed = True
            if int(today.strftime('%H')) == (gas_daily_r0_calibration_hour + 1) and gas_daily_r0_calibration_completed:
                gas_daily_r0_calibration_completed = False

except KeyboardInterrupt:
    if enable_send_data_to_homemanager or enable_receive_data_from_homemanager:
        client.loop_stop()
    noise_stream.abort()
    print('Keyboard Interrupt')

# Acknowledgements
# Based on code from:
# https://github.com/pimoroni/enviroplus-python/blob/master/examples/all-in-one.py
# https://github.com/pimoroni/enviroplus-python/blob/master/examples/combined.py
# https://github.com/pimoroni/enviroplus-python/blob/master/examples/compensated-temperature.py
# https://github.com/pimoroni/enviroplus-python/blob/master/examples/luftdaten.py
# https://github.com/pimoroni/enviroplus-python/blob/enviro-non-plus/examples/weather-and-light.py
# https://github.com/pimoroni/sgp30-python
# https://github.com/pimoroni/enviroplus-python/blob/master/examples/noise-amps-at-freqs.py
# https://github.com/home-assistant-ecosystem/python-luftdaten
# https://github.com/endolith/waveform_analysis/blob/master/waveform_analysis/weighting_filters/ABC_weighting.py#L29
# Weather Forecast based on www.worldstormcentral.co/law_of_storms/secret_law_of_storms.html by R. J. Ellis
