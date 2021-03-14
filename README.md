# enviro-monitor
This project uses a Raspberry Pi Zero W, a Pimoroni Enviro+ and a Plantower air quality sensor to monitor, display and report on air particles, gases, temperature, humidity, air pressure, light levels and noise levels. The option to monitor eCO2 and TVOC levels by adding an [SGP30 sensor](https://shop.pimoroni.com/products/sgp30-air-quality-sensor-breakout) is now available. The code is based on many of the Python [examples and libraries](https://github.com/pimoroni/enviroplus-python) [published](https://github.com/pimoroni/sgp30-python) by Pimoroni, with the following modifications and enhancements:

A basic weather forecast function, based on air pressure levels and changes.

The light level display in the superb [Weather and Light](https://github.com/pimoroni/enviroplus-python/blob/master/examples/weather-and-light.py) has been changed to air quality. The background hue now represents the air quality level instead of sun position and the sun position is now provided with a visible sun icon. It also uses the above-mentioned weather forecast information and has some minor changes to the humidity indicator.

The [Combined]( https://github.com/pimoroni/enviroplus-python/blob/master/examples/combined.py) function has been modified to provide a more visible display of each graph, to use graph colours based on level thresholds for each parameter and to only display parameters that have been measured. The display_everything method has also been modified to only show air quality parameters, in order to improve readability of the display.

The [All in One]( https://github.com/pimoroni/enviroplus-python/blob/master/examples/all-in-one.py) function has been modified to allow cycling through the monitor’s functions.

The accuracy of the temperature and humidity measurements has been improved by undertaking extensive testing and [regression analysis](https://github.com/roscoe81/enviro-monitor/blob/master/Regression_Analysis/Northcliff_Enviro_Monitor_Regression_Analyser.py) to develop more effective compensation algorithms. However on their own, even these improved algorithms were not sufficient and it was necessary to use a [3D-printed case](https://github.com/roscoe81/enviro-monitor/tree/master/3DP_Files) to separate the Enviro+ from the Raspberry Pi Zero W and connect them together via a ribbon cable. The case needs to be sheltered from the elements and the [base](https://github.com/roscoe81/enviro-monitor/blob/master/3DP_Files/Northcliff_EM_Base_01.stl) is only required if the unit is not mounted on a vertical surface. There is now a variant of the [case](https://github.com/roscoe81/enviro-monitor/blob/master/3DP_Files/Northcliff_EM_Case_Indoor_Plus.stl) and [cover](https://github.com/roscoe81/enviro-monitor/blob/master/3DP_Files/Northcliff_EM_Cover_Indoor_Plus.stl) for the Indoor Plus model (that monitors eCO2 and TVOC levels) to provide space and airflow for the SGP30 sensor.

There is also an option of adding a [weather cover](https://github.com/roscoe81/enviro-monitor/blob/master/3DP_Files/Northcliff_EM_Weather_Cover.stl) to provide additional protection from the elements. When using this cover, it is necessary to set "enable_display" in the [config.json](https://github.com/roscoe81/enviro-monitor/blob/master/Config/config.json) file to "false". That limits the display fuctionality to just air quality-based hue and serial number, as well as to changing the temperature and humidity compensation variables to mitigate the effect of the cover on the temperature and humidity sensor. Altitude compensation for the air pressure readings is set by the altitude parameter in the config.json file.

Likewise, testing and regression analysis was used to provide time-based drift, temperature, humidity and air pressure compensation for the Enviro+ gas sensors. Algorithms and clean-air calibration is included to provide gas sensor readings in ppm. A data logging function is provided to support the regression analysis. The log file needs to be converted to a valid json format before undertaking the regression analysis.

## Note: Even though the accuracy has been improved, the readings are still not thoroughly and accurately calibrated and should not be relied upon for critical purposes or applications.

Approximate noise levels measurements have been added to Version 6, based on [this repository](https://github.com/roscoe81/northcliff_spl_monitor). This feature is not to be used for accurate sound level measurements and only has a limited method of frequency compensation and calibration. This feature requires additional setup and after setup, needs to be enabled in the configuration file.

mqtt support is provided to use external temperature and humidity sensors (for data logging and regression analysis), interworking between the monitor and a [home automation system](https://github.com/roscoe81/Home-Manager) and to support interworking between outdoor and indoor Enviro Monitors. That latter interworking allows the display of an indoor Enviro Monitor to cycle between indoor and outdoor readings.

An alternative to using mqtt-linked indoor and outdoor Enviro Monitors to get outdoor readings on an indoor Enviro Monitor, is to configure the indoor Enviro Monitor to capture Luftdaten readings or Adafruit IO feeds from another Enviro Monitor.

[Luftdaten]( https://github.com/pimoroni/enviroplus-python/blob/master/examples/luftdaten.py) interworking has been modified to support the addition of noise measurements and the ability to use external temperature and humidity sensors via mqtt messages. Currently, Luftdaten doesn't allow three sensors per node without a manual request to their technical support. Once that is available, noise data can be sent by setting "enable_luftdaten_noise" in the config.json file to true.

The same [Enviro+ setup]( https://github.com/pimoroni/enviroplus-python/blob/master/README.md) is used and the [config.json](https://github.com/roscoe81/enviro-monitor/blob/master/Config/config.json) file parameters are used to customise its functionality. A description of the config.json file's parameters is [here](https://github.com/roscoe81/enviro-monitor/blob/master/Config/Config_README.md).

Setting up of the noise level measurements requires the following additional steps:

# Additional Noise Measurement Setup

Successful execution of this setup is necessary before enabling noise measurement in the config file.

sudo apt-get update

sudo apt-get-upgrade

curl -sSL https://get.pimoroni.com/enviroplus | bash

sudo python -m pip uninstall sounddevice

sudo pip3 install sounddevice==0.3.15

Follow instructions at:
https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test
including “Adding Volume Control”

Use the following instead of the documented text for ~/.asoundrc:

1.	#This section makes a reference to your I2S hardware, adjust the card name
2.	#to what is shown in arecord -l after card x: before the name in []
3.	#You may have to adjust channel count also but stick with default first
4.	pcm.dmic_hw {
5.	type hw
6.	card adau7002
7.	channels 2
8.	format S32_LE
9.	}
10.	 
11.	#This is the software volume control, it links to the hardware above and after
12.	#saving the .asoundrc file you can type alsamixer, press F6 to select
13.	#your I2S mic then F4 to set the recording volume and arrow up and down
14.	#to adjust the volume
15.	#After adjusting the volume - go for 50 percent at first, you can do
16.	#something like 
17.	#arecord -D dmic_sv -c2 -r 48000 -f S32_LE -t wav -V mono -v myfile.wav
18.	pcm.dmic_sv {
19.	type softvol
20.	slave.pcm dmic_hw
21.	control {
22.	name "Master Capture Volume"
23.	card adau7002
24.	}
25.	min_dB -3.0
26.	max_dB 30.0
27.	}

Use alsamixer to set adau7002 capture level to 50


A [User Guide](https://github.com/roscoe81/enviro-monitor/blob/master/User%20Guide/Northcliff%20Enviro%20Monitor%20User%20Guide-Gen.pdf) provides guidance on the use of the monitor.

## Adafruit IO Support
Support is provided for streaming weather forecast, air quality, temperature, humidity, air pressure, PM concentration, gas concentration, light levels, noise levels and, with the optional SGP30 sensor, eCO2 and TVOC data to Adafruit IO. This can be enabled and set up as follows:

### Config File Settings to Support Adafruit IO
The following fields in the Enviro Monitor’s config.json file need to be populated to supply data to the Adafruit IO feeds.

"enable_adafruit_io": Set to true to enable and false to disable Adafruit IO feeds,
  
"aio_user_name": "Your Adafruit IO User Name",
  
"aio_key": "Your Adafruit IO Key",
  
"aio_feed_window": Value between 0 and 9. Sets the start time for the one minute feed window (see Adafruit Throttling Control). Set to 0 if you only have one Enviro Monitor,

"aio_feed_sequence": Value between 0 and 3. Sets the feed update start time within the one minute feed update window (see Adafruit Throttling Control). Set to 0 if you only have one Enviro Monitor,

"aio_household_prefix": "The Adafruit IO Key Prefix for the household you’re monitoring (see Adafruit IO Naming Convention)",

"aio_location_prefix": "The Adafruit IO Key Prefix for the location of this particular Enviro Monitor.
Use ‘indoor’ for an indoor monitor or ‘outdoor’ for an outdoor monitor. (see Adafruit IO Naming Convention)",

"aio_package": Set to "Premium Plus" or "Premium Plus Noise" or "Premium" or "Premium Noise" or "Basic Air" or "Basic Combo"

You will need an Adafruit IO+ account in order to use ‘Premium Plus’, 'Premium Plus Noise', ‘Premium’ or 'Premium Noise' packages and an Enviro Monitor Indoor Plus (equipped with an SGP30 eCO2/TVOC sensor) for the ‘Premium Plus’ or 'Premium Plus Noise' packages (see Adafruit IO Packages)>",

### Adafruit IO Feed, Dashboard and Block Setup
The [script](https://github.com/roscoe81/enviro-monitor/blob/master/Adafruit%20IO%20Feed%20Setup/Northcliff_adafruit_io_feed_setup_Gen.py) sets up the Enviro Monitor’s Adafruit IO feeds, dashboards and blocks like [this example](https://io.adafruit.com/Roscoe81/dashboards/northcliff)

The script can set up multiple households and locations in one run, by populating the aio_feed_prefix dictionary with the required data. The format for aio_feed_prefix is:

aio_feed_prefix = {'Household 1 Name': {'key': 'household1key', 'package': 'aio_package', 'locations': {'Location1Name': 'location1key', 'Location2Name': 'location2key'}, 'visibility': 'public' or 'private'}, 'Household 2 Name': {'key': 'household2key', 'package': 'aio_package', 'locations': {'Location1Name': 'location1key'}, 'visibility': 'public' or 'private'}}
  
The Household Names and Household Keys need to be consistent with those defined in the relevant Enviro Monitors’ config.json files.

For example, if you only have one Enviro Monitor for your household, and if you’ve set "aio_household_prefix" to “home”, "aio_location_prefix" to “outdoor” and "aio_package" to “Premium” in your config.json file for that Enviro Monitor, and if you want the feeds, dashboards and blocks set with private visibility:

aio_feed_prefix = {‘Home’: {'key': 'home', 'package': Premium', 'locations': {‘Outdoor': 'outdoor’}, 'visibility': 'private'}}

If you have two Enviro Monitors for your household, and if you’ve set the config.json files as "aio_household_prefix" to “home” for both Enviro Monitors, "aio_location_prefix" to “outdoor” for the outdoor monitor and “indoor” for your indoor monitor, "aio_package" to “Premium” for your outdoor monitor and “Premium Plus” for your indoor monitor, and if you want the feeds, dashboards and blocks set with public visibility:

aio_feed_prefix = {‘Home’: {'key': 'home', 'package': Premium Plus', 'locations': {‘Outdoor': 'outdoor’, ‘Indoor’: ‘indoor’}, 'visibility': 'public'}}

The two other user-defined dictionaries are aio_user_name and aio_key. These need to be populated with the same user name and key that you used in your Enviro Monitor’s config.json file.

aio_user_name = "Your Adafruit IO User Name"
  
aio_key = "Your Adafruit IO Key"

### Adafruit IO Throttling Control
If enabled, Adafruit IO feed updates are generated every 10 minutes. The config file's aio_feed_window and aio_feed_sequence variables are used to minimise Adafruit IO throttling errors when collecting feeds from multiple Enviro Monitors. The aio_feed_window variable can be a value between 0 and 9 to set the start time for a one minute feed update window. 0 opens the window at 0, 10, 20, 30, 40 and 50 minutes past the hour, 1 opens the window at 1, 11, 21, 31, 41, and 51 minutes past the hour, 2 opens the window at 2, 12, 22, 32, 42 and 52 minutes past the hour, and so on. The aio_feed_sequence variable can be a value between 0 and 3 to set the feed update start time within the one minute feed update window. 0 starts the feed update immediately after the window opens, 1 delays the start by 15 seconds, 2 by 30 seconds and 3 by 45 seconds.

### Adafruit IO Naming Convention
The naming convention for each Enviro Monitor’s Adafruit IO feeds, dashboards or blocks, is to use the name of the household, followed by the location of the relevant Enviro Monitor’s location within that household, as a prefix for each feed, dashboard or block. You choose a suitable name for "aio_household_prefix", and "aio_location_prefix" can either be “indoor” or “outdoor”. For example, setting “aio_household_prefix" to “home” and "aio_location_prefix" to “outdoor” will set the prefix of each feed’s name as “Home Outdoor “ and the prefix of each feed’s key as “home-outdoor-“. So, the Temperature Feed will have the name “Home Outdoor Temperature” and the key “home-outdoor-temperature”. The dashboard will have the name “Home” and key “home” and the temperature gauge block within that dashboard will have the name “Outdoor Temperature Gauge” and the key “outdoor-temperature-gauge”.

### Adafruit IO Packages
Six Adafruit IO package options are available: "Premium" with 14 data feeds per Enviro, "Premium Noise" with 17 data feeds per Enviro, "Premium Plus" with 16 data feeds per Enviro (i.e. the addition of eCO2 and TVOC through the optional SGP30 sensor), "Premium Plus Noise" with 19 data feeds per Enviro which all need an Adafruit IO+ account; "Basic Air" with 5 air quality data streams (Air Quality Level, Air Quality Text, PM1, PM2.5 and PM10) and "Basic Combo" with 5 air quality/climate streams (Air Quality Level, Weather Forecast Icon, Temperature, Humidity and Air Pressure). 

### Use of Adafruit IO Noise Packages
Using the "Premium Noise" and "Premium Plus Noise" Adafruit IO packages requires configuring and enabling Noise measurements in the Enviro, using the relevant setup instructions.
Version 6.5 changes the noise feeds and dashboards to show Max, Min and Mean noise levels between feed updates, whereas prior versions only showed Max noise levels between feed updates.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details

## Acknowledgements

Weather Forecast based on www.worldstormcentral.co/law_of_storms/secret_law_of_storms.html by R. J. Ellis
