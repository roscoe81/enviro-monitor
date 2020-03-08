#!/usr/bin/env python3
#Northcliff Environment Monitor - 3.43 - Gen
# Requires Home Manager >=8.43 with new mqtt message topics for indoor and outdoor and new parsed_json labels

import paho.mqtt.client as mqtt
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
from astral.geocoder import database, lookup
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
#from subprocess import PIPE, Popen, check_output
from subprocess import check_output
from PIL import Image, ImageDraw, ImageFont, ImageFilter
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus
import logging

# Config Setup
enable_send_data_to_homemanager = True
enable_receive_data_from_homemanager = True
enable_indoor_outdoor_functionality = True
mqtt_broker_name = "<Your mqtt broker name here" # Only required if at least one of the previous three flags are True
enable_luftdaten = True
enable_climate_and_gas_logging = True
enable_particle_sensor = True
incoming_temp_hum_mqtt_topic = 'domoticz/out'
incoming_temp_hum_mqtt_sensor_name = 'Rear Balcony Climate'
indoor_outdoor_function = 'Outdoor'
mqtt_client_name = indoor_outdoor_function + ' Northcliff EM0'
outdoor_mqtt_topic = 'Outdoor EM0'
indoor_mqtt_topic = 'Indoor EM0'

# The city and timezone that you want to display.
city_name = "Sydney"
time_zone = "Australia/Sydney"

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
def read_climate_gas_values(cpu_temps, luft_values, mqtt_values, own_data, maxi_temp, mini_temp, own_disp_values):
    current_time = time.time()
    use_internal_temp_hum = True
    if enable_receive_data_from_homemanager:
        use_internal_temp_hum = not(es.check_valid_readings(current_time)) # Don't use internal temp/hum if there's a valid external reading
    if use_internal_temp_hum:
        print("Internal Temp/Hum Sensor")
        raw_temp, comp_temp, cpu_temps, avg_cpu_temp = adjusted_temperature(cpu_temps)
        luft_values["temperature"] = "{:.2f}".format(comp_temp)
        own_data["Temp"][1] = round(comp_temp, 1)
        comp_hum, raw_hum, dew_point = adjusted_humidity(raw_temp, comp_temp)
        luft_values["humidity"] = "{:.2f}".format(comp_hum)
        own_data["Hum"][1] = round(comp_hum, 1)
    else: # Use external temp/hum sensor but still capture raw temp and raw hum for gas compensation
        print("External Temp/Humidity Sensor")
        luft_values["temperature"] = es.temperature
        own_data["Temp"][1] = float(luft_values["temperature"])
        luft_values["humidity"] = es.humidity
        own_data["Hum"][1] = float(luft_values["humidity"])
        raw_temp = bme280.get_temperature()
        raw_hum = bme280.get_humidity()
    own_disp_values["Temp"] = own_disp_values["Temp"][1:] + [[own_data["Temp"][1], 1]]
    mqtt_values["Temp"] = own_data["Temp"][1]
    own_disp_values["Hum"] = own_disp_values["Hum"][1:] + [[own_data["Hum"][1], 1]]
    mqtt_values["Hum"] = own_data["Hum"][1]
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
    own_data["Bar"][1] = round((bme280.get_pressure() + bar_comp_factor), 1)# Used for storing and displaying all readings
    own_disp_values["Bar"] = own_disp_values["Bar"][1:] + [[own_data["Bar"][1], 1]]
    mqtt_values["Bar"] = own_data["Bar"][1]
    luft_values["pressure"] = "{:.2f}".format(own_data["Bar"][1] * 100)
    red_in_ppm, oxi_in_ppm, nh3_in_ppm, red_rs, oxi_rs, nh3_rs = read_gas_in_ppm(raw_temp, raw_hum, own_data["Bar"][1])
    own_data["Red"][1] = round(red_in_ppm, 2)
    own_disp_values["Red"] = own_disp_values["Red"][1:] + [[own_data["Red"][1], 1]]
    mqtt_values["Red"] = own_data["Red"][1]
    own_data["Oxi"][1] = round(oxi_in_ppm, 2)
    own_disp_values["Oxi"] = own_disp_values["Oxi"][1:] + [[own_data["Oxi"][1], 1]]
    mqtt_values["Oxi"] = own_data["Oxi"][1]
    own_data["NH3"][1] = round(nh3_in_ppm, 2)
    own_disp_values["NH3"] = own_disp_values["NH3"][1:] + [[own_data["NH3"][1], 1]]
    mqtt_values["NH3"] = own_data["NH3"][1]
    proximity = ltr559.get_proximity()
    if proximity < 500:
        own_data["Lux"][1] = round(ltr559.get_lux(), 1)
    else:
        own_data["Lux"][1] = 1
    own_disp_values["Lux"] = own_disp_values["Lux"][1:] + [[own_data["Lux"][1], 1]]
    mqtt_values["Lux"] = own_data["Lux"][1]
    return cpu_temps, luft_values, mqtt_values, own_data, maxi_temp, mini_temp, own_disp_values, red_rs, oxi_rs, nh3_rs
    
