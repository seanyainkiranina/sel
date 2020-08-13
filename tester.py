import base64
import os
import pyodbc
import random
import sys
import time
from random import randrange

from boto3 import session
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from namegroups import Namegroups
from secret import Secret
from test import Test
from databasecreds import DatabaseCreds
import uuid


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

    def __init__(self, id, database_creds, ng):
        self.cnxn = pyodbc.connect(database_creds.get_connectioN_string(), autocommit=True)
        self.ng = ng

        pid = os.getpid()

        cursor = self.cnxn.cursor()
        self.save_cursor = self.cnxn.cursor()
        option = Options()

        option.add_argument("--disable-infobars")

        option.add_argument("--disable-gpu")
        option.add_argument("--start-maximized")
        option.add_argument("--headless")
       # option.add_argument("--window-size=1024,768")
        option.add_argument("--disable-extensions")
        option.add_argument("--disable-translate")
        option.add_argument("--allow-file-access-from-files")
        # option.add_argument("--enable-usermedia-screen-capturing")
        # option.add_argument("--use-fake-ui-for-media-stream")
        # option.add_argument("--use-fake-device-for-media-stream")
       #  option.add_argument("--use-fake-ui-device-for-media-stream")
       #  option.add_argument("--use-file-for-fake-video-capture=C:\\temp\\bunnyvideo.mjpeg")
     #   option.add_argument("--use-file-for-fake-audio-capture=C:\\temp\\bunny.opus")
        option.add_argument("--enable-tracing")
      #  option.add_argument("--enable-tracing-output = c:\\temp\\log.txt")

        # Pass the argument 1 to allow and 2 to block
        option.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2
        })
        option.set_capability('unhandledPromptBehavior', 'accept')

        self.driver = webdriver.Remote(
            command_executor='http://64.227.83.96:4444/wd/hub',
            desired_capabilities={
                "browserName": "chrome",
            }, options=option)

        self.step = Test()
        self.session = session.Session()
        self.master_id = id

        self.run()

    def get_id(self):

        cursor = self.cnxn.cursor()
        cursor.execute("SELECT top 1 id,webpage,group_id,alt_webpage from master_unit_tests where id=(?)",
                       self.master_id)
        row = cursor.fetchone()
        while row:
            self.step.master_id = row[0]
            self.step.url = row[1].strip()
            if row[3] is not None and len(row[3]) > 0 and len(row[3].strip()) > 0:
                coin = randrange(101)
                if coin > 50:
                    self.step.url = row[3].strip()
            self.step.group_id = row[2]
            if self.step.group_id != 0:
                self.step.user_name = self.ng.get_individual(self.step.group_id)
            else:
                self.step.user_name = ""
            row = cursor.fetchone()
        self.my_uuid = uuid.uuid4()
        cursor.execute(
            "insert into  master_run(start_date,master_id,run_id,group_id,individual,starting_url) values(CURRENT_TIMESTAMP,?,?,?,?,?)",
            [self.master_id, self.my_uuid, self.step.group_id, self.step.user_name, self.step.url])
        cursor.close()

    def run(self):

        self.get_id()
        self.execute_test()
        self.step.current_step = self.step.current_step + 1
        master_cursor = self.cnxn.cursor()
        master_cursor.execute(
            "select id,route from child_unit_tests where master_id=(?) and active_task=1 order by step_number",
            self.step.master_id)
        master_row = master_cursor.fetchone()
        while master_row:
            self.step.id = master_row[0]
            if self.step.route == master_row[1].strip():
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
        pid = os.getpid()
        self.save_cursor.execute(
            "insert into detail_unit_tests(master_id,start,step_id,run_id,p_id,individual,my_route) values(?,CURRENT_TIMESTAMP,?,?,?,?,?); select scope_identity() as id",
            [self.step.master_id, self.step.current_step, self.my_uuid, pid, self.step.user_name, self.step.route])
        self.save_cursor.nextset()
        for id in self.save_cursor:
            self.step.log_id = id
        self.step.log_id = int(self.step.log_id[0])

    def action_stop(self) -> object:
        self.save_cursor.execute("update detail_unit_tests set elapse=CURRENT_TIMESTAMP,success=1 where id=(?)",
                                 self.step.log_id)
        self.save_cursor.execute(
            "update master_run set end_date=CURRENT_TIMESTAMP where run_id=?",
            [self.my_uuid])

    def log_error_stop(self, error_message: object) -> object:
        print(error_message)
        self.save_cursor.execute(
            "update detail_unit_tests set elapse=CURRENT_TIMESTAMP,success=0,response='Error' where id=(?)",
            self.step.log_id)
        self.save_image()
        self.save_cursor.execute(
            "update master_run set end_date=CURRENT_TIMESTAMP where run_id=?",
            [self.my_uuid])

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
        print(self.step.id)
        print("self.step.id")
        cursor.execute(
            "select action,element,keys,keys_append,route,alt_route,alt_route_2 from child_unit_tests where id=(?) ",
            self.step.id)
        if cursor.rowcount == 0:
            print('row count 0')
            exit(1)
        row = cursor.fetchone()
        self.step.action = row[0]
        self.step.element = row[1]
        self.step.keys = row[2]
        self.step.keys_append = row[3]
        self.step.route = row[4].strip()
        self.step.alt_route = row[5].strip()
        self.step.alt_route_2 = row[6].strip()
        self.execute_test()
        self.step.current_step = self.step.current_step + 1
        cursor.close()
        self.action_stop()

    def execute_test(self) -> object:
        print("execute_test ")
        print(self.step.action)
        check_for_custom_field = self.ng.get_value(self.step.group_id, self.step.user_name, self.step.element)
        if check_for_custom_field is not None:
            self.step.keys = check_for_custom_field
            print(self.step.keys)
        if self.step.action == "random_class":
            classes = self.driver.find_elements_by_class_name(self.step.element.strip())
            coin = randrange(0, len(classes))
            classes[coin].click()
        if self.step.action == "random_route":
            time.sleep(int(self.step.element.strip()))
            coin = randrange(101)
            if coin > 50:
                self.step.route = self.step.alt_route
            else:
                self.step.route = self.step.alt_route_2
        if self.step.action == "get":
            print(self.step.url)
            self.driver.get(self.step.url)
        elif self.step.action == "by_name":
            element = self.driver.find_element_by_name(self.step.element)
            element.send_keys(self.step.keys.strip())
            print(self.step.keys.strip())
            if len(self.step.keys_append) > 0:
                self.send_keys(element)
        elif self.step.action == "newtab":
            self.driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + 't')
        elif self.step.action == "wait":
            self.wait()
        elif self.step.action == "gett":
            self.driver.get(self.step.element.strip())
        elif self.step.action == "by_linkText":
            self.driver.implicitly_wait(10)
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
        elif self.step.action == "by_link_texts":
            elements = self.driver.find_elements_by_link_text(self.step.element)
            for element in elements:
                print(element)
        elif self.step.action == "by_class_names":
            elements = self.driver.find_elements_by_class_name(self.step.element)
            for element in elements:
                print(element)
        elif self.step.action == "by_class_name":
            element = self.driver.find_element_by_class_name(self.step.element)
            if self.step.keys_append == "HClick":
                hover = ActionChains(self.driver).move_to_element(element).click().perform()
            if self.step.keys_append == "Click":
                element.click()
        elif self.step.action == "by_xpath":
            element = self.driver.find_element_by_xpath(self.step.element)

            if self.step.keys_append == "HClick":
                hover = ActionChains(self.driver).move_to_element(element)
                hover.perform()
                element.click()

            if self.step.keys_append == "Click":
                element.click()
        elif self.step.action == "click_by_id":
            element = self.driver.find_element_by_id(self.step.element)
            element.click()
        elif self.step.action == "by_id":
            print(self.step.element)
            element = self.driver.find_element_by_id(self.step.element)
            self.driver.implicitly_wait(60)
            ActionChains(self.driver).move_to_element(element).click(element).perform()
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
        file_name = str(self.step.current_step) + str(os.getpid()) + str(random.randrange(1000)) + ".png"
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
        if self.step.element == "id":
            print('waited for element')
            element = WebDriverWait(self.driver, int(self.step.keys_append)).until(
               EC.element_to_be_clickable((By.ID, self.step.keys)))

        return
