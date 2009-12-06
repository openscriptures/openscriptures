#!/bin/bash

perl -e 'print scalar(localtime) . "\n"'

python manage.py reset core --noinput
python manage.py syncdb
#If exists data/supplemental_data.sql, then import the data
cd data/manuscripts
python import.py
#python merge.py

perl -e 'print scalar(localtime) . "\n"'