def read_gas_in_ppm(raw_temp, raw_hum, barometer):
    gas_data = gas.read_all()
    red_rs, oxi_rs, nh3_rs = comp_gas(gas_data, raw_temp, raw_hum, barometer)
    #red_rs = gas_data.reducing
    #oxi_rs = gas_data.oxidising
    #nh3_rs = gas_data.nh3
    print("Red Rs:", round(red_rs, 0), "Oxi Rs:", round(oxi_rs, 0), "NH3 Rs:", round(nh3_rs, 0))
    red_in_ppm = math.pow(10, -1.25 * math.log10(red_rs/red_r0) + 0.64)
    oxi_in_ppm = math.pow(10, math.log10(oxi_rs/oxi_r0) - 0.8129)
    nh3_in_ppm = math.pow(10, -1.8 * math.log10(nh3_rs/nh3_r0) - 0.163)
    return red_in_ppm, oxi_in_ppm, nh3_in_ppm, red_rs, oxi_rs, nh3_rs

def calibrate_gas():
    #print("R0 Calibration. Old R0.  Red R0:", red_r0, "Oxi R0:", oxi_r0, "NH3 R0:", nh3_r0)
    raw_temp = bme280.get_temperature()
    raw_hum = bme280.get_humidity()
    barometer = bme280.get_pressure() + bar_comp_factor
    calibration_gas_reading = gas.read_all()
    red_r0, oxi_r0, nh3_r0 = comp_gas(calibration_gas_reading, raw_temp, raw_hum, barometer)
    return red_r0, oxi_r0, nh3_r0

def comp_gas(gas_data, raw_temp, raw_hum, barometer):
    gas_temp_diff = raw_temp - gas_temp_baseline
    gas_hum_diff = raw_hum - gas_hum_baseline
    gas_bar_diff = barometer - gas_bar_baseline
    raw_red_rs = round(gas_data.reducing, 0)
    comp_red_rs = round(raw_red_rs - (red_temp_comp_factor * gas_temp_diff + red_hum_comp_factor * gas_hum_diff + red_bar_comp_factor * gas_bar_diff), 0)
    raw_oxi_rs = round(gas_data.oxidising, 0)
    comp_oxi_rs = round(raw_oxi_rs - (oxi_temp_comp_factor * gas_temp_diff + oxi_hum_comp_factor * gas_hum_diff + oxi_bar_comp_factor * gas_bar_diff), 0)
    raw_nh3_rs = round(gas_data.nh3, 0)
    comp_nh3_rs = round(raw_nh3_rs - (nh3_temp_comp_factor * gas_temp_diff + nh3_hum_comp_factor * gas_hum_diff + nh3_bar_comp_factor * gas_bar_diff), 0)
    print("Gas Compensation. Raw Red Rs:", raw_red_rs, "Comp Red Rs:", comp_red_rs, "Raw Oxi Rs:", raw_oxi_rs, "Comp Oxi Rs:", comp_oxi_rs,
          "Raw NH3 Rs:", raw_nh3_rs, "Comp NH3 Rs:", comp_nh3_rs)
    return comp_red_rs, comp_oxi_rs, comp_nh3_rs
    
    
