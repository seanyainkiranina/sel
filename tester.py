import base64
import os
import pyodbc
import random
import sys
import time

from boto3 import session
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from secret import Secret
from test import Test
from databasecreds import DatabaseCreds
import uuid
from namegroups import Namegroups

class Tester:
    database_creds = None
    cnxn = None
    save_cursor = None
    cursor = None
    driver: WebDriver = None
    step: Test = None
    master_id = 1
    my_uuid = None
    ng = None

    def __init__(self, id, database_creds):
        self.cnxn = pyodbc.connect(database_creds.get_connectioN_string(), autocommit=True)
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
        self.driver = webdriver.Remote(
            command_executor='http://127.0.0.1:4444/wd/hub',
            desired_capabilities={
                "browserName": "chrome",
                "video": "True",
                "platformName": "windows",
            }, options=option)

        self.step = Test()
        self.session = session.Session()
        self.master_id = id

        self.run()

    def get_id(self,ng):
        self.ng = ng
        cursor = self.cnxn.cursor()
        cursor.execute("SELECT top 1 id,webpage,group_id from master_unit_tests where id=(?)", self.master_id)
        row = cursor.fetchone()
        while row:
            self.step.master_id = row[0]
            self.step.url = row[1].strip()
            self.step.group_id = row[2].strip()
            self.step.user_name = self.ng.get_individual( self.step.group_id)
            row = cursor.fetchone()
        self.my_uuid = uuid.uuid4()
        cursor.execute("insert into  master_run(start_date,master_id,run_id,individual) values(CURRENT_TIMESTAMP,?,?,?)",
                       [self.master_id,self.my_uuid,self,self.step.user_name])
        cursor.close()

    def run(self):
        self.get_id()
        self.execute_test()
        self.step.current_step = self.step.current_step + 1
        master_cursor = self.cnxn.cursor()
        master_cursor.execute("select id from child_unit_tests where master_id=(?) order by step_number",
                              self.step.master_id)
        master_row = master_cursor.fetchone()
        while master_row:
            self.step.id = master_row[0]
            print('nextstep ')
            try:
                self.next_step()
            except:
                print(sys.exc_info())
                e = sys.exc_info()[0]
                self.log_error_stop(e)
                try:
                    self.driver.quit()
                except:
                    print(sys.exc_info())
                exit(1)
            master_row = master_cursor.fetchone()
        master_cursor.close()
        self.driver.quit()

    def action_start(self) -> object:
        self.save_cursor.execute(
            "insert into detail_unit_tests(master_id,start,step_id,run_id,p_id) values(?,CURRENT_TIMESTAMP,?,?); select scope_identity() as id",
            [self.step.master_id, self.step.current_step, self.my_uuid, os.getpid()])
        self.save_cursor.nextset()
        for id in self.save_cursor:
            self.step.log_id = id
        self.step.log_id = int(self.step.log_id[0])

    def action_stop(self) -> object:
        print(self.step.log_id)
        self.save_cursor.execute("update detail_unit_tests set elapse=CURRENT_TIMESTAMP,success=1 where id=(?)",
                                 self.step.log_id)

    def log_error_stop(self, error_message: object) -> object:
        print(error_message)
        self.save_cursor.execute(
            "update detail_unit_tests set elapse=CURRENT_TIMESTAMP,success=0,response='Error' where id=(?)",
            self.step.log_id)
        self.save_image()

    def encode(self, file_name):
        try:
            return "data:image/png;base64," + base64.encodebytes(open(file_name, "rb").read())
        except:
            return ""

    def next_step(self) -> object:
        cursor = self.cnxn.cursor()
        self.action_start()
        print(self.step.master_id)
        print(self.step.current_step)
        cursor.execute("select action,element,keys,keys_append from child_unit_tests where id=(?) ", self.step.id)
        if cursor.rowcount == 0:
            print('row count 0')
            exit(1)
        row = cursor.fetchone()
        self.step.action = row[0]
        self.step.element = row[1]
        self.step.keys = row[2]
        self.step.keys_append = row[3]
        self.execute_test()
        self.step.current_step = self.step.current_step + 1
        cursor.close()
        self.action_stop()

    def execute_test(self) -> object:
        print(self.step.action)
        if self.step.action == "get":
            print(self.step.url)
            self.driver.get(self.step.url)
        elif self.step.action == "by_name":
            element = self.driver.find_element_by_name(self.step.element)
            element.send_keys(self.step.keys.strip())
            if len(self.step.keys_append) > 0:
                self.send_keys(element)
        elif self.step.action == "wait":
            self.wait()
        elif self.step.action == "gett":
            self.driver.get(self.step.element.strip())
        elif self.step.action == "by_linkText":
            element = self.driver.find_element_by_link_text(self.step.element)
            print(element)
            element.click()
        elif self.step.action == "window":
            windows = self.driver.window_handles
            self.driver.switch_to.window(windows[int(self.step.element)])
        elif self.step.action == "class":
            classes = self.driver.find_elements_by_class_name(self.step.element.strip())
            print('classes ')
            print(len(classes))
        elif self.step.action == "tags":
            links = self.driver.find_elements_by_tag_name(self.step.element.strip())
        elif self.step.action == "javascript":
            windows = self.driver.window_handles
            self.driver.execute_script(self.step.element)
        elif self.step.action == "by_xpath":
            element = self.driver.find_element_by_xpath(self.step.element)
            if self.step.keys_append == "Click":
                element.click()
        elif self.step.action == "by_id":
            element = self.driver.find_element_by_id(self.step.element)
            element.send_keys(self.step.keys.strip())
            if len(self.step.keys_append) > 0:
                self.send_keys(element)
            if len(self.step.keys_append) > 0:
                self.send_keys(element)
        elif self.step.action == "sleep":
            time.sleep(int(self.step.element.strip()))
            self.save_image()

    def send_keys(self, element):
        if self.step.keys_append == "Key.RETURN":
            element.send_keys(Keys.ENTER)
        return

    def save_image(self):
        file_name = str(self.step.current_step) + str(random.randrange(1000)) + ".png"
        self.driver.save_screenshot(file_name)
        s = Secret()
        client = self.session.client('s3',
                                     region_name='sfo2',
                                     endpoint_url='https://sfo2.digitaloceanspaces.com',
                                     aws_access_key_id=s.ACCESS_ID,
                                     aws_secret_access_key=s.SECRET_KEY)

        client.upload_file(file_name, 'eshow-test-space', 'screenshots/' + file_name,
                           ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/png'})
        base_image = "https://eshow-test-space.sfo2.cdn.digitaloceanspaces.com/screenshots/" + file_name
        self.save_cursor.execute("update detail_unit_tests set screenshot=(?) where id=(?)", base_image,
                                 int(self.step.log_id))
        os.unlink(file_name)

    def save_image64(self):
        self.driver.save_screenshot(str(self.step.current_step) + ".png")
        baseImage = self.encode(str(self.step.current_step) + ".png")
        self.save_cursor.execute("update detail_unit_tests set screenshot=? where id=?", [baseImage, self.step.log_id])

    def wait(self):
        print('wait title')
        if self.step.element == "title":
            print('waited for title')
            element = WebDriverWait(self.driver, int(self.step.keys_append)).until(
                EC.title_contains(self.step.keys)
            )
        return
