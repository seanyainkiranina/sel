import time

from py._builtin import execfile
from selenium import webdriver
import pyodbc
import sys
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
from boto3 import session
from botocore.client import Config
import os
from secret import Secret
import random


class Test:
    master_id =0
    action = "Get"
    url = ""
    current_step =1
    id =0
    element = ""
    keys = ""
    keys_append = ""
    log_id =0

    def __init__(self):
        self.master_id = 0
        self.action = "get"
        self.url = ""
        self.current_step = 1
        self.id =0
        self.log_id =0

class Tester:
    server = 'tcp:localhost'
    database = 'test_db'
    username = 'sai'
    password = 'chicago'
    cnxn = None
    save_cursor = None
    cursor = None
    driver: WebDriver =None
    step: Test =None

    def __init__(self):
        self.cnxn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'+
                                    'SERVER='+self.server+';MARS_Connection=Yes;DATABASE='+self.database+';'+
                                    'UID='+self.username+';PWD='+ self.password,autocommit = True)
        cursor = self.cnxn.cursor()
        self.save_cursor = self.cnxn.cursor()
        option = Options()

        option.add_argument("--disable-infobars")
        option.add_argument("--start-maximized")
        option.add_argument("--disable-extensions")

        # Pass the argument 1 to allow and 2 to block
        option.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 1
        })
        self.driver = webdriver.Chrome(chrome_options=option, executable_path='C:\\Users\\jpalmer\\Workspace\\nodesel\\chromedriver.exe')  # Optional argument, if not specified will search path.
        self.step = Test()
        self.session = session.Session()


        self.run()
    def getID(self):
        cursor = self.cnxn.cursor()
        cursor.execute("SELECT top 1 id,webpage from master_unit_tests")
        row = cursor.fetchone()
        while row:
            self.step.master_id = row[0]
            self.step.url = row[1].strip()
            print(self.step.url)
            print('url')
            row = cursor.fetchone()
        cursor.close()
    def run(self):
        self.getID()
        self.executeTest()
        self.step.current_step = self.step.current_step + 1
        master_cursor = self.cnxn.cursor()
        master_cursor.execute("select id from child_unit_tests where master_id=(?) order by step_number",self.step.master_id)
        master_row=master_cursor.fetchone()
        while master_row:
            self.step.id = master_row[0]
            print('nextstep ')
            try:
                self.nextStep()
            except:
                print(sys.exc_info())
                e = sys.exc_info()[0]
                self.logErrorStop(e)
                exit(1)
            master_row = master_cursor.fetchone()
        master_cursor.close()
        self.driver.quit()
    def actionStart(self):
        self.save_cursor.execute("insert into detail_unit_tests(master_id,start,step_id) values(?,CURRENT_TIMESTAMP,?); select scope_identity() as id",[self.step.master_id,self.step.current_step])
        self.save_cursor.nextset()
        for id in self.save_cursor:
            self.step.log_id = id
        self.step.log_id = int(self.step.log_id[0])
    def actionStop(self):
        print(self.step.log_id)
        self.save_cursor.execute("update detail_unit_tests set elapse=CURRENT_TIMESTAMP,success=1 where id=(?)",self.step.log_id)
    def logErrorStop(self,error_message):
        print(error_message)
        self.save_cursor.execute("update detail_unit_tests set elapse=CURRENT_TIMESTAMP,success=0,response='Error' where id=(?)",self.step.log_id)
        self.saveImage()
    def encode(self,file_name):
        try:
            return "data:image/png;base64," + base64.encodebytes(open(file_name,"rb").read())
        except:
            return ""
    def nextStep(self):
        cursor = self.cnxn.cursor()
        self.actionStart()
        print(self.step.master_id)
        print(self.step.current_step)
        cursor.execute("select action,element,keys,keys_append from child_unit_tests where id=(?) ",self.step.id)
        if cursor.rowcount == 0:
            print('row count 0')
            exit(1)
        row = cursor.fetchone()
        self.step.action = row[0]
        self.step.element = row[1]
        self.step.keys = row[2]
        self.step.keys_append = row[3]
        self.executeTest()
        self.step.current_step = self.step.current_step + 1
        cursor.close()
        self.actionStop()
    def executeTest(self):
        print(self.step.action)
        if self.step.action == "get":
            print(self.step.url)
            self.driver.get(self.step.url)
        elif self.step.action == "by_name":
            element = self.driver.find_element_by_name(self.step.element)
            element.send_keys(self.step.keys.strip())
            if len(self.step.keys_append)>0:
                self.sendKeys(element)
        elif self.step.action == "wait":
            self.wait()
        elif self.step.action=="by_linkText":
            element = self.driver.find_element_by_link_text(self.step.element)
            print(element)
            element.click()
        elif self.step.action=="window":
            windows = self.driver.window_handles
            self.driver.switch_to.window(windows[int(self.step.element)])
        elif self.step.action=="class":
            classes = self.driver.find_elements_by_class_name(self.step.element.strip())
            print('classes ')
            print(len(classes))
        elif self.step.action=="tags":
            links = self.driver.find_elements_by_tag_name(self.step.element.strip())
        elif self.step.action == "javascript":
            windows = self.driver.window_handles
            self.driver.execute_script(self.step.element)
        elif self.step.action=="by_xpath":
            element = self.driver.find_element_by_xpath(self.step.element)
            if self.step.keys_append == "Click":
                element.click()
        elif self.step.action=="by_id":
            element = self.driver.find_element_by_id(self.step.element)
            element.send_keys(self.step.keys.strip())
            if len(self.step.keys_append) > 0:
                self.sendKeys(element)
            if len(self.step.keys_append) > 0:
                self.sendKeys(element)
        elif self.step.action=="sleep":
            time.sleep(int(self.step.element.strip()))
            self.saveImage()
    def sendKeys(self,element):
        if self.step.keys_append == "Key.RETURN":
            element.send_keys(Keys.ENTER)
        return
    def saveImage(self):
        file_name = str(self.step.current_step) + str(random.randrange(1000))  + ".png"
        self.driver.save_screenshot(file_name)
        s = Secret()
        client = self.session.client('s3',
                                region_name='sfo2',
                                endpoint_url='https://sfo2.digitaloceanspaces.com',
                                aws_access_key_id=s.ACCESS_ID,
                                aws_secret_access_key=s.SECRET_KEY)

        client.upload_file(file_name, 'eshow-test-space', 'screenshots/' + file_name, ExtraArgs={'ACL':'public-read','ContentType':'image/png'})
        baseImage = "https://eshow-test-space.sfo2.cdn.digitaloceanspaces.com/screenshots/" + file_name
        self.save_cursor.execute("update detail_unit_tests set screenshot=(?) where id=(?)",baseImage,int(self.step.log_id))
        os.unlink(file_name)
    def saveImage64(self):
        self.driver.save_screenshot(str(self.step.current_step) + ".png")
        baseImage = self.encode(str(self.step.current_step) + ".png")
        self.save_cursor.execute("update detail_unit_tests set screenshot=? where id=?",[baseImage,self.step.log_id])
    def wait(self):
        print('wait title')
        if self.step.element == "title":
            print('waited for title')
            element = WebDriverWait(self.driver, int(self.step.keys_append)).until(
                EC.title_contains(self.step.keys)
            )
        return

browser= Tester()
