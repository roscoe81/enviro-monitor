#!/usr/bin/env python3
#Northcliff Environment Monitor - 3.72 - Gen
# Requires Home Manager >=8.43 with new mqtt message topics for indoor and outdoor and new parsed_json labels

import paho.mqtt.client as mqtt
from Adafruit_IO import Client, Feed, Data, RequestError, ThrottlingError
import colorsys
import math
import json
import requests
import ST7735
import os
import time
from datetime import datetime, timedelta
import numpy
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

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
logging.info("""Northcliff_Environment_Monitor.py - Combined enviro+ sensor capture, external sensor capture, Luftdaten and Home Manager Updates and display of readings.
#Press Ctrl+C to exit!

#Note: you'll need to register with Luftdaten at:
#https://meine.luftdaten.info/ and enter your Raspberry Pi
#serial number that's displayed on the Enviro plus LCD along
#with the other details before the data appears on the
#Luftdaten map.

#""")

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
    f = open('<Your config.json file location>', 'r')
    parsed_config_parameters = json.loads(f.read())
    print('Retrieved Config', parsed_config_parameters)
    temp_offset = parsed_config_parameters['temp_offset']
    enable_adafruit_io = parsed_config_parameters['enable_adafruit_io']
    aio_user_name = parsed_config_parameters['aio_user_name']
    aio_key = parsed_config_parameters['aio_key']
    aio_household_prefix = parsed_config_parameters['aio_household_prefix']
    aio_location_prefix = parsed_config_parameters['aio_location_prefix']
    enable_send_data_to_homemanager = parsed_config_parameters['enable_send_data_to_homemanager']
    enable_receive_data_from_homemanager = parsed_config_parameters['enable_receive_data_from_homemanager']
    enable_indoor_outdoor_functionality = parsed_config_parameters['enable_indoor_outdoor_functionality']
    mqtt_broker_name = parsed_config_parameters['mqtt_broker_name']
    enable_luftdaten = parsed_config_parameters['enable_luftdaten']
    enable_climate_and_gas_logging = parsed_config_parameters['enable_climate_and_gas_logging']
    enable_particle_sensor = parsed_config_parameters['enable_particle_sensor']
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
    return (temp_offset, enable_adafruit_io, aio_user_name, aio_key, aio_household_prefix, aio_location_prefix,
            enable_send_data_to_homemanager, enable_receive_data_from_homemanager, enable_indoor_outdoor_functionality,
            mqtt_broker_name, enable_luftdaten, enable_climate_and_gas_logging, enable_particle_sensor,
            incoming_temp_hum_mqtt_topic, incoming_temp_hum_mqtt_sensor_name, incoming_barometer_mqtt_topic, incoming_barometer_sensor_id,
            indoor_outdoor_function, mqtt_client_name, outdoor_mqtt_topic, indoor_mqtt_topic, city_name, time_zone, custom_locations)

# Config Setup
(temp_offset, enable_adafruit_io, aio_user_name, aio_key, aio_household_prefix, aio_location_prefix,
  enable_send_data_to_homemanager, enable_receive_data_from_homemanager, enable_indoor_outdoor_functionality, mqtt_broker_name,
  enable_luftdaten, enable_climate_and_gas_logging,  enable_particle_sensor, incoming_temp_hum_mqtt_topic,
  incoming_temp_hum_mqtt_sensor_name, incoming_barometer_mqtt_topic, incoming_barometer_sensor_id,
  indoor_outdoor_function, mqtt_client_name, outdoor_mqtt_topic, indoor_mqtt_topic,
  city_name, time_zone, custom_locations) = retrieve_config()

# Add to city database
db = database()
add_locations(custom_locations, db)

if enable_particle_sensor:
    # Create a PMS5003 instance
    pms5003 = PMS5003()
    time.sleep(1)
            
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

# Read gas and climate values from Home Manager and /or BME280 
def read_climate_gas_values(luft_values, mqtt_values, own_data, maxi_temp, mini_temp, own_disp_values, gas_r0_calibration_after_warmup_completed, gas_calib_temp, gas_calib_hum, gas_calib_bar):
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
    own_disp_values["Temp"] = own_disp_values["Temp"][1:] + [[own_data["Temp"][1], 1]]
    mqtt_values["Temp"] = own_data["Temp"][1]
    own_disp_values["Hum"] = own_disp_values["Hum"][1:] + [[own_data["Hum"][1], 1]]
    mqtt_values["Hum"][0] = own_data["Hum"][1]
    mqtt_values["Hum"][1] = domoticz_hum_map[describe_humidity(own_data["Hum"][1])]
    # Determine max and min temps
    if first_climate_reading_done == False:
        maxi_temp = None
        mini_temp = None
    else:
        if maxi_temp == None:
            maxi_temp = own_data["Temp"][1]
        elif own_data["Temp"][1] > maxi_temp:
            maxi_temp = own_data["Temp"][1]
        else:
            pass
        if mini_temp == None:
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
        own_data["Bar"][1] = round((raw_barometer + bar_comp_factor), 1)
        own_disp_values["Bar"] = own_disp_values["Bar"][1:] + [[own_data["Bar"][1], 1]]
        mqtt_values["Bar"][0] = own_data["Bar"][1]
        luft_values["pressure"] = "{:.2f}".format((raw_barometer + bar_comp_factor) * 100)
    else:
        print("External Barometer")
        own_data["Bar"][1] = round(float(es.barometer), 1)
        own_disp_values["Bar"] = own_disp_values["Bar"][1:] + [[own_data["Bar"][1], 1]]
        mqtt_values["Bar"][0] = own_data["Bar"][1]
        luft_values["pressure"] = "{:.2f}".format(float(es.barometer) * 100)
    red_in_ppm, oxi_in_ppm, nh3_in_ppm, comp_red_rs, comp_oxi_rs, comp_nh3_rs, raw_red_rs, raw_oxi_rs, raw_nh3_rs = read_gas_in_ppm(gas_calib_temp, gas_calib_hum, gas_calib_bar, raw_temp, raw_hum, raw_barometer, gas_r0_calibration_after_warmup_completed)
    own_data["Red"][1] = round(red_in_ppm, 2)
    own_disp_values["Red"] = own_disp_values["Red"][1:] + [[own_data["Red"][1], 1]]
    mqtt_values["Red"] = own_data["Red"][1]
    own_data["Oxi"][1] = round(oxi_in_ppm, 2)
    own_disp_values["Oxi"] = own_disp_values["Oxi"][1:] + [[own_data["Oxi"][1], 1]]
    mqtt_values["Oxi"] = own_data["Oxi"][1]
    own_data["NH3"][1] = round(nh3_in_ppm, 2)
    own_disp_values["NH3"] = own_disp_values["NH3"][1:] + [[own_data["NH3"][1], 1]]
    mqtt_values["NH3"] = own_data["NH3"][1]
    mqtt_values["Gas Calibrated"] = gas_r0_calibration_after_warmup_completed
    proximity = ltr559.get_proximity()
    if proximity < 500:
        own_data["Lux"][1] = round(ltr559.get_lux(), 1)
    else:
        own_data["Lux"][1] = 1
    own_disp_values["Lux"] = own_disp_values["Lux"][1:] + [[own_data["Lux"][1], 1]]
    mqtt_values["Lux"] = own_data["Lux"][1]
    return luft_values, mqtt_values, own_data, maxi_temp, mini_temp, own_disp_values, raw_red_rs, raw_oxi_rs, raw_nh3_rs, raw_temp, comp_temp, comp_hum, raw_hum, use_external_temp_hum, use_external_barometer, raw_barometer
    