def adjusted_temperature(cpu_temps):
    cpu_temp = get_cpu_temperature()        
    # Smooth out with some averaging to decrease jitter
    cpu_temps = cpu_temps[1:] + [cpu_temp]
    avg_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
    raw_temp = bme280.get_temperature()
    cpu_temp_factor = cpu_temp_factor_slope * (avg_cpu_temp - raw_temp) + cpu_temp_factor_intercept
    raw_temp_without_cpu_impact = raw_temp - cpu_temp_factor
    comp_temp = comp_temp_slope * raw_temp_without_cpu_impact + comp_temp_intercept
    return raw_temp, comp_temp, cpu_temps, avg_cpu_temp

def adjusted_humidity(raw_temp, comp_temp):
    raw_hum = bme280.get_humidity()
    dew_point = (243.04 * (math.log(raw_hum / 100) + ((17.625 * raw_temp) / (243.04 + raw_temp)))) / (17.625 - math.log(raw_hum / 100) - (17.625 * raw_temp / (243.04 + raw_temp)))
    temp_adjusted_hum = 100 * (math.exp((17.625 * dew_point)/(243.04 + dew_point)) / math.exp((17.625 * comp_temp) / (243.04 + comp_temp)))
    comp_hum = comp_hum_slope * temp_adjusted_hum + comp_hum_intercept
    return min(100, comp_hum), raw_hum, dew_point
    
def log_climate_and_gas(run_time, cpu_temps, own_data, red_rs, oxi_rs, nh3_rs): # Used to log climate and gas data to create compensation algorithms
    raw_temp, comp_temp, cpu_temps, avg_cpu_temp = adjusted_temperature(cpu_temps)
    comp_hum, raw_hum, dew_point = adjusted_humidity(raw_temp, comp_temp)
    #print('CPU Temps:', cpu_temps, 'Raw Temp:', raw_temp, 'Raw Hum:', raw_hum)
    avg_cpu_temp = round(avg_cpu_temp, 2)
    raw_temp = round(raw_temp, 2)
    raw_hum = round(raw_hum, 2)
    comp_temp = round(comp_temp, 2)
    comp_hum = round(comp_hum, 2)
    dew_point = round(dew_point, 2)
    red_rs = round(red_rs, 0)
    oxi_rs = round(oxi_rs, 0)
    nh3_rs = round(nh3_rs, 0)
    climate_log_data = {'CPU Temperature': avg_cpu_temp, 'Raw Temperature': raw_temp, 'Output Temp': comp_temp, 'Real Temperature': own_data["Temp"][1],
                         'Raw Humidity': raw_hum, 'Dew Point': dew_point, 'Output Humidity': comp_hum, 'Real Humidity': own_data["Hum"][1], 'Run Time': run_time,
                          "Bar": own_data["Bar"][1], "Oxi": own_data["Oxi"][1], "Red": own_data["Red"][1], "NH3": own_data["NH3"][1], "OxiRS": oxi_rs, "RedRS": red_rs, "NH3RS": nh3_rs}
    print('Logging Climate Data.', climate_log_data)
    with open ('<Your log file name here>', 'a') as f:
        f.write(',\n' + json.dumps(climate_log_data))
    return cpu_temps

# Get CPU temperature to use for compensation
def get_cpu_temperature():
    #process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE, universal_newlines=True)
    #output, _error = process.communicate()
    #return float(output[output.index('=') + 1:output.rindex("'")])
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        temp = f.read()
        temp = int(temp) / 1000.0
    return temp

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
        client.subscribe(incoming_temp_hum_mqtt_topic) # Subscribe to the topic with the external temp/hum data
    if enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor':
        client.subscribe(outdoor_mqtt_topic)

