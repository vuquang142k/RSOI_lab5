import psycopg2
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class PrivilegesDataBase:
    def __init__(self):
        try:
            # Establishing a database connection
            self.connection = psycopg2.connect(
                database="privileges",
                user="program",
                password="test",
                host="postgres",
                port="5432"
            )

            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            self.cursor = self.connection.cursor()

        except (Exception, Error) as error:
            print("Ошибка при работе с PostgreSQL", error)

        # Checking the existence of table 'privilege'
        if not self.db_check_table('privilege'):
            self.db_create_table_privilege()

        # Checking the existence of table 'privilege_history'
        if not self.db_check_table('privilege_history'):
            self.db_create_table_privilege_history()

    def db_check_table(self, db_name):
        self.cursor.execute(
            f"SELECT EXISTS (SELECT 1 AS result FROM pg_tables WHERE tablename = '{db_name}');")
        tableExists = self.cursor.fetchone()[0]
        return tableExists

    def db_create_table_privilege(self):

        # Create table privilege
        create_table_query = '''CREATE TABLE privilege
                                (
                                    id       SERIAL PRIMARY KEY,
                                    username VARCHAR(80) NOT NULL UNIQUE,
                                    status   VARCHAR(80) NOT NULL DEFAULT 'BRONZE'
                                        CHECK (status IN ('BRONZE', 'SILVER', 'GOLD')),
                                    balance  INT
                                );'''
        self.cursor.execute(create_table_query)

        # Add the first test record ('Test Max', 'GOLD', '1500')
        insert_query = "INSERT INTO privilege (username, status, balance) VALUES (%s,%s,%s);"
        insert_data = ('Test Max', 'GOLD', 1500)
        self.cursor.execute(insert_query, insert_data)

        return

    def db_create_table_privilege_history(self):

        # Create a table 'privilege_history'
        create_table_query = '''CREATE TABLE privilege_history
                                (
                                    id             SERIAL PRIMARY KEY,
                                    privilege_id   INT REFERENCES privilege (id),
                                    ticket_uid     uuid        NOT NULL,
                                    datetime       TIMESTAMP   NOT NULL,
                                    balance_diff   INT         NOT NULL,
                                    operation_type VARCHAR(20) NOT NULL
                                        CHECK (operation_type IN ('FILL_IN_BALANCE', 'DEBIT_THE_ACCOUNT'))
                                );'''
        self.cursor.execute(create_table_query)

        # Add the first test record
        # (1, '049161bb-badd-4fa8-9d90-87c9a82b0668', '2021-10-08T19:59:19Z', 1500, 'FILL_IN_BALANCE')
        insert_query = 'INSERT INTO privilege_history ' \
                       '(privilege_id, ticket_uid, datetime, balance_diff, operation_type) ' \
                       'VALUES (%s,%s,%s,%s,%s);'
        insert_data = (1, '049161bb-badd-4fa8-9d90-87c9a82b0668', '2021-10-08T19:59:19Z', 1500, 'FILL_IN_BALANCE')
        self.cursor.execute(insert_query, insert_data)

        return

    def db_get_privilege(self, username):
        query = f"SELECT id FROM privilege WHERE username='{username}'"
        self.cursor.execute(query)

        user_id = self.cursor.fetchone()[0]

        query = f"SELECT status, balance FROM privilege WHERE username='{username}'"
        self.cursor.execute(query)
        user_info = self.cursor.fetchone()

        query = f"SELECT ticket_uid, datetime, balance_diff, operation_type FROM privilege_history " \
                f"WHERE privilege_id='{user_id}' "
        self.cursor.execute(query)
        user_history = self.cursor.fetchall()

        response = {'balance': user_info[1], 'status': user_info[0], 'history': []}

        for item in user_history:
            d = dict()
            d['ticketUid'] = item[0]
            d['date'] = item[1]
            d['balanceDiff'] = item[2]
            d['operationType'] = item[3]
            response['history'].append(d)

        return response

    def db_debit_bonus(self, data):

        # Get bonus balance
        query = f"SELECT balance FROM privilege WHERE username='{data['username']}'"
        self.cursor.execute(query)
        balance_bonus = int(self.cursor.fetchone()[0])

        # Calculation of accrual/write-off of bonuses
        if data['price'] <= balance_bonus:
            new_balance_bonus = balance_bonus - int(data['price'])
            balance_diff = int(data['price'])
        else:
            new_balance_bonus = 0
            balance_diff = balance_bonus

        # Updating the balance in the privilege table
        query = f"UPDATE privilege SET balance = {new_balance_bonus} WHERE username='{data['username']}';"
        self.cursor.execute(query)

        # Adding changes to the privilege history
        query = f"SELECT id FROM privilege WHERE username='{data['username']}'"
        self.cursor.execute(query)

        user_id = int(self.cursor.fetchone()[0])
        query = 'INSERT INTO privilege_history (privilege_id, ticket_uid, datetime, balance_diff, operation_type) ' \
                'VALUES (%s,%s,%s,%s,%s);'
        insert_data = (user_id, data['ticketUid'], '2021-10-08T19:59:19Z', balance_diff, 'DEBIT_THE_ACCOUNT')
        self.cursor.execute(query, insert_data)
        return str(balance_diff)

    def db_replenishment_bonus(self, data):

        balance_diff = int(0.1 * int(data['price']))

        # Updating the balance in the privilege table
        query = f"UPDATE privilege SET balance = balance+{balance_diff} WHERE username='{data['username']}';"
        self.cursor.execute(query)

        # Adding changes to the privilege history
        query = f"SELECT id FROM privilege WHERE username='{data['username']}'"
        self.cursor.execute(query)

        user_id = int(self.cursor.fetchone()[0])
        query = 'INSERT INTO privilege_history (privilege_id, ticket_uid, datetime, balance_diff, operation_type) ' \
                'VALUES (%s,%s,%s,%s,%s);'
        insert_data = (user_id, data['ticketUid'], '2021-10-08T19:59:19Z', balance_diff, 'FILL_IN_BALANCE')
        self.cursor.execute(query, insert_data)

        return

    def db_refund_of_bonuses(self, ticket_uid, username):

        # Debiting bonuses after ticket purchase cancellation
        query = f"SELECT privilege_id, balance_diff, operation_type FROM privilege_history " \
                f"WHERE ticket_uid='{ticket_uid}';"
        self.cursor.execute(query)
        privilege_id, balance_diff, operation_type = self.cursor.fetchone()

        if operation_type == 'FILL_IN_BALANCE':
            query = f"UPDATE privilege SET balance=balance-{balance_diff} WHERE username='{username}'"
            self.cursor.execute(query)

            query = 'INSERT INTO privilege_history (privilege_id, ticket_uid, datetime, balance_diff, operation_type) ' \
                    'VALUES (%s,%s,%s,%s,%s);'
            insert_data = (privilege_id, ticket_uid, '2021-10-08T19:59:19Z', balance_diff, 'DEBIT_THE_ACCOUNT')
            self.cursor.execute(query, insert_data)

        else:
            query = f"UPDATE privilege SET balance=balance+{balance_diff} WHERE username='{username}'"
            self.cursor.execute(query)

            query = 'INSERT INTO privilege_history (privilege_id, ticket_uid, datetime, balance_diff, operation_type) ' \
                    'VALUES (%s,%s,%s,%s,%s);'
            insert_data = (privilege_id, ticket_uid, '2021-10-08T19:59:19Z', balance_diff, 'FILL_IN_BALANCE')
            self.cursor.execute(query, insert_data)

        return

    def db_disconnect(self):
        self.cursor.close()
        self.connection.close()
