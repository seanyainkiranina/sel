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
from namegroups import Namegroups

def runner(test_number, throttle):
    dbc = DatabaseCreds()
    if throttle > 0:
        time.sleep(throttle)
    browser = Tester(test_number, dbc)


if __name__ == "__main__":
    dbc = DatabaseCreds()
    sc = Scheduler(dbc)
    ng = Namegroups(dbc)
    ng.get_namegroups()
    q = sc.get_schedule(ng)
    idelay = 0
    seconds = time.time()
    totalRequests = 0
    qq = queue.Queue()
    procs = 1

    while q.qsize() > 0:
        stRunner = q.get()
        qq.put(stRunner)
        if isinstance(stRunner.max_simul, int) and stRunner.max_simul > 0 and stRunner.max_simul > procs:
            procs=stRunner.max_simul

    while qq.qsize() > 0:
        procs = 20
        cseconds = time.time()
        stRunner = qq.get()
        if isinstance(stRunner.delay_time, int) and (cseconds - seconds) < stRunner.delay_time:
            print('delay_time')
        # q.put(stRunner)
        #    continue
        if isinstance(stRunner.exec_limit, int) and (cseconds - seconds) > stRunner.exec_limit:
            print('exec_limit')
        #    continue
        totalRequests = totalRequests + procs
        if isinstance(stRunner.requests, int) and stRunner.requests > 0:
            if totalRequests > stRunner.requests:
                procs = 0
                continue
        jobs = []
        for i in range(0, procs):
            out_list = list()
            process = multiprocessing.Process(target=runner,
                                              args=(stRunner.batch_number, stRunner.throttle))
            jobs.append(process)

        # Start the processes (i.e. calculate the random number lists)
        for j in jobs:
            j.start()

        # Ensure all of the processes have finished
        for j in jobs:
            j.join()
        exit(1)