def on_message(client, userdata, msg):
    decoded_payload = str(msg.payload.decode("utf-8"))
    parsed_json = json.loads(decoded_payload)
    if msg.topic == incoming_temp_hum_mqtt_topic and parsed_json['name'] == incoming_temp_hum_mqtt_sensor_name: # Identify temp/hum sensor
        es.capture_temp_humidity(parsed_json)
    if enable_indoor_outdoor_functionality and indoor_outdoor_function == 'Indoor' and msg.topic == outdoor_mqtt_topic:
        capture_outdoor_data(parsed_json)
    
def capture_outdoor_data(parsed_json):
    global outdoor_reading_captured
    global outdoor_data
    global outdoor_maxi_temp
    global outdoor_mini_temp
    global outdoor_disp_values
    for reading in outdoor_data:
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
        message = "Barometer {:.1f} hPa\n3Hr Change {:.1f} hPa\n{}".format(barometer, barometer_change, forecast)
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
        #if check_time - self.barometer_update_time < 500:
            #valid_barometer_reading = True
        #else:
            #valid_barometer_reading = False
        if check_time - self.temp_humidity_update_time < 500:
            valid_temp_humidity_reading = True
        else:
            valid_temp_humidity_reading = False
        return valid_temp_humidity_reading

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
        forecast, icon_forecast = analyse_barometer(barometer_change, barometer)
    else:
        valid_barometer_history=False
        forecast = 'Insufficient Data'
        icon_forecast = 'Wait'
        barometer_change = 0
        barometer_trend = ''
    #print("Log Barometer")
    #print("Result", barometer_history, "Valid Barometer History is", valid_barometer_history, "3 Hour Barometer Change is", round(barometer_change,2), "millibars")
    return barometer_history, barometer_change, valid_barometer_history, barometer_log_time, forecast, barometer_trend, icon_forecast

def analyse_barometer(barometer_change, barometer):
    if barometer<1009:
        if barometer_change>-1.1 and barometer_change<6:
            forecast = 'Clearing and Colder'
            icon_forecast = 'Fair'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
        elif barometer_change<=-1.1 and barometer_change>=-4:
            forecast = 'Rain and Wind'
            icon_forecast = 'Rain'
        elif barometer_change<-4 and barometer_change>-10:
            forecast = 'Storm'
            icon_forecast = 'Storm'
        else:
            forecast = 'Storm and Gale'
            icon_forecast = 'Gale'
    elif barometer>=1009 and barometer <=1018:
        if barometer_change>-4 and barometer_change<1.1:
            forecast = 'No Change'
            icon_forecast = 'Stable'
        elif barometer_change>=1.1 and barometer_change<=6 and barometer<=1015:
            forecast = 'No Change'
            icon_forecast = 'Stable'
        elif barometer_change>=1.1 and barometer_change<=6 and barometer>1015:
            forecast = 'Poorer Weather'
            icon_forecast = 'Poorer'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
        else:
            forecast = 'Rain and Wind'
            icon_forecast = 'Rain'
    elif barometer>1018 and barometer <=1023:
        if barometer_change>0 and barometer_change<1.1:
            forecast = 'No Change'
            icon_forecast = 'Stable'
        elif barometer_change>=1.1 and barometer_change<6:
            forecast = 'Poorer Weather'
            icon_forecast = 'Poorer'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
        elif barometer_change>-1.1 and barometer_change<=0:
            forecast = 'Fair Weather with\nSlight Temp Change'
            icon_forecast = 'Fair'
        elif barometer_change<=-1.1 and barometer_change>-4:
            forecast = 'No Change but\nRain in 24 Hours'
            icon_forecast = 'Stable'
        else:
            forecast = 'Rain, Wind and\n Higher Temp'
            icon_forecast = 'Rain'
    else: # barometer>1023
        if barometer_change>0 and barometer_change<1.1:
            forecast = 'Fair Weather'
            icon_forecast = 'Fair'
        elif barometer_change>-1.1 and barometer_change<=0:
            forecast = 'Fair Weather with\nNo Marked Temp Change'
            icon_forecast = 'Fair'
        elif barometer_change>=1.1 and barometer_change<6:
            forecast = 'Poorer Weather'
            icon_forecast = 'Poorer'
        elif barometer_change>=6 and barometer_change<10:
            forecast = 'Strong Wind Warning'
            icon_forecast = 'Windy'
        elif barometer_change>=10:
            forecast = 'Gale Warning'
            icon_forecast = 'Gale'
        elif barometer_change<=-1.1 and barometer_change>-4:
            forecast = 'Fair Weather and\nSlowly Rising Temp'
            icon_forecast = 'Fair'
        else:
            forecast = 'Warming Trend'
            icon_forecast = 'Fair'
    print('3 hour barometer change is '+str(round(barometer_change,1))+' millibars with a current reading of '+str(round(barometer,1))+' millibars. The weather forecast is '+forecast) 
    return forecast, icon_forecast

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


