Installation
============
To install, first install any non-python dependancies which can be done on Ubuntu using the following command:
```
$ sudo apt-get install python-dev firefox xvfb libjpeg-dev libxml2-dev libxslt-dev libssl-dev libffi-dev
```
The install the Python dependancies with this command:
```
pip install -r requirements.txt
```

Conventions
===========
PEP8 for the most part. Also note that the abbreviation Asn (Autonomous System Number) is commonly used in place of AS (Autonomous System) since we most frequently refer to ASes by number and for variable naming reasons ("as" is a bad variable namme in python)