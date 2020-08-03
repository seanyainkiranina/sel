import pyodbc
from databasecreds import DatabaseCreds
from scheduletask import ScheduleTask
import queue
from namegroups import Namegroups


class Scheduler:
    database_creds = None
    cnxn = None
    save_cursor = None
    cursor = None
    q = None
    dg = None

    def __init__(self, database_creds):
        self.cnxn = pyodbc.connect(database_creds.get_connectioN_string(), autocommit=True)
        self.q = queue.Queue()

    def get_schedule(self,dg):
        self.dg = dg
        cursor = self.cnxn.cursor()
        cursor.execute(
            "select master_batch.delay_time,master_batch.test_number,master_batch.throttle,master_batch.max_simul,master_batch.batch_number,"
            "master_batch.exec_limit,master_batch.increment,master_unit_tests.requests,master_unit_tests.browser,master_unit_tests.group_id "
            "from master_batch INNER JOIN master_unit_tests on master_unit_tests.id=master_batch.test_number where master_batch.done=0 and (master_batch.start_date is NULL or master_batch.start_date>CURRENT_TIMESTAMP or master_batch.start_date='1900-01-01 00:00:00') "
            "and (master_batch.end_date is NULL or master_batch.end_date<CURRENT_TIMESTAMP or master_batch.end_date='1900-01-01 00:00:00') ORDER BY RAND()")
        row = cursor.fetchone()
        while row:
            st = ScheduleTask()
            st.delay_time = row[0]
            st.test_number = row[1]
            st.throttle = row[2]
            st.max_simul = row[3]
            st.batch_number = row[4]
            st.exec_limit = row[5]
            st.increment = row[6]
            st.requests = row[7]
            st.browser = row[8]
            st.group_id = row[9]
            st.user_name = self.dg.get_individual(row[9])
            self.q.put(st)
            row = cursor.fetchone()
            print(st.batch_number)
        cursor.close()
        return self.q