import base64
import os
import pyodbc
import random
import sys
import time
from random import randrange

from boto3 import session
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from namegroups import Namegroups
from secret import Secret
from test import Test
from databasecreds import DatabaseCreds
import uuid


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

    def __init__(self, id, database_creds, ng):
        self.cnxn = pyodbc.connect(database_creds.get_connectioN_string(), autocommit=True)
        self.ng = ng

        pid = os.getpid()

        cursor = self.cnxn.cursor()
        self.save_cursor = self.cnxn.cursor()
        option = Options()

        option.add_argument("--disable-infobars")

        option.add_argument("--disable-gpu")
        option.add_argument("--start-maximized")
        option.add_argument("--headless")
        option.add_argument("--window-size=1024,768")
        option.add_argument("--disable-extensions")
        option.add_argument("--disable-translate")
        option.add_argument("--allow-file-access-from-files")
        # option.add_argument("--enable-usermedia-screen-capturing")
        # option.add_argument("--use-fake-ui-for-media-stream")
        # option.add_argument("--use-fake-device-for-media-stream")
       #  option.add_argument("--use-fake-ui-device-for-media-stream")
       #  option.add_argument("--use-file-for-fake-video-capture=C:\\temp\\bunnyvideo.mjpeg")
     #   option.add_argument("--use-file-for-fake-audio-capture=C:\\temp\\bunny.opus")
        option.add_argument("--enable-tracing")
      #  option.add_argument("--enable-tracing-output = c:\\temp\\log.txt")

        # Pass the argument 1 to allow and 2 to block
      #  option.add_experimental_option("prefs", {
       #     "profile.default_content_setting_values.notifications": 2
      #  })
        option.set_capability('unhandledPromptBehavior', 'accept')

        self.driver = webdriver.Remote(
            command_executor='http://64.227.83.96:4444/wd/hub',
            desired_capabilities={
                "browserName": "firefox",
            }, options=option)

        self.step = Test()
        self.session = session.Session()
        self.master_id = id

        self.run()

    def get_id(self):

        cursor = self.cnxn.cursor()
        cursor.execute("SELECT top 1 id,webpage,group_id,alt_webpage from master_unit_tests where id=(?)",
                       self.master_id)
        row = cursor.fetchone()
        while row:
            self.step.master_id = row[0]
            self.step.url = row[1].strip()
            if row[3] is not None and len(row[3]) > 0 and len(row[3].strip()) > 0:
                coin = randrange(101)
                if coin > 50:
                    self.step.url = row[3].strip()
            self.step.group_id = row[2]
            if self.step.group_id != 0:
                self.step.user_name = self.ng.get_individual(self.step.group_id)
            else:
                self.step.user_name = ""
            row = cursor.fetchone()
        self.my_uuid = uuid.uuid4()
        cursor.execute(
            "insert into  master_run(start_date,master_id,run_id,group_id,individual,starting_url) values(CURRENT_TIMESTAMP,?,?,?,?,?)",
            [self.master_id, self.my_uuid, self.step.group_id, self.step.user_name, self.step.url])
        cursor.close()

    def run(self):

        self.get_id()
        self.execute_test()
        self.step.current_step = self.step.current_step + 1
        master_cursor = self.cnxn.cursor()
        master_cursor.execute(
            "select id,route from child_unit_tests where master_id=(?) and active_task=1 order by step_number",
            self.step.master_id)
        master_row = master_cursor.fetchone()
        while master_row:
            self.step.id = master_row[0]
            if self.step.route == master_row[1].strip():
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
        pid = os.getpid()
        self.save_cursor.execute(
            "insert into detail_unit_tests(master_id,start,step_id,run_id,p_id,individual,my_route) values(?,CURRENT_TIMESTAMP,?,?,?,?,?); select scope_identity() as id",
            [self.step.master_id, self.step.current_step, self.my_uuid, pid, self.step.user_name, self.step.route])
        self.save_cursor.nextset()
        for id in self.save_cursor:
            self.step.log_id = id
        self.step.log_id = int(self.step.log_id[0])

    def action_stop(self) -> object:
        self.save_cursor.execute("update detail_unit_tests set elapse=CURRENT_TIMESTAMP,success=1 where id=(?)",
                                 self.step.log_id)
        self.save_cursor.execute(
            "update master_run set end_date=CURRENT_TIMESTAMP where run_id=?",
            [self.my_uuid])

    def log_error_stop(self, error_message: object) -> object:
        print(error_message)
        self.save_cursor.execute(
            "update detail_unit_tests set elapse=CURRENT_TIMESTAMP,success=0,response='Error' where id=(?)",
            self.step.log_id)
        self.save_image()
        self.save_cursor.execute(
            "update master_run set end_date=CURRENT_TIMESTAMP where run_id=?",
            [self.my_uuid])

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
        print(self.step.id)
        print("self.step.id")
        cursor.execute(
            "select action,element,keys,keys_append,route,alt_route,alt_route_2 from child_unit_tests where id=(?) ",
            self.step.id)
        if cursor.rowcount == 0:
            print('row count 0')
            exit(1)
        row = cursor.fetchone()
        self.step.action = row[0]
        self.step.element = row[1]
        self.step.keys = row[2]
        self.step.keys_append = row[3]
        self.step.route = row[4].strip()
        self.step.alt_route = row[5].strip()
        self.step.alt_route_2 = row[6].strip()
        self.execute_test()
        self.step.current_step = self.step.current_step + 1
        cursor.close()
        self.action_stop()

    def execute_test(self) -> object:
        print("execute_test ")
        print(self.step.action)
        check_for_custom_field = self.ng.get_value(self.step.group_id, self.step.user_name, self.step.element)
        if check_for_custom_field is not None:
            self.step.keys = check_for_custom_field
            print(self.step.keys)
        if self.step.action == "random_class":
            classes = self.driver.find_elements_by_class_name(self.step.element.strip())
            coin = randrange(0, len(classes))
            classes[coin].click()
        if self.step.action == "random_route":
            time.sleep(int(self.step.element.strip()))
            coin = randrange(101)
            if coin > 50:
                self.step.route = self.step.alt_route
            else:
                self.step.route = self.step.alt_route_2
        if self.step.action == "get":
            print(self.step.url)
            self.driver.get(self.step.url)
        elif self.step.action == "by_name":
            element = self.driver.find_element_by_name(self.step.element)
            element.send_keys(self.step.keys.strip())
            print(self.step.keys.strip())
            if len(self.step.keys_append) > 0:
                self.send_keys(element)
        elif self.step.action == "newtab":
            self.driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + 't')
        elif self.step.action == "wait":
            self.wait()
        elif self.step.action == "gett":
            self.driver.get(self.step.element.strip())
        elif self.step.action == "by_linkText":
            self.driver.implicitly_wait(10)
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
        elif self.step.action == "by_link_texts":
            elements = self.driver.find_elements_by_link_text(self.step.element)
            for element in elements:
                print(element)
        elif self.step.action == "by_class_names":
            elements = self.driver.find_elements_by_class_name(self.step.element)
            for element in elements:
                print(element)
        elif self.step.action == "by_class_name":
            element = self.driver.find_element_by_class_name(self.step.element)
            if self.step.keys_append == "HClick":
                hover = ActionChains(self.driver).move_to_element(element).click().perform()
            if self.step.keys_append == "Click":
                element.click()
        elif self.step.action == "by_xpath":
            element = self.driver.find_element_by_xpath(self.step.element)

            if self.step.keys_append == "HClick":
                hover = ActionChains(self.driver).move_to_element(element)
                hover.perform()
                element.click()

            if self.step.keys_append == "Click":
                element.click()
        elif self.step.action == "click_by_id":
            element = self.driver.find_element_by_id(self.step.element)
            element.click()
        elif self.step.action == "by_id":
            print(self.step.element)
            element = self.driver.find_element_by_id(self.step.element)
            self.driver.implicitly_wait(60)
            ActionChains(self.driver).move_to_element(element).click(element).perform()
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
        file_name = str(self.step.current_step) + str(os.getpid()) + str(random.randrange(1000)) + ".png"
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
        if self.step.element == "id":
            print('waited for element')
            element = WebDriverWait(self.driver, int(self.step.keys_append)).until(
               EC.element_to_be_clickable((By.ID, self.step.keys)))

        return