def read_raw_gas():
    gas_data = gas.read_all()
    raw_red_rs = round(gas_data.reducing, 0)
    raw_oxi_rs = round(gas_data.oxidising, 0)
    raw_nh3_rs = round(gas_data.nh3, 0)
    return raw_red_rs, raw_oxi_rs, raw_nh3_rs
    
def read_gas_in_ppm(gas_calib_temp, gas_calib_hum, gas_calib_bar, raw_temp, raw_hum, raw_barometer, gas_r0_calibration_after_warmup_completed):
    if gas_r0_calibration_after_warmup_completed:
        comp_red_rs, comp_oxi_rs, comp_nh3_rs, raw_red_rs, raw_oxi_rs, raw_nh3_rs = comp_gas(gas_calib_temp, gas_calib_hum, gas_calib_bar, raw_temp, raw_hum, raw_barometer)
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
        red_ratio = 1
    if comp_oxi_rs/oxi_r0 > 0:
        oxi_ratio = comp_oxi_rs/oxi_r0
    else:
        oxi_ratio = 1
    if comp_nh3_rs/nh3_r0 > 0:
        nh3_ratio = comp_nh3_rs/nh3_r0
    else:
        nh3_ratio = 1
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
    comp_red_rs = round(raw_red_rs - (red_temp_comp_factor * gas_temp_diff + red_hum_comp_factor * gas_hum_diff + red_bar_comp_factor * gas_bar_diff), 0)
    raw_oxi_rs = round(gas_data.oxidising, 0)
    comp_oxi_rs = round(raw_oxi_rs - (oxi_temp_comp_factor * gas_temp_diff + oxi_hum_comp_factor * gas_hum_diff + oxi_bar_comp_factor * gas_bar_diff), 0)
    raw_nh3_rs = round(gas_data.nh3, 0)
    comp_nh3_rs = round(raw_nh3_rs - (nh3_temp_comp_factor * gas_temp_diff + nh3_hum_comp_factor * gas_hum_diff + nh3_bar_comp_factor * gas_bar_diff), 0)
    print("Gas Compensation. Raw Red Rs:", raw_red_rs, "Comp Red Rs:", comp_red_rs, "Raw Oxi Rs:", raw_oxi_rs, "Comp Oxi Rs:", comp_oxi_rs,
          "Raw NH3 Rs:", raw_nh3_rs, "Comp NH3 Rs:", comp_nh3_rs)
    return comp_red_rs, comp_oxi_rs, comp_nh3_rs, raw_red_rs, raw_oxi_rs, raw_nh3_rs
    
    
def adjusted_temperature():
    raw_temp = bme280.get_temperature()
    #comp_temp = comp_temp_slope * raw_temp + comp_temp_intercept
    comp_temp = comp_temp_cub_a * math.pow(raw_temp, 3) + comp_temp_cub_b * math.pow(raw_temp, 2) + comp_temp_cub_c * raw_temp + comp_temp_cub_d
    return raw_temp, comp_temp

def adjusted_humidity():
    raw_hum = bme280.get_humidity()
    #comp_hum = comp_hum_slope * raw_hum + comp_hum_intercept
    comp_hum = comp_hum_quad_a * math.pow(raw_hum, 2) + comp_hum_quad_b * raw_hum + comp_hum_quad_c
    return raw_hum, min(100, comp_hum)
    
def log_climate_and_gas(run_time, own_data, raw_red_rs, raw_oxi_rs, raw_nh3_rs, raw_temp, comp_temp, comp_hum, raw_hum, use_external_temp_hum, use_external_barometer, raw_barometer): # Used to log climate and gas data to create compensation algorithms
    raw_temp = round(raw_temp, 2)
    raw_hum = round(raw_hum, 2)
    comp_temp = round(comp_temp, 2)
    comp_hum = round(comp_hum, 2)
    raw_barometer = round(raw_barometer, 1)
    raw_red_rs = round(raw_red_rs, 0)
    raw_oxi_rs = round(raw_oxi_rs, 0)
    raw_nh3_rs = round(raw_nh3_rs, 0)
    if use_external_temp_hum and use_external_barometer:
        environment_log_data = {'Run Time': run_time, 'Raw Temperature': raw_temp, 'Output Temp': comp_temp,
                             'Real Temperature': own_data["Temp"][1], 'Raw Humidity': raw_hum,
                             'Output Humidity': comp_hum, 'Real Humidity': own_data["Hum"][1], 'Output Bar': own_data["Bar"][1], 'Raw Bar': raw_barometer,
                             'Oxi': own_data["Oxi"][1], 'Red': own_data["Red"][1], 'NH3': own_data["NH3"][1], 'Raw OxiRS': raw_oxi_rs, 'Raw RedRS': raw_red_rs, 'Raw NH3RS': raw_nh3_rs}
    elif use_external_temp_hum and not(use_external_barometer):
        environment_log_data = {'Run Time': run_time, 'Raw Temperature': raw_temp, 'Output Temp': comp_temp,
                             'Real Temperature': own_data["Temp"][1], 'Raw Humidity': raw_hum,
                             'Output Humidity': comp_hum, 'Real Humidity': own_data["Hum"][1], 'Output Bar': own_data["Bar"][1],
                             'Oxi': own_data["Oxi"][1], 'Red': own_data["Red"][1], 'NH3': own_data["NH3"][1], 'Raw OxiRS': raw_oxi_rs, 'Raw RedRS': raw_red_rs, 'Raw NH3RS': raw_nh3_rs}     
    elif not(use_external_temp_hum) and use_external_barometer:
        environment_log_data = {'Run Time': run_time, 'Raw Temperature': raw_temp, 'Output Temp': comp_temp,
                             'Raw Humidity': raw_hum, 'Output Humidity': comp_hum, 'Output Bar': own_data["Bar"][1], 'Raw Bar': raw_barometer,
                             'Oxi': own_data["Oxi"][1], 'Red': own_data["Red"][1], 'NH3': own_data["NH3"][1], 'Raw OxiRS': raw_oxi_rs, 'Raw RedRS': raw_red_rs, 'Raw NH3RS': raw_nh3_rs}
    else:
        environment_log_data = {'Run Time': run_time, 'Raw Temperature': raw_temp, 'Output Temp': comp_temp,
                             'Raw Humidity': raw_hum, 'Output Humidity': comp_hum, 'Output Bar': own_data["Bar"][1],
                             'Oxi': own_data["Oxi"][1], 'Red': own_data["Red"][1], 'NH3': own_data["NH3"][1], 'Raw OxiRS': raw_oxi_rs, 'Raw RedRS': raw_red_rs, 'Raw NH3RS': raw_nh3_rs}
    print('Logging Environment Data.', environment_log_data)
    with open('<Your log file location>', 'a') as f:
        f.write(',\n' + json.dumps(environment_log_data))


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
    
