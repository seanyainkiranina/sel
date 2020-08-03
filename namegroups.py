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
    groups = {}

    def __init__(self, database_creds):
        self.cnxn = pyodbc.connect(database_creds.get_connectioN_string(), autocommit=True)
        self.q = queue.Queue()

    def get_namegroups(self):
        self.groups = {}
        individual = {}
        cursor = self.cnxn.cursor()
        cursor.execute("select  mock_data_detail.id, mock_data_detail.name_id, "
                       "mock_data_detail.name_value, mock_data_detail.name_group,mock_data_names.mock_data_name,"
                       "mock_data_detail.sub_group from  mock_data_detail INNER JOIN mock_data_names ON "
                       "mock_data_names.id=mock_data_detail.name_id where mock_data_detail.active=1")
        row = cursor.fetchone()
        while row:
            group_key = str(row[3])
            one_key = str(row[5])
            val_key = str(row[4])
            val_val = str(row[2])


            if group_key not in self.groups.keys():
                self.groups[group_key] = {}

            individuals = self.groups[group_key]

            if one_key is None or one_key=='None':
                one_key = ""

            if one_key not in individuals.keys():
                individuals[one_key] ={}

            individual = individuals[one_key]
            individual[val_key]=val_val
            individuals[one_key]=individual

            self.groups[group_key] = individuals

            row = cursor.fetchone()
        cursor.close()
    def get_individual(self,group_id):
        users=list(self.groups[str(group_id)].keys())
        if len(users)-1 ==0:
            return ""

        which_user_id = random.randint(0, len(users)-1)
        while users[which_user_id] == "":
            which_user_id = random.randint(0, len(users) - 1)

        return users[which_user_id]
    def get_value(self,group_id,individual_name,value_name):
        data = self.groups[str(group_id)]
        default_data = data[""]
        if value_name in default_data.keys():
            return default_data[value_name]
        if value_name in data[individual_name].keys():
            return data[individual_name][value_name]
        return None



database_creds = DatabaseCreds()
ng = Namegroups(database_creds)
ng.get_namegroups()
user = ng.get_individual(1)
login = ng.get_value(1,user,"account_id")

print(user)