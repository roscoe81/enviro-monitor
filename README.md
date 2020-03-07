# enviro-monitor
This project uses a Raspberry Pi Zero W, a Pimoroni Enviro+ and a Plantower air quality sensor to monitor, display and report on air particles, gases, temperature, humidity and air pressure. It’s based on many of the Python [examples and libraries]( https://github.com/pimoroni/enviroplus-python) published by Pimoroni, with the following modifications and enhancements:

A basic weather forecast function, based on air pressure levels and changes.

The light level display in the superb [Weather and Light](https://github.com/pimoroni/enviroplus-python/blob/master/examples/weather-and-light.py) has been changed to air quality. It also uses the above-mentioned weather forecast information and has some minor changes to the humidity indicator.

The [Combined]( https://github.com/pimoroni/enviroplus-python/blob/master/examples/combined.py) has been modified to provide a more visible display of each graph, to use graph colours based on level thresholds for each parameter and to only display parameters that have been measured. The display_everything method has also been modified to only show air quality parameters, in order to improve readability of the display.

The [All in One]( https://github.com/pimoroni/enviroplus-python/blob/master/examples/all-in-one.py) function has been modified to allow cycling through the monitor’s functions.

The accuracy of the temperature and humidity measurements has been improved by undertaking extensive testing and regression analysis to develop more effective compensation algorithms. However, even these improved algorithms required the development of  3D-printed case that separates the Enviro+ from the Raspberry Pi Zero W and connects them together via a ribbon cable. 

Likewise, testing and regression analysis was used to provide temperature, humidity and air pressure compensation for the Enviro+ gas sensors. Algorithms and clean-air calibration is included to provide gas sensor readings in ppm. A data logging function is provided to support the regression analysis.

##(Note: Even though the accuracy has been improved, the readings are still not thoroughly and accurately calibrated and should not be relied upon for critical purposes or applications.)

mqtt support is provided to use external temperature and humidity sensors (for data logging and regression analysis), interworking between the monitor and a home automation system and to support interworking between outdoor and indoor sensors. That latter interworking allows the displays to cycle between indoor and outdoor readings.

[Luftdaten]( https://github.com/pimoroni/enviroplus-python/blob/master/examples/luftdaten.py)  interworking is essentially unchanged, other than the ability to use external temperature and humidity sensors via mqtt messages. 

The same [Enviro+ setup]( https://github.com/pimoroni/enviroplus-python/blob/master/README.md) is used and the Config Setup parameters in the code can be further used to customise its functionality.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details

