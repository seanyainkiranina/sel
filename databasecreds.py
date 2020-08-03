class DatabaseCreds:
    server = 'tcp:localhost'
    database = 'test_db'
    username = 'ka'
    password = 'chicago'

    def __init__(self,server="tcp:localhost",database="test_db",username="ka",password="chicago"):
        self.database=database
        self.server=server
        self.username=username
        self.password=password

    def get_database(self):
        return self.database

    def get_server(self):
        return self.server

    def get_username(self):
        return self.username

    def get_password(self):
        return self.password

    def get_connectioN_string(self):
        return 'DRIVER={ODBC Driver 17 for SQL Server};SERVER='+self.server+';MARS_Connection=Yes;DATABASE='+self.database+';UID='+self.username+';PWD='+ self.password
