import base64
import os
import pyodbc
import random
import sys
import time
import queue
import multiprocessing

from boto3 import session
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from secret import Secret
from test import Test
from tester import Tester
from databasecreds import DatabaseCreds
from scheduletask import ScheduleTask
from scheduler import Scheduler
import uuid
import pprint


class Namegroups:
    database_creds = None
    cnxn = None
    save_cursor = None
    cursor = None
    q = None

    def __init__(self, database_creds):
        self.cnxn = pyodbc.connect(database_creds.get_connectioN_string(), autocommit=True)
        self.q = queue.Queue()

    def get_namegroups(self):
        groups = {}
        individual = {}
        cursor = self.cnxn.cursor()
        cursor.execute("select  mock_data_detail.id, mock_data_detail.name_id, "
                       "mock_data_detail.name_value, mock_data_detail.name_group,mock_data_names.mock_data_name,"
                       "mock_data_detail.sub_group from  mock_data_detail INNER JOIN mock_data_names ON "
                       "mock_data_names.id=mock_data_detail.name_id where mock_data_detail.active=1")
        row = cursor.fetchone()
        while row:
            xkey = str(row[3])
            okey = str(row[5])
            dkey = str(row[2])
            dval = str(row[3])

            if xkey in groups.keys():
                groups[xkey] = []
                individual[okey] = {dkey: dval}
                groups[xkey].append(individual[okey])
            else:
                indvs = groups[xkey]
                if okey in indvs.keys:
                    xdict = indvs[okey]
                    xdict[str(row[2])] = row[3]
                else:
                    indvs[okey] = row[3]
            row = cursor.fetchone()
        cursor.close()
        return groups


database_creds = DatabaseCreds()
ng = Namegroups(database_creds)
x = ng.get_namegroups()
pp = pprint.PrettyPrinter(indent=4)
pp.pprint(x)
