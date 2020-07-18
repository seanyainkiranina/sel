import time
from selenium import webdriver
import pyodbc
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Test:
    master_id =0
    action = "Get"
    url = ""
    current_step =1
    id =0
    element = ""
    keys = ""
    keys_append = ""

    def __init__(self):
        self.master_id = 0
        self.action = "get"
        self.url = ""
        self.current_step = 1
        self.id =0

class Tester:
    server = 'tcp:localhost'
    database = 'test_db'
    username = 'sai'
    password = 'chicago'
    cnxn = None
    driver: WebDriver =None
    step: Test =None

    def __init__(self):
        self.cnxn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'+
                                    'SERVER='+self.server+';MARS_Connection=Yes;DATABASE='+self.database+';'+
                                    'UID='+self.username+';PWD='+ self.password)
        cursor = self.cnxn.cursor()
        self.driver = webdriver.Chrome('C:\\Users\\jpalmer\\Workspace\\nodesel\\chromedriver.exe')  # Optional argument, if not specified will search path.
        self.step = Test()
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
        print('Got Id')
        self.getID()
        self.executeTest()
        print('etwrt finished')
        self.step.current_step = self.step.current_step + 1
        master_cursor = self.cnxn.cursor()
        master_cursor.execute("select id from child_unit_tests where master_id=(?) order by id",self.step.master_id)
        master_row=master_cursor.fetchone()
        while master_row:
            self.step.id = master_row[0]
            print('nextstep ')
            self.nextStep()
            master_row = master_cursor.fetchone()
        master_cursor.close()
    def actionStart(self):
        cursor = self.cnxn.cursor()
        cursor.execute("insert into detail_unit_tests(master_id,step_id) values(?,?);",self.step.master_id,self.step.current_step)
        self.cnxn.commit()
        cursor.execute("SELECT SCOPE_IDENTITY();")
        row = cursor.fetchone()
        print('inserting ')
        print(row[0])
        self.step.id = row[0]
    def actionStop(self):
        cursor = self.cnxn.cursor()
        cursor.execute("update detail_unit_tests set elapse=CURRENT_TIMESTAMP where id=(?)",self.step.id)
        self.cnxn.commit()
    def nextStep(self):
        cursor = self.cnxn.cursor()
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
        time.sleep(3)
        self.executeTest()
        self.step.current_step = self.step.current_step + 1
        cursor.close()
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
        elif self.step.action=="by_xpath":
            element = self.driver.find_element_by_xpath(self.step.element)
            if self.step.keys_append == "Click":
                element.click()
    def sendKeys(self,element):
        if self.step.keys_append == "Key.RETURN":
            element.send_keys(Keys.ENTER)
        return
    def wait(self):
        print('wait title')
        if self.step.element == "title":
            print('waited for title')
            element = WebDriverWait(self.driver, int(self.step.keys_append)).until(
                EC.title_contains(self.step.keys)
            )
        return

browser= Tester()