# Display Raspberry Pi serial and Wi-Fi status on LCD
def display_status():
    wifi_status = "connected" if check_wifi() else "disconnected"
    text_colour = (255, 255, 255)
    back_colour = (0, 170, 170) if check_wifi() else (85, 15, 15)
    id = get_serial_number()
    message = "Northcliff\nEnvironment Monitor\n{}\nWi-Fi: {}".format(id, wifi_status)
    img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    size_x, size_y = draw.textsize(message, mediumfont)
    x = (WIDTH - size_x) / 2
    y = (HEIGHT / 2) - (size_y / 2)
    draw.rectangle((0, 0, 160, 80), back_colour)
    draw.text((x, y), message, font=mediumfont, fill=text_colour)
    disp.display(img)

def send_to_luftdaten(luft_values, id, enable_particle_sensor):
    print("Sending Data to Luftdaten")
    if enable_particle_sensor:
        pm_values = dict(i for i in luft_values.items() if i[0].startswith("P"))
    temp_values = dict(i for i in luft_values.items() if not i[0].startswith("P"))
    resp1_exception = False
    resp2_exception = False

    if enable_particle_sensor:
        try:
            resp_1 = requests.post("https://api.luftdaten.info/v1/push-sensor-data/",
                     json={
                         "software_version": "enviro-plus 0.0.1",
                         "sensordatavalues": [{"value_type": key, "value": val} for
                                              key, val in pm_values.items()]
                     },
                     headers={
                         "X-PIN":   "1",
                         "X-Sensor": id,
                         "Content-Type": "application/json",
                         "cache-control": "no-cache"
                     }
            )
        except requests.exceptions.ConnectionError as e:
            resp1_exception = True
            print('Luftdaten PM Connection Error', e)
        except requests.exceptions.Timeout as e:
            resp1_exception = True
            print('Luftdaten PM Timeout Error', e)
        except requests.exceptions.RequestException as e:
            resp1_exception = True
            print('Luftdaten PM Request Error', e)

    try:
        resp_2 = requests.post("https://api.luftdaten.info/v1/push-sensor-data/",
                 json={
                     "software_version": "enviro-plus 0.0.1",
                     "sensordatavalues": [{"value_type": key, "value": val} for
                                          key, val in temp_values.items()]
                 },
                 headers={
                     "X-PIN":   "11",
                     "X-Sensor": id,
                     "Content-Type": "application/json",
                     "cache-control": "no-cache"
                 }
        )
    except requests.exceptions.ConnectionError as e:
        resp2_exception = True
        print('Luftdaten Climate Connection Error', e)
    except requests.exceptions.Timeout as e:
        resp2_exception = True
        print('Luftdaten Climate Timeout Error', e)
    except requests.exceptions.RequestException as e:
        resp2_exception = True
        print('Luftdaten Climate Request Error', e)

    if resp1_exception == False and resp2_exception == False:
        if resp_1.ok and resp_2.ok:
            return True
        else:
            return False
    else:
        return False
    
def on_connect(client, userdata, flags, rc):
    es.print_update('Northcliff Environment Monitor Connected with result code ' + str(rc))
    if enable_receive_data_from_homemanager:
        client.subscribe(incoming_temp_hum_mqtt_topic) # Subscribe to the topic for the external temp/hum data
        client.subscribe(incoming_barometer_mqtt_topic) # Subscribe to the topic for the external barometer data
    if enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor':
        client.subscribe(outdoor_mqtt_topic)

def on_message(client, userdata, msg):
    decoded_payload = str(msg.payload.decode("utf-8"))
    parsed_json = json.loads(decoded_payload)
    if msg.topic == incoming_temp_hum_mqtt_topic and parsed_json['name'] == incoming_temp_hum_mqtt_sensor_name: # Identify external temp/hum sensor
        es.capture_temp_humidity(parsed_json)
    if msg.topic == incoming_barometer_mqtt_topic and parsed_json['idx'] == incoming_barometer_sensor_id: # Identify external barometer
        es.capture_barometer(parsed_json['svalue'])
    if enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor' and msg.topic == outdoor_mqtt_topic:
        capture_outdoor_data(parsed_json)
        
    
def capture_outdoor_data(parsed_json):
    global outdoor_reading_captured
    global outdoor_data
    global outdoor_maxi_temp
    global outdoor_mini_temp
    global outdoor_disp_values
    for reading in outdoor_data:
        if reading == "Bar" or reading == "Hum": # Barometer and Humidity readings have their data in lists
            outdoor_data[reading][1] = parsed_json[reading][0]
        else:
            outdoor_data[reading][1] = parsed_json[reading]
        outdoor_disp_values[reading] = outdoor_disp_values[reading][1:] + [[outdoor_data[reading][1], 1]]
    outdoor_maxi_temp = parsed_json["Max Temp"]
    outdoor_mini_temp = parsed_json["Min Temp"]
    outdoor_reading_captured = True
    
# Displays data and text on the 0.96" LCD
def display_graphed_data(location, disp_values, variable, data, WIDTH):
    # Scale the received disp_values for the variable between 0 and 1
    received_disp_values = [disp_values[variable][v][0]*disp_values[variable][v][1] for v in range(len(disp_values[variable]))]
    graph_range = [(v - min(received_disp_values)) / (max(received_disp_values) - min(received_disp_values)) if ((max(received_disp_values) - min(received_disp_values)) != 0)
                   else 0 for v in received_disp_values]           
    # Format the variable name and value
    if variable == "Oxi":
        message = "{} {}: {:.2f} {}".format(location, variable[:4], data[1], data[0])
    elif variable == "Bar":
        message = "{}: {:.1f} {}".format(variable[:4], data[1], data[0])
    elif variable[:1] == "P" or variable == "Red" or variable == "NH3" or variable == "Hum" or variable == "Lux":
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
        message = "Barometer {:.0f} hPa\n3Hr Change {:.0f} hPa\n{}".format(round(barometer, 0), round(barometer_change, 0), forecast)
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
    