def sun_moon_time(dt, city_name, time_zone):
    """Calculate the progress through the current sun/moon period (i.e day or
       night) from the last sunrise or sunset, given a datetime object 't'."""

    city = lookup(city_name, database())

    # Datetime objects for yesterday, today, tomorrow
    today = dt.date()
    dt = pytz.timezone(time_zone).localize(dt)
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
    if sunrise_today < dt < sunset_today:
        day = True
        period = sunset_today - sunrise_today
        mid = sunrise_today + (period / 2)
        progress = dt - sunrise_today

    elif dt > sunset_today:
        day = False
        period = sunrise_tomorrow - sunset_today
        mid = sunset_today + (period / 2)
        progress = dt - sunset_today

    else:
        day = False
        period = sunrise_today - sunset_yesterday
        mid = sunset_yesterday + (period / 2)
        progress = dt - sunset_yesterday

    # Convert time deltas to seconds
    progress = progress.total_seconds()
    period = period.total_seconds()

    return (progress, period, day)


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
    """Convert relative humidity into good/bad description."""
    if 30 < humidity < 70:
        description = "good"
    elif humidity >= 70:
        description = "wet"
    else:
        description = "dry"
    return description


def display_icon_weather_aqi(location, data, barometer_trend, icon_forecast, maxi_temp, mini_temp, air_quality_data, icon_air_quality_levels):
    dt = datetime.now()
#   dt += timedelta(minutes=5)
    progress, period, day = sun_moon_time(dt, city_name, time_zone)
    background = draw_background(progress, period, day)

    # Time.
    date_string = dt.strftime("%d %b %y").lstrip('0')
    time_string = dt.strftime("%H:%M") + '  ' + location
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

# Compensation factors for temperature, humidity and air pressure
cpu_temp_factor_slope = -0.0646 # Linear Regression to minimise impact of CPU temp on Raw Temp
cpu_temp_factor_intercept = 18.7811
comp_temp_slope = 0.8135 # Linear Regression to adjust Raw Temp (with impact of CPU Temp removed) to provide compensated temp
comp_temp_intercept = 13.9981
comp_hum_slope = 0.9425 # Linear Regression to adjust temperature-adjusted raw relative humidity to provide compensated relative humidity
comp_hum_intercept = 9.295

bar_comp_factor = 2.4
# Gas Comp Factors: Change in Rs per degree C, percent humidity or Bar of pressure relative to baselines
red_temp_comp_factor = -9000
red_hum_comp_factor = -1750
red_bar_comp_factor = 0
oxi_temp_comp_factor = -10000
oxi_hum_comp_factor = -646
oxi_bar_comp_factor = 2639
nh3_temp_comp_factor = -16000
nh3_hum_comp_factor = 0
nh3_bar_comp_factor = 1526
gas_temp_baseline = 23
gas_hum_baseline = 50
gas_bar_baseline = 1013

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

