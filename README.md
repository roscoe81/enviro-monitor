# enviro-monitor
This project uses a Raspberry Pi Zero W, a Pimoroni Enviro+ and a Plantower air quality sensor to monitor, display and report on air particles, gases, temperature, humidity, air pressure and light levels. It’s based on many of the Python [examples and libraries]( https://github.com/pimoroni/enviroplus-python) published by Pimoroni, with the following modifications and enhancements:

A basic weather forecast function, based on air pressure levels and changes.

The light level display in the superb [Weather and Light](https://github.com/pimoroni/enviroplus-python/blob/master/examples/weather-and-light.py) has been changed to air quality. It also uses the above-mentioned weather forecast information and has some minor changes to the humidity indicator.

The [Combined]( https://github.com/pimoroni/enviroplus-python/blob/master/examples/combined.py) has been modified to provide a more visible display of each graph, to use graph colours based on level thresholds for each parameter and to only display parameters that have been measured. The display_everything method has also been modified to only show air quality parameters, in order to improve readability of the display.

The [All in One]( https://github.com/pimoroni/enviroplus-python/blob/master/examples/all-in-one.py) function has been modified to allow cycling through the monitor’s functions.

The accuracy of the temperature and humidity measurements has been improved by undertaking extensive testing and [regression analysis](https://github.com/roscoe81/enviro-monitor/blob/master/Regression_Analysis/Northcliff_Enviro_Monitor_Regression_Analyser.py) to develop more effective compensation algorithms. However on their own, even these improved algorithms were not sufficient and it was necessary to use a [3D-printed case](https://github.com/roscoe81/enviro-monitor/tree/master/3DP_Files) to separate the Enviro+ from the Raspberry Pi Zero W and connect them together via a ribbon cable. The case needs to be sheltered from the elements and the [base](https://github.com/roscoe81/enviro-monitor/blob/master/3DP_Files/Northcliff_EM_Base_01.stl) is only required if the unit is not mounted on a vertical surface.

Likewise, testing and regression analysis was used to provide time-based drift, temperature, humidity and air pressure compensation for the Enviro+ gas sensors. Algorithms and clean-air calibration is included to provide gas sensor readings in ppm. A data logging function is provided to support the regression analysis. The log file needs to be converted to a valid json format before undertaking the regression analysis.

## Note: Even though the accuracy has been improved, the readings are still not thoroughly and accurately calibrated and should not be relied upon for critical purposes or applications.

mqtt support is provided to use external temperature and humidity sensors (for data logging and regression analysis), interworking between the monitor and a [home automation system](https://github.com/roscoe81/Home-Manager) and to support interworking between outdoor and indoor sensors. That latter interworking allows the display of an indoor unit to cycle between indoor and outdoor readings.

[Luftdaten]( https://github.com/pimoroni/enviroplus-python/blob/master/examples/luftdaten.py)  interworking is essentially unchanged, other than the ability to use external temperature and humidity sensors via mqtt messages.

Support is provided for streaming weather forecast, air quality, temperature, humidity, air pressure, PM concentration and gas concentration data to Adafruit IO. Three Adafruit IO package options are available: "Premium" with 14 data streams that will need an Adafruit IO+ account, "Basic Air" with 5 air quality data streams (Air Quality Level, Air Quality Text, PM1, PM2.5 and PM10) and "Basic Combo" with 5 air quality/climate streams (Air Quality Level, Weather Forecast Icon, Temperature, Humidity and Air Pressure). If enabled, Adafruit IO feed updates are generated every 5 minutes. The config file's aio_feed_window and aio_feed_sequence variables are used when collecting feeds from multiple Enviro Monitors to minimise Adafruit IO throttling errors. The aio_feed_window variable can be a value between 0 and 4 to set the start time for a one minute feed update window. 0 opens the window at 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50 and 55 minutes past the hour, 1 opens the window at 1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51 and 56 minutes past the hour, 2 opens the window at 2, 7, 12, 17, 22, 27, 32, 37, 42, 47, 52 and 57 minutes past the hour, 3 opens the window at 3, 8, 13, 18, 23, 28, 33, 38, 43, 48, 53 and 58 minutes past the hour and 4 opens the window at 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54 and 59 minutes past the hour. The aio_feed_sequence variable can be a value between 0 and 3 to set the feed update start time within the one minute feed update window. 0 starts the feed update immediately after the window opens, 1 delays the start by 15 seconds, 2 by 30 seconds and 3 by 45 seconds. A [tool](https://github.com/roscoe81/enviro-monitor/blob/master/Adafruit%20IO%20Feed%20Setup/Northcliff_adafruit_io_feed_setup_Gen.py) is provided to help set up the Adafruit IO feeds, dashboards and blocks. The tool can produce a dashboard like [this](https://io.adafruit.com/Roscoe81/dashboards/northcliff).

The same [Enviro+ setup]( https://github.com/pimoroni/enviroplus-python/blob/master/README.md) is used and the config.json file parameters are used to customise its functionality.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details

## Acknowledgements

Weather Forecast based on www.worldstormcentral.co/law_of_storms/secret_law_of_storms.html by R. J. Ellis