# Displays all the text on the 0.96" LCD
def display_all_aq(location, data, data_in_display_all_aq):
    draw.rectangle((0, 0, WIDTH, HEIGHT), (0, 0, 0))
    column_count = 2
    draw.text((2, 2), location + ' AIR QUALITY', font=font_ml, fill=(255, 255, 255))
    row_count = round((len(data_in_display_all_aq) / column_count), 0)
    for i in data_in_display_all_aq:
        data_value = data[i][1]
        unit = data[i][0]
        column = int(data[i][3] / row_count)
        row = data[i][3] % row_count
        x = x_offset + ((WIDTH/column_count) * column)
        y = y_offset + ((HEIGHT/(row_count + 1) * (row +1)))
        if i == "Oxi":
            message = "{}: {:.2f}".format(i, data_value)
        else:
            message = "{}: {:.0f}".format(i, round(data_value, 0))
        lim = data[i][2]
        rgb = palette[0]
        for j in range(len(lim)):
            if data_value > lim[j]:
                rgb = palette[j+1]
        draw.text((x, y), message, font=font_ml, fill=rgb)
    disp.display(img)

def display_results(start_current_display, current_display_is_own, display_modes, indoor_outdoor_display_duration, own_data, data_in_display_all_aq, outdoor_data, outdoor_reading_captured,
                    own_disp_values, outdoor_disp_values, delay, last_page, mode, luft_values, mqtt_values, WIDTH, valid_barometer_history, forecast,
                    barometer_available_time, barometer_change, barometer_trend, icon_forecast, maxi_temp, mini_temp, update_icon_display):
    proximity = ltr559.get_proximity()
    # If the proximity crosses the threshold, toggle the mode
    if proximity > 1500 and time.time() - last_page > delay:
        mode += 1
        mode %= len(display_modes)
        print('Mode', mode)
        last_page = time.time()
    selected_display_mode = display_modes[mode]
    if enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor':
        if ((time.time() -  start_current_display) > indoor_outdoor_display_duration) and outdoor_reading_captured:
            current_display_is_own = not current_display_is_own
            start_current_display = time.time()
    if selected_display_mode in own_data:
        if current_display_is_own and indoor_outdoor_function == 'Indoor' or selected_display_mode == "Bar":
            display_graphed_data('IN', own_disp_values, selected_display_mode, own_data[selected_display_mode], WIDTH)
        elif current_display_is_own and indoor_outdoor_function == 'Outdoor':
            display_graphed_data('OUT', own_disp_values, selected_display_mode, own_data[selected_display_mode], WIDTH)
        else:
            display_graphed_data('OUT', outdoor_disp_values, selected_display_mode, outdoor_data[selected_display_mode], WIDTH)
    elif selected_display_mode == "Forecast":
        display_forecast(valid_barometer_history, forecast, barometer_available_time, own_data["Bar"][1], barometer_change)
    elif selected_display_mode == "Status":
        display_status()
    elif selected_display_mode == "All Air":
        # Display everything on one screen
        if current_display_is_own and indoor_outdoor_function == 'Indoor':
            display_all_aq('IN', own_data, data_in_display_all_aq)
        elif current_display_is_own and indoor_outdoor_function == 'Outdoor':
            display_all_aq('OUT', own_data, data_in_display_all_aq)
        else:
            display_all_aq('OUT', outdoor_data, data_in_display_all_aq)
    elif selected_display_mode == "Icon Weather":
        #if update_icon_display:
        # Display icon weather/aqi
        if current_display_is_own and indoor_outdoor_function == 'Indoor':
            display_icon_weather_aqi('IN', own_data, barometer_trend, icon_forecast, maxi_temp, mini_temp, air_quality_data, icon_air_quality_levels)
        elif current_display_is_own and indoor_outdoor_function == 'Outdoor':
            display_icon_weather_aqi('OUT', own_data, barometer_trend, icon_forecast, maxi_temp, mini_temp, air_quality_data, icon_air_quality_levels)
        else:
            display_icon_weather_aqi('OUT', outdoor_data, barometer_trend, icon_forecast, outdoor_maxi_temp, outdoor_mini_temp, air_quality_data,
                                         icon_air_quality_levels)
            #update_icon_display = False
    else:
        pass
    return last_page, mode, start_current_display, current_display_is_own, update_icon_display

class ExternalSensors(object): # Handles the external temp/hum sesnors
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
    for pointer in range (8, 0, -1): # Move previous temperatures one position in the list to prepare for new temperature to be recorded
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
        forecast, icon_forecast, domoticz_forecast = analyse_barometer(barometer_change, barometer)
    else:
        valid_barometer_history=False
        forecast = 'Insufficient Data'
        icon_forecast = 'Wait'
        domoticz_forecast = '0'
        barometer_change = 0
        barometer_trend = ''
    #print("Log Barometer")
    #print("Result", barometer_history, "Valid Barometer History is", valid_barometer_history, "3 Hour Barometer Change is", round(barometer_change,2), "millibars")
    return barometer_history, barometer_change, valid_barometer_history, barometer_log_time, forecast, barometer_trend, icon_forecast, domoticz_forecast

def analyse_barometer(barometer_change, barometer):
    if barometer<1009:
        if barometer_change>-1.1 and barometer_change<6:
            forecast = 'Clearing and Colder'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
            domoticz_forecast = '3'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
            domoticz_forecast = '4'
        elif barometer_change<=-1.1 and barometer_change>=-4:
            forecast = 'Rain and Wind'
            icon_forecast = 'Rain'
            domoticz_forecast = '4'
        elif barometer_change<-4 and barometer_change>-10:
            forecast = 'Storm'
            icon_forecast = 'Storm'
            domoticz_forecast = '4'
        else:
            forecast = 'Storm and Gale'
            icon_forecast = 'Gale'
            domoticz_forecast = '4'
    elif barometer>=1009 and barometer <=1018:
        if barometer_change>-4 and barometer_change<1.1:
            forecast = 'No Change'
            icon_forecast = 'Stable'
            domoticz_forecast = '0'
        elif barometer_change>=1.1 and barometer_change<=6 and barometer<=1015:
            forecast = 'No Change'
            icon_forecast = 'Stable'
            domoticz_forecast = '0'
        elif barometer_change>=1.1 and barometer_change<=6 and barometer>1015:
            forecast = 'Poorer Weather'
            icon_forecast = 'Poorer'
            domoticz_forecast = '3'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
            domoticz_forecast = '3'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
            domoticz_forecast = '4'
        else:
            forecast = 'Rain and Wind'
            icon_forecast = 'Rain'
            domoticz_forecast = '4'
    elif barometer>1018 and barometer <=1023:
        if barometer_change>0 and barometer_change<1.1:
            forecast = 'No Change'
            icon_forecast = 'Stable'
            domoticz_forecast = '0'
        elif barometer_change>=1.1 and barometer_change<6:
            forecast = 'Poorer Weather'
            icon_forecast = 'Poorer'
            domoticz_forecast = '3'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
            domoticz_forecast = '3'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
            domoticz_forecast = '4'
        elif barometer_change>-1.1 and barometer_change<=0:
            forecast = 'Fair Weather with\nSlight Temp Change'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
        elif barometer_change<=-1.1 and barometer_change>-4:
            forecast = 'No Change but\nRain in 24 Hours'
            icon_forecast = 'Stable'
            domoticz_forecast = '0'
        else:
            forecast = 'Rain, Wind and\n Higher Temp'
            icon_forecast = 'Rain'
            domoticz_forecast = '4'
    else: # barometer>1023
        if barometer_change>0 and barometer_change<1.1:
            forecast = 'Fair Weather'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
        elif barometer_change>-1.1 and barometer_change<=0:
            forecast = 'Fair Weather with\nLittle Temp Change'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
        elif barometer_change>=1.1 and barometer_change<6:
            forecast = 'Poorer Weather'
            icon_forecast = 'Poorer'
            domoticz_forecast = '3'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
            domoticz_forecast = '3'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
            domoticz_forecast = '4'
        elif barometer_change<=-1.1 and barometer_change>-4:
            forecast = 'Fair Weather and\nSlowly Rising Temp'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
        else:
            forecast = 'Warming Trend'
            icon_forecast = 'Fair'
            domoticz_forecast = '1'
    print('3 hour barometer change is '+str(round(barometer_change,1))+' millibars with a current reading of '+str(round(barometer,1))+' millibars. The weather forecast is '+forecast) 
    return forecast, icon_forecast, domoticz_forecast