# Set up CPU Temps list
cpu_temps = [get_cpu_temperature()] * 5

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

# Take one reading from each climate sensor on start up to stabilise readings
first_pressure_reading = bme280.get_pressure() + bar_comp_factor
first_temperature_reading = bme280.get_temperature()
first_humidity_reading = bme280.get_humidity()
first_light_reading = ltr559.get_lux()
first_proximity_reading = ltr559.get_proximity()
first_gas_reading = gas.read_all()
red_rs, oxi_rs, nh3_rs = comp_gas(first_gas_reading, first_temperature_reading, first_humidity_reading, first_pressure_reading)

red_r0, oxi_r0, nh3_r0 = calibrate_gas() # Set up startup R0
print('Startup gas sensor R0s are. Red R0:', red_r0, 'Oxi R0:', oxi_r0, 'NH3 R0:', nh3_r0)
# Set up lists to permit gas sensor drift compensation
reds_r0 = [red_r0] * 7
oxis_r0 = [oxi_r0] * 7
nh3s_r0 = [nh3_r0] * 7
r0_calibration_after_warmup_completed = False
gas_sensors_warmup_time = 6000
daily_r0_calibration_completed = False
daily_r0_calibration_hour = 3 # Adjust this to set the hour at which daily gas sensor calibrations are undertaken

# Set up weather forecast
first_climate_reading_done = False
barometer_history = [0.00 for x in range (9)]
barometer_change = 0
barometer_trend = ''
barometer_log_time = 0
valid_barometer_history = False
forecast = 'Insufficient Data'
icon_forecast = 'Wait'
update_time = 0
start_time = time.time()
barometer_available_time = start_time + 10945 # Initialise the time until a forecast is available (3 hours + the time taken before the first climate reading)
mqtt_values["Forecast"] = {"Valid": valid_barometer_history, "3 Hour Change": barometer_change, "Forecast": forecast}
path = os.path.dirname(os.path.realpath(__file__))

