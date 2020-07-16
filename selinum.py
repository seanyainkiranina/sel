import time
from selenium import webdriver
import pyodbc
from selenium.webdriver.chrome.webdriver import WebDriver


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
        self.actionStart()
        self.executeTest()
        self.actionStop()
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
        cursor.execute("insert into detail_unit_tests(master_id,step_id) values(?,?)",self.step.master_id,self.step.current_step)
        cursor.execute("SELECT SCOPE_IDENTITY()")
        row = cursor.fetchone()
        self.step.id = row[0]
        cursor.close()
    def actionStop(self):
        cursor = self.cnxn.cursor()
        cursor.execute("update detail_unit_tests set elapse=CURRENT_TIMESTAMP where id=(?)",self.step.id)
        cursor.close()
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
        self.actionStart()
        self.executeTest()
        self.step.current_step = self.step.current_step + 1
        cursor.close()
    def executeTest(self):
        print(self.step.action)
        if self.step.action == "get":
            print(self.step.url)
            self.driver.get(self.step.url)
        elif self.step.action == "by_name":
            self.driver.find_elwment_by_name(self.step.element)
            self.driver.send_keys(self.step.keys)
            if len(self.step.keys_append)>0:
                self.driver.send_keys(eval(self.step.keys_append))
            elif self.step.action == "wait":
                self.driver.wait(eval(self.step.element),self.step.keys_append)
        self.actionStop()

browser= Tester()