def calculate_y_pos(x, centre):
    """Calculates the y-coordinate on a parabolic curve, given x."""
    centre = 80
    y = 1 / centre * (x - centre) ** 2

    return int(y)


def circle_coordinates(x, y, radius):
    """Calculates the bounds of a circle, given centre and radius."""

    x1 = x - radius  # Left
    x2 = x + radius  # Right
    y1 = y - radius  # Bottom
    y2 = y + radius  # Top

    return (x1, y1, x2, y2)


def map_colour(x, centre, start_hue, end_hue, day):
    """Given an x coordinate and a centre point, a start and end hue (in degrees),
       and a Boolean for day or night (day is True, night False), calculate a colour
       hue representing the 'colour' of that time of day."""

    start_hue = start_hue / 360  # Rescale to between 0 and 1
    end_hue = end_hue / 360

    sat = 1.0

    # Dim the brightness as you move from the centre to the edges
    val = 1 - (abs(centre - x) / (2 * centre))

    # Ramp up towards centre, then back down
    if x > centre:
        x = (2 * centre) - x

    # Calculate the hue
    hue = start_hue + ((x / centre) * (end_hue - start_hue))

    # At night, move towards purple/blue hues and reverse dimming
    if not day:
        hue = 1 - hue
        val = 1 - val

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

    # Sun objects for yesterfay, today, tomorrow
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


