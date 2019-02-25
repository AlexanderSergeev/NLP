import datetime
from csv import DictWriter
from crawler import Crawler

filename = str(datetime.datetime.now()).replace(" ", "_").replace(":", "_") + '.csv'
with open(filename, 'w') as f:
    fieldnames = ['story', 'meta', 'url', 'title', 'descr']
    writer = DictWriter(f, fieldnames = fieldnames)
    writer.writeheader()
    for row in Crawler().traverse():
        writer.writerow(row)
