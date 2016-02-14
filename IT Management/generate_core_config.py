import yaml
import re
import csv
import sys
import os

print("HUSD Core Config Gen")
SITE = raw_input("Enter Site Name: ").upper()

if not os.path.isfile('yamls\\{0}.yml'.format(SITE)):
    sys.exit('Site not setup, run setup_site.py')

# Loads access info
with open('yamls\\{0}.yml'.format(SITE), 'r+') as f:
    saved_data = yaml.load(f)

with open('csv\\{0}'.format(saved_data.VLANs)) as data:
    data = csv.reader(data)

for row in data:
    print(row)