def draw_background(progress, period, day):
    """Given an amount of progress through the day or night, draw the
       background colour and overlay a blurred sun/moon."""

    # x-coordinate for sun/moon
    x = x_from_sun_moon_time(progress, period, WIDTH)

    # If it's day, then move right to left
    if day:
        x = WIDTH - x

    # Calculate position on sun/moon's curve
    centre = WIDTH / 2
    y = calculate_y_pos(x, centre)

    # Background colour
    background = map_colour(x, 80, mid_hue, day_hue, day)

    # New image for background colour
    img = Image.new('RGBA', (WIDTH, HEIGHT), color=background)
    draw = ImageDraw.Draw(img)

    # New image for sun/moon overlay
    overlay = Image.new('RGBA', (WIDTH, HEIGHT), color=(0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # Draw the sun/moon
    circle = circle_coordinates(x, y, sun_radius)
    overlay_draw.ellipse(circle, fill=(200, 200, 50, opacity))

    # Overlay the sun/moon on the background as an alpha matte
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
    if 30 < humidity < 70:
        description = "good"
    elif humidity >= 70:
        description = "wet"
    else:
        description = "dry"
    return description


def display_icon_weather_aqi(location, data, barometer_trend, icon_forecast, maxi_temp, mini_temp, air_quality_data, icon_air_quality_levels):
    progress, period, day, local_dt = sun_moon_time(city_name, time_zone)
    background = draw_background(progress, period, day)

    # Time.
    date_string = local_dt.strftime("%d %b %y").lstrip('0')
    time_string = local_dt.strftime("%H:%M") + '  ' + location
    img = overlay_text(background, (0 + margin, 0 + margin), time_string, font_smm)
    img = overlay_text(img, (WIDTH - margin, 0 + margin), date_string, font_smm, align_right=True)
    temp_string = f"{data['Temp'][1]:.0f}°C"
    img = overlay_text(img, (68, 18), temp_string, font_smm, align_right=True)
    spacing = font_smm.getsize(temp_string)[1] + 1
    if mini_temp is not None and maxi_temp is not None:
        range_string = f"{mini_temp:.0f}-{maxi_temp:.0f}"
    else:
        range_string = "------"
    img = overlay_text(img, (68, 18 + spacing), range_string, font_sm, align_right=True, rectangle=True)
    temp_icon = Image.open(path + "/icons/temperature.png")
    img.paste(temp_icon, (margin, 18), mask=temp_icon)

    # Humidity
    corr_humidity = data["Hum"][1]
    humidity_string = f"{corr_humidity:.0f}%"
    img = overlay_text(img, (68, 48), humidity_string, font_smm, align_right=True)
    spacing = font_smm.getsize(humidity_string)[1] + 1
    humidity_desc = describe_humidity(corr_humidity).upper()
    img = overlay_text(img, (68, 48 + spacing), humidity_desc, font_sm, align_right=True, rectangle=True)
    humidity_icon = Image.open(path + "/icons/humidity-" + humidity_desc.lower() + ".png")
    img.paste(humidity_icon, (margin, 48), mask=humidity_icon)
                
    # AQI
    max_aqi = ['All', 0]
    for aqi_factor in air_quality_data:
        aqi_factor_level = 0
        thresholds = data[aqi_factor][2]
        for level in range(len(thresholds)):
            if data[aqi_factor][1] > thresholds[level]:
                aqi_factor_level = level + 1
        if aqi_factor_level > max_aqi[1]:
            max_aqi = [aqi_factor, aqi_factor_level]
    aqi_string = f"{max_aqi[1]}: {max_aqi[0]}"
    img = overlay_text(img, (WIDTH - margin, 18), aqi_string, font_smm, align_right=True)
    spacing = font_smm.getsize(aqi_string)[1] + 1
    aqi_desc = icon_air_quality_levels[max_aqi[1]].upper()
    img = overlay_text(img, (WIDTH - margin - 1, 18 + spacing), aqi_desc, font_sm, align_right=True, rectangle=True)
    #aqi_icon = Image.open(path + "/icons/aqi-" + icon_air_quality_levels[max_aqi[1]].lower() +  ".png")
    aqi_icon = Image.open(path + "/icons/aqi.png")
    img.paste(aqi_icon, (80, 18), mask=aqi_icon)

    # Pressure
    pressure = data["Bar"][1]
    pressure_string = f"{int(pressure)} {barometer_trend}"
    img = overlay_text(img, (WIDTH - margin, 48), pressure_string, font_smm, align_right=True)
    pressure_desc = icon_forecast.upper()
    spacing = font_smm.getsize(pressure_string)[1] + 1
    img = overlay_text(img, (WIDTH - margin - 1, 48 + spacing), pressure_desc, font_sm, align_right=True, rectangle=True)
    pressure_icon = Image.open(path + "/icons/weather-" + pressure_desc.lower() +  ".png")
    img.paste(pressure_icon, (80, 48), mask=pressure_icon)

    # Display image
    disp.display(img)
    
def update_aio(mqtt_values, aio_format):
    print("Sending data to Adafruit IO")
    aio_error = False
    for feed in aio_format:
        aio_feed = aio_format[feed][0]
        if aio_format[feed][1]:
            try:
                aio.send_data(aio_feed.key, mqtt_values[feed][0])
            except RequestError:
                print('Adafruit IO Data Update Request Error', feed)
                aio_error = True
            except ThrottlingError:
                print('Adafruit IO Data Update Throttling Error', feed)
                aio_error = True
            except AdafruitIOError:
                print('Adafruit IO Data Update Error', feed)
                aio_error = True
            except MaxRetryError:
                print('Adafruit IO Data Update Max Retry Error', feed)
                aio_error = True
            except NewConnectionError:
                print('Adafruit IO Data Update New Connection Error', feed)
                aio_error = True
            except ConnectionError:
                print('Adafruit IO Data Update Connection Error', feed)
                aio_error = True
        else:
            try:
                aio.send_data(aio_feed.key, mqtt_values[feed])
            except RequestError:
                print('Adafruit IO Data Update Request Error', feed)
                aio_error = True
            except ThrottlingError:
                print('Adafruit IO Data Update Throttling Error', feed)
                aio_error = True
            except AdafruitIOError:
                print('Adafruit IO Data Update Error', feed)
                aio_error = True
            except MaxRetryError:
                print('Adafruit IO Data Update Max Retry Error', feed)
                aio_error = True
            except NewConnectionError:
                print('Adafruit IO Data Update New Connection Error', feed)
                aio_error = True
            except ConnectionError:
                print('Adafruit IO Data Update Connection Error', feed)
                aio_error = True
    if aio_error == False:
        print('Data sent to Adafruit IO')

# Compensation factors for temperature, humidity and air pressure
# Cubic polynomial temp comp coefficients adjusted by config's temp_offset
comp_temp_cub_a = 0.00012
comp_temp_cub_b = -0.01408
comp_temp_cub_c = 1.38546
comp_temp_cub_d = -8.17903
comp_temp_cub_d = comp_temp_cub_d + temp_offset
# Quadratic polynomial hum comp coefficients
comp_hum_quad_a = -0.0051
comp_hum_quad_b = 1.8070
comp_hum_quad_c = -0.2405
    
bar_comp_factor = 2
# Gas Comp Factors: Change in Rs per degree C, percent humidity or Hpa of pressure relative to baselines
red_temp_comp_factor = -1200
red_hum_comp_factor = -1200
red_bar_comp_factor = 1200
oxi_temp_comp_factor = -2000
oxi_hum_comp_factor = -1600
oxi_bar_comp_factor = 2000
nh3_temp_comp_factor = -2500
nh3_hum_comp_factor = -1000
nh3_bar_comp_factor = 1000

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
#font = ImageFont.truetype(UserFont, font_size_large)
#font = ImageFont.truetype("/home/pi/AQI/fonts/Asap/Asap-Bold.ttf", 16)
#smallfont = ImageFont.truetype("/home/pi/AQI/fonts/Asap/Asap-Bold.ttf", 10)
message = ""

# Set up icon display
# Set up air quality levels for icon display
icon_air_quality_levels = ['Great', 'OK', 'Alert', 'Poor', 'Bad']
# Values that alter the look of the background
blur = 50
opacity = 125
mid_hue = 0
day_hue = 25
sun_radius = 50
# Margins
margin = 3

# Create a own_data dict to store the data to be displayed in Display Everything
# Format: {Display Item: [Units, Current Value, [Level Thresholds], display_all_aq position]}
own_data = {"P1": ["ug/m3", 0, [6,17,27,35], 0], "P2.5": ["ug/m3", 0, [11,35,53,70], 1], "P10": ["ug/m3", 0, [16,50,75,100], 2],
            "Oxi": ["ppm", 0, [0.5, 1, 3, 5], 3], "Red": ["ppm", 0, [5, 30, 50, 75], 4], "NH3": ["ppm", 0, [5, 30, 50, 75], 5],
            "Temp": ["C", 0, [10,16,28,35], 6], "Hum": ["%", 0, [20,40,60,90], 7], "Bar": ["hPa", 0, [250,650,1013,1015], 8],
            "Lux": ["Lux", 1, [-1,-1,30000,100000], 9]}
data_in_display_all_aq =  ["P1", "P2.5", "P10", "Oxi", "Red", "NH3"]
# Defines the order in which display modes are chosen
display_modes = ["Icon Weather", "All Air", "P1", "P2.5", "P10", "Oxi", "Red", "NH3", "Forecast", "Temp", "Hum", "Bar", "Lux", "Status"]

# For graphing own display data
own_disp_values = {}
for v in own_data:
    own_disp_values[v] = [[1, 0]] * int(WIDTH/2)
                   
if enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor': # Prepare outdoor data, if it's required'             
    outdoor_data = {"P1": ["ug/m3", 0, [6,17,27,35], 0], "P2.5": ["ug/m3", 0, [11,35,53,70], 1], "P10": ["ug/m3", 0, [16,50,75,100], 2],
                    "Oxi": ["ppm", 0, [0.5, 1, 3, 5], 3], "Red": ["ppm", 0, [5, 30, 50, 75], 4], "NH3": ["ppm", 0, [10, 50, 100, 150], 5],
                    "Temp": ["C", 0, [10,16,28,35], 6], "Hum": ["%", 0, [20,40,60,80], 7], "Bar": ["hPa", 0, [250,650,1013,1015], 8],
                    "Lux": ["Lux", 1, [-1,-1,30000,100000], 9]}
    # For graphing outdoor display data
    outdoor_disp_values = {}
    for v in outdoor_data:
        outdoor_disp_values[v] = [[1, 0]] * int(WIDTH/2)
else:
    outdoor_data = {}
    outdoor_disp_values = []
# Used to define aqi components and their priority for the icon display.
air_quality_data = ["P1", "P2.5", "P10", "Oxi", "Red", "NH3"]
current_display_is_own = True # Start with own display
start_current_display = time.time()
indoor_outdoor_display_duration = 5 # Seconds for duration of indoor or outdoor display
outdoor_reading_captured = False # Used to determine whether the outdoor dispaly is ready.
update_icon_display = True

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
palette = [(128,128,255),          # Very Low
           (0,255,255),      # Low
           (0,255,0),          # Moderate
           (255,255,0),      # High
           (255,0,0)]          # Very High
    
luft_values = {} # To be sent to Luftdaten
mqtt_values = {} # To be sent to Home Manager or outdoor to indoor unit communications
maxi_temp = None
mini_temp = None


# Raspberry Pi ID to send to Luftdaten
id = "raspi-" + get_serial_number()

# Display Raspberry Pi serial and Wi-Fi status
logging.info("Raspberry Pi serial: {}".format(get_serial_number()))
logging.info("Wi-Fi: {}\n".format("connected" if check_wifi() else "disconnected"))

# Set up mqtt if required
if enable_send_data_to_homemanager or enable_receive_data_from_homemanager or enable_indoor_outdoor_functionality:
    es = ExternalSensors()
    client = mqtt.Client(mqtt_client_name)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqtt_broker_name, 1883, 60)
    client.loop_start()
  
if enable_adafruit_io:
    # Set up Adafruit IO
    print('Setting up Adafruit IO')
    aio = Client(aio_user_name, aio_key)
    aio_feed_prefix = aio_household_prefix + '-' + aio_location_prefix
    aio_format = {}
    try:
        aio_temp = aio.feeds(aio_feed_prefix + "-temperature")
        aio_hum = aio.feeds(aio_feed_prefix + "-humidity")
        aio_bar = aio.feeds(aio_feed_prefix + "-barometer")
        aio_lux = aio.feeds(aio_feed_prefix + "-lux")
        aio_p1 = aio.feeds(aio_feed_prefix + "-pm1")
        aio_p2_5 = aio.feeds(aio_feed_prefix + "-pm2-dot-5")
        aio_p10 = aio.feeds(aio_feed_prefix + "-pm10")
        aio_red = aio.feeds(aio_feed_prefix + "-reducing")
        aio_oxi = aio.feeds(aio_feed_prefix + "-oxidising")
        aio_nh3 = aio.feeds(aio_feed_prefix + "-ammonia")
        aio_format = {'Temp': [aio_temp, False], 'Hum': [aio_hum, True], 'Bar': [aio_bar, True], 'Lux': [aio_lux, False], 'P1': [aio_p1, False],
                      'P2.5': [aio_p2_5, False], 'P10': [aio_p10, False], 'Red': [aio_red, False], 'Oxi': [aio_oxi, False], 'NH3': [aio_nh3, False]}
        print('Adafruit IO set up completed')
    except RequestError:
        print('Adafruit IO set up Request Error')
    
# Take one reading from each climate and gas sensor on start up to stabilise readings
first_pressure_reading = bme280.get_pressure() + bar_comp_factor
first_temperature_reading = bme280.get_temperature()
first_humidity_reading = bme280.get_humidity()
use_external_temp_hum = False
use_external_barometer = False
first_light_reading = ltr559.get_lux()
first_proximity_reading = ltr559.get_proximity()
raw_red_rs, raw_oxi_rs, raw_nh3_rs = read_raw_gas()

# Set up startup R0 with no compensation (Compensation will be set up after warm up time)
red_r0, oxi_r0, nh3_r0 = read_raw_gas()
print("Startup R0. Red R0:", round(red_r0, 0), "Oxi R0:", round(oxi_r0, 0), "NH3 R0:", round(nh3_r0, 0))
# Capture temp/hum/bar to define variables
gas_calib_temp = first_temperature_reading
gas_calib_hum = first_humidity_reading
gas_calib_bar = first_pressure_reading - bar_comp_factor
gas_r0_calibration_after_warmup_completed = False
mqtt_values["Gas Calibrated"] = False # Only set to true after the gas sensor warmup time has been completed
gas_sensors_warmup_time = 6000
gas_daily_r0_calibration_completed = False
gas_daily_r0_calibration_hour = 3 # Adjust this to set the hour at which daily gas sensor calibrations are undertaken

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
update_time = 0
start_time = time.time()
barometer_available_time = start_time + 10945 # Initialise the time until a forecast is available (3 hours + the time taken before the first climate reading)
mqtt_values["Forecast"] = {"Valid": valid_barometer_history, "3 Hour Change": barometer_change, "Forecast": forecast}
mqtt_values["Bar"] = [gas_calib_bar, domoticz_forecast]
domoticz_hum_map = {"good": "1", "dry": "2", "wet": "3"}
mqtt_values["Hum"] = [gas_calib_hum, domoticz_hum_map["good"]]
path = os.path.dirname(os.path.realpath(__file__))

# Main loop to read data, display, and send to Luftdaten
try:
    while True:
        time_since_update = time.time() - update_time
        luft_values, mqtt_values, own_data, own_disp_values = read_pm_values(luft_values, mqtt_values, own_data, own_disp_values)
        if time_since_update > 145:
            update_icon_display = True
            (luft_values, mqtt_values, own_data, maxi_temp, mini_temp, own_disp_values, raw_red_rs, raw_oxi_rs, raw_nh3_rs,
             raw_temp, comp_temp, comp_hum, raw_hum, use_external_temp_hum,
             use_external_barometer, raw_barometer) = read_climate_gas_values(luft_values, mqtt_values, own_data,
                                                                              maxi_temp, mini_temp, own_disp_values,
                                                                              gas_r0_calibration_after_warmup_completed,
                                                                              gas_calib_temp, gas_calib_hum, gas_calib_bar)
            first_climate_reading_done = True
            print('Luftdaten Values', luft_values)
            print('mqtt Values', mqtt_values)
            if (indoor_outdoor_function == 'Indoor' and enable_send_data_to_homemanager):
                client.publish(indoor_mqtt_topic, json.dumps(mqtt_values))
            elif (indoor_outdoor_function == 'Outdoor' and (enable_indoor_outdoor_functionality or enable_send_data_to_homemanager)):
                client.publish(outdoor_mqtt_topic, json.dumps(mqtt_values))
            else:
                pass
            update_time = time.time()
            run_time = round((update_time - start_time), 0)
            if enable_climate_and_gas_logging:
                log_climate_and_gas(run_time, own_data, raw_red_rs, raw_oxi_rs, raw_nh3_rs, raw_temp, comp_temp, comp_hum, raw_hum, use_external_temp_hum, use_external_barometer, raw_barometer)
            if enable_adafruit_io and aio_format != {}: # Send data to Adafruit IO if enabled and set up
                update_aio(mqtt_values, aio_format)
            if enable_luftdaten: # Send data to Luftdaten if enabled
                resp = send_to_luftdaten(luft_values, id, enable_particle_sensor)
                logging.info("Luftdaten Response: {}\n".format("ok" if resp else "failed"))
            if "Forecast" in mqtt_values:
                mqtt_values.pop("Forecast") # Remove Forecast after sending it to home manager so that forecast data is only sent when updated
            # Write to the watchdog file
            with open('<Your Watchdog File Name Here>', 'w') as f:
                f.write('Enviro Script Alive')
        if first_climate_reading_done and (time.time() - barometer_log_time) >= 1200: # Read and update the barometer log if the first climate reading has been done and the last update was >= 20 minutes ago
            if barometer_log_time == 0: # If this is the first barometer log, record the time that a forecast will be available (3 hours)
                barometer_available_time = time.time() + 10800
            barometer_history, barometer_change, valid_barometer_history, barometer_log_time, forecast, barometer_trend, icon_forecast, domoticz_forecast = log_barometer(own_data['Bar'][1], barometer_history)
            mqtt_values["Forecast"] = {"Valid": valid_barometer_history, "3 Hour Change": round(barometer_change, 1), "Forecast": forecast}
            #mqtt_values["Bar"] = [own_data['Bar'][1], domoticz_forecast] # Add Domoticz Weather Forecast
            mqtt_values["Bar"][1] = domoticz_forecast # Add Domoticz Weather Forecast
        last_page, mode, start_current_display, current_display_is_own, update_icon_display = display_results(start_current_display, current_display_is_own, display_modes,
                                                                                         indoor_outdoor_display_duration, own_data, data_in_display_all_aq,
                                                                                          outdoor_data, outdoor_reading_captured, own_disp_values,outdoor_disp_values,
                                                                                         delay, last_page, mode, luft_values, mqtt_values, WIDTH, valid_barometer_history,
                                                                                         forecast, barometer_available_time, barometer_change, barometer_trend,
                                                                                         icon_forecast, maxi_temp, mini_temp, update_icon_display)
        if ((time.time() - start_time) > gas_sensors_warmup_time) and gas_r0_calibration_after_warmup_completed == False: # Calibrate gas sensors after warmup
            gas_calib_temp = raw_temp
            gas_calib_hum = raw_hum
            gas_calib_bar = raw_barometer
            red_r0, oxi_r0, nh3_r0 = read_raw_gas()
            print("Gas Sensor Calibration after Warmup. Red R0:", red_r0, "Oxi R0:", oxi_r0, "NH3 R0:", nh3_r0)
            print("Gas Calibration Baseline. Temp:", round(gas_calib_temp, 1), "Hum:", round(gas_calib_hum, 0), "Barometer:", round(gas_calib_bar, 1))
            reds_r0 = [red_r0] * 7
            oxis_r0 = [oxi_r0] * 7
            nh3s_r0 = [nh3_r0] * 7
            gas_calib_temps = [gas_calib_temp] * 7
            gas_calib_hums = [gas_calib_hum] * 7
            gas_calib_bars = [gas_calib_bar] * 7
            gas_r0_calibration_after_warmup_completed = True
        # Calibrate gas sensors daily, using average of daily readings over a week if not already done in the current day and if warmup calibration is completed
        # Compensates for gas sensor drift over time
        today=datetime.now()
        if int(today.strftime('%H')) == gas_daily_r0_calibration_hour and gas_daily_r0_calibration_completed == False and gas_r0_calibration_after_warmup_completed:
            print("Daily Gas Sensor Calibration. Old R0s. Red R0:", red_r0, "Oxi R0:", oxi_r0, "NH3 R0:", nh3_r0)
            print("Old Calibration Baseline. Temp:", round(gas_calib_temp, 1), "Hum:", round(gas_calib_hum, 0), "Barometer:", round(gas_calib_bar, 1)) 
            # Set new calibration baseline using 7 day rolling average
            gas_calib_temps = gas_calib_temps[1:] + [raw_temp]
            #print("Calib Temps", gas_calib_temps)
            gas_calib_temp = round(sum(gas_calib_temps)/float(len(gas_calib_temps)), 1)
            gas_calib_hums = gas_calib_hums[1:] + [raw_hum]
            #print("Calib Hums", gas_calib_hums)
            gas_calib_hum = round(sum(gas_calib_hums)/float(len(gas_calib_hums)), 0)
            gas_calib_bars = gas_calib_bars[1:] + [raw_barometer]
            #print("Calib Bars", gas_calib_bars)
            gas_calib_bar = round(sum(gas_calib_bars)/float(len(gas_calib_bars)), 1)
            # Update R0s based on new calibration baseline
            spot_red_r0, spot_oxi_r0, spot_nh3_r0, raw_red_r0, raw_oxi_r0, raw_nh3_r0 = comp_gas(gas_calib_temp, gas_calib_hum, gas_calib_bar, raw_temp, raw_hum, raw_barometer)
            # Convert R0s to 7 day rolling average
            reds_r0 = reds_r0[1:] + [spot_red_r0]
            #print("Reds R0", reds_r0)
            red_r0 = round(sum(reds_r0)/float(len(reds_r0)), 0)
            oxis_r0 = oxis_r0[1:] + [spot_oxi_r0]
            ##print("Oxis R0", oxis_r0)
            oxi_r0 = round(sum(oxis_r0)/float(len(oxis_r0)), 0)
            nh3s_r0 = nh3s_r0[1:] + [spot_nh3_r0]
            #print("NH3s R0", nh3s_r0)
            nh3_r0 = round(sum(nh3s_r0)/float(len(nh3s_r0)), 0)
            print('New R0s with compensation. Red R0:', red_r0, 'Oxi R0:', oxi_r0, 'NH3 R0:', nh3_r0)
            print("New Calibration Baseline. Temp:", round(gas_calib_temp, 1), "Hum:", round(gas_calib_hum, 0), "Barometer:", round(gas_calib_bar, 1))
            gas_daily_r0_calibration_completed = True
        if int(today.strftime('%H')) == (gas_daily_r0_calibration_hour + 1) and gas_daily_r0_calibration_completed:
            gas_daily_r0_calibration_completed = False
        time.sleep(1)
            
except KeyboardInterrupt:
    if enable_send_data_to_homemanager or enable_receive_data_from_homemanager:
        client.loop_stop()
    print('Keyboard Interrupt')

# Acknowledgements
# Based on code from:
# https://github.com/pimoroni/enviroplus-python/blob/master/examples/all-in-one.py
# https://github.com/pimoroni/enviroplus-python/blob/master/examples/combined.py
# https://github.com/pimoroni/enviroplus-python/blob/master/examples/compensated-temperature.py
# https://github.com/pimoroni/enviroplus-python/blob/master/examples/luftdaten.py
# https://github.com/pimoroni/enviroplus-python/blob/enviro-non-plus/examples/weather-and-light.py
# Weather Forecast based on www.worldstormcentral.co/law_of_storms/secret_law_of_storms.html by R. J. Ellis