# Main loop to read data, display, and send to Luftdaten
try:
    while True:
        time_since_update = time.time() - update_time
        luft_values, mqtt_values, own_data, own_disp_values = read_pm_values(luft_values, mqtt_values, own_data, own_disp_values)
        if time_since_update > 145:
            update_icon_display = True
            cpu_temps, luft_values, mqtt_values, own_data, maxi_temp, mini_temp, own_disp_values, red_rs, oxi_rs, nh3_rs = read_climate_gas_values(cpu_temps, luft_values, mqtt_values, own_data, maxi_temp, mini_temp, own_disp_values)
            first_climate_reading_done = True
            print('Luftdaten Values', luft_values)
            print('mqtt Values', mqtt_values)
            if (indoor_outdoor_function == 'Indoor' and enable_send_data_to_homemanager) or (indoor_outdoor_function == 'Outdoor' and enable_send_data_to_homemanager
                                                                                     and enable_indoor_outdoor_functionality == False):
                client.publish(indoor_mqtt_topic, json.dumps(mqtt_values))
            elif indoor_outdoor_function == 'Outdoor' and enable_indoor_outdoor_functionality:
                client.publish(outdoor_mqtt_topic, json.dumps(mqtt_values))
            else:
                pass
            if enable_luftdaten:
                resp = send_to_luftdaten(luft_values, id, enable_particle_sensor)
                logging.info("Luftdaten Response: {}\n".format("ok" if resp else "failed"))
            update_time = time.time()
            run_time = round((update_time - start_time), 0)
            if enable_climate_and_gas_logging and enable_receive_data_from_homemanager: # Log data if activated and if there are external readings available
                cpu_temps = log_climate_and_gas(run_time, cpu_temps, own_data, red_rs, oxi_rs, nh3_rs)
            elif enable_climate_and_gas_logging and enable_receive_data_from_homemanager == False: # Warn that logging is not possible if there are no external readings available
                print("Unable to log climate data. External data not available")
            else:
                pass
            mqtt_values = {} # Clear mqtt_values after sending to home manager so that forecast data is only sent when updated
        if first_climate_reading_done and (time.time() - barometer_log_time) >= 1200: # Read and update the barometer log if the first climate reading has been done and the last update was >= 20 minutes ago
            if barometer_log_time == 0: # If this is the first barometer log, record the time that a forecast will be available (3 hours)
                barometer_available_time = time.time() + 10800
            barometer_history, barometer_change, valid_barometer_history, barometer_log_time, forecast, barometer_trend, icon_forecast = log_barometer(own_data['Bar'][1], barometer_history)
            mqtt_values["Forecast"] = {"Valid": valid_barometer_history, "3 Hour Change": round(barometer_change, 1), "Forecast": forecast}
        last_page, mode, start_current_display, current_display_is_own, update_icon_display = display_results(start_current_display, current_display_is_own, display_modes,
                                                                                         indoor_outdoor_display_duration, own_data, data_in_display_all_aq,
                                                                                          outdoor_data, outdoor_reading_captured, own_disp_values,outdoor_disp_values,
                                                                                         delay, last_page, mode, luft_values, mqtt_values, WIDTH, valid_barometer_history,
                                                                                         forecast, barometer_available_time, barometer_change, barometer_trend,
                                                                                         icon_forecast, maxi_temp, mini_temp, update_icon_display)
        time.sleep(1)
        if ((time.time() - start_time) > gas_sensors_warmup_time) and r0_calibration_after_warmup_completed == False: # Calibrate gas sensors after warmup
            print('Gas Sensor Calibration after Warmup. Pre calibration R0s were. Red R0:', red_r0, 'Oxi R0:', oxi_r0, 'NH3 R0:', nh3_r0)
            red_r0, oxi_r0, nh3_r0 = calibrate_gas()
            print('Post calibration R0s are Red R0:', red_r0, 'Oxi R0:', oxi_r0, 'NH3 R0:', nh3_r0)
            reds_r0 = [red_r0] * 7
            oxis_r0 = [oxi_r0] * 7
            nh3s_r0 = [nh3_r0] * 7
            r0_calibration_after_warmup_completed = True
        # Calibrate gas sensors daily, using average of daily readings over a week
        today=datetime.now()
        if int(today.strftime('%H')) == daily_r0_calibration_hour and daily_r0_calibration_completed == False:
            print('Daily Gas Sensor Calibration. Pre calibration R0s were. Red R0:', red_r0, 'Oxi R0:', oxi_r0, 'NH3 R0:', nh3_r0)
            spot_red_r0, spot_oxi_r0, spot_nh3_r0 = calibrate_gas()
            reds_r0 = reds_r0[1:] + [spot_red_r0]
            red_r0 = round(sum(reds_r0)/float(len(reds_r0)), 0)
            oxis_r0 = oxis_r0[1:] + [spot_oxi_r0]
            oxi_r0 = round(sum(oxis_r0)/float(len(oxis_r0)), 0)
            nh3s_r0 = nh3s_r0[1:] + [spot_nh3_r0]
            nh3_r0 = round(sum(nh3s_r0)/float(len(nh3s_r0)), 0)
            print('Post calibration R0s are Red R0:', red_r0, 'Oxi R0:', oxi_r0, 'NH3 R0:', nh3_r0)
            daily_r0_calibration_completed = True
        if int(today.strftime('%H')) == (daily_r0_calibration_hour + 1) and daily_r0_calibration_completed:
            daily_r0_calibration_completed = False       
            
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
# Relative Humidity Temperature adjustment using August-Roche_Magnus approximation using https://bmcnoldy.rsmas.miami.edu/Humidity.html
# Weather Forecast based on www.worldstormcentral.co/law_of_storms/secret_law_of_storms.html by R. J. Ellis

