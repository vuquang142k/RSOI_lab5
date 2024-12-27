import psycopg2
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import uuid


class TicketsDataBase:
    def __init__(self):
        try:
            # Establishing a database connection
            self.connection = psycopg2.connect(
                database="tickets",
                user="program",
                password="test",
                host="postgres",
                port="5432"
            )

            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            self.cursor = self.connection.cursor()

        except (Exception, Error) as error:
            print("Ошибка при работе с PostgreSQL", error)

        # Checking the existence of table 'ticket'
        if not self.db_check_table('ticket'):
            self.db_create_table_ticket()

    def db_check_table(self, db_name):
        self.cursor.execute(
            f"SELECT EXISTS (SELECT 1 AS result FROM pg_tables WHERE tablename = '{db_name}');")
        tableExists = self.cursor.fetchone()[0]
        return tableExists

    def db_create_table_ticket(self):

        # Create a table 'ticket'
        create_table_query = '''CREATE TABLE ticket
                                (
                                    id            SERIAL PRIMARY KEY,
                                    ticket_uid    uuid UNIQUE NOT NULL,
                                    username      VARCHAR(80) NOT NULL,
                                    flight_number VARCHAR(20) NOT NULL,
                                    price         INT         NOT NULL,
                                    status        VARCHAR(20) NOT NULL
                                        CHECK (status IN ('PAID', 'CANCELED'))
                                );'''
        self.cursor.execute(create_table_query)

        return

    def db_buy_ticket(self, data):
        # Generate a random UUID for the ticket
        ticket_uid = str(uuid.uuid4())

        # Adding the record to the database
        query = "INSERT INTO ticket (ticket_uid, username, flight_number, price, status) " \
                "VALUES (%s,%s,%s,%s,%s)"

        insert_data = (ticket_uid, data['username'], data['flightNumber'], int(data['price']), data['status'])

        self.cursor.execute(query, insert_data)

        return ticket_uid

    def db_ticket_refund(self, ticket_uid):
        # Checking the existence of a ticket
        query = f"SELECT EXISTS(SELECT * FROM ticket WHERE ticket_uid = '{ticket_uid}');"
        self.cursor.execute(query)
        result = self.cursor.fetchone()[0]

        # Exiting the function with the value False
        if not result:
            return result

        # Ticket status update to 'CANCELED'
        query = f"UPDATE ticket SET status='CANCELED' WHERE ticket_uid = '{ticket_uid}'"
        self.cursor.execute(query)

        return result

    def db_get_tickets(self, username):

        # Check that the ticket belongs to the user
        query = f"SELECT EXISTS(SELECT * FROM ticket WHERE  username = '{username}');"
        self.cursor.execute(query)
        result = self.cursor.fetchone()[0]

        # Exiting the function with the value False
        if not result:
            return "You haven't bought any tickets yet!"

        # Ticket information (ticket_uid, flight_number, status)
        query = f"SELECT ticket_uid, flight_number, status FROM ticket WHERE username = '{username}';"
        self.cursor.execute(query)

        # Convert Ticket information from tuple to json
        rows = self.cursor.fetchall()
        result = list()
        for row in rows:
            d = dict()
            d['ticketUid'] = row[0]
            d['flightNumber'] = row[1]
            d['status'] = row[2]
            result.append(d)
        return result

    def db_get_ticket_by_uid(self, ticket_uid, username):

        # Check that the ticket belongs to the user
        query = f"SELECT EXISTS(SELECT * FROM ticket WHERE ticket_uid = '{ticket_uid}' AND username = '{username}');"
        self.cursor.execute(query)
        result = self.cursor.fetchone()[0]

        # Exiting the function with the value False
        if not result:
            return result

        # Ticket information (flight_number, status) by ticket_uid
        query = f"SELECT flight_number, status FROM ticket WHERE ticket_uid = '{ticket_uid}';"
        self.cursor.execute(query)

        # Convert Ticket information from tuple to json
        tmp = self.cursor.fetchone()
        result = dict()
        result['flightNumber'] = tmp[0]
        result['status'] = tmp[1]

        return result

    def db_disconnect(self):
        self.cursor.close()
        self.connection.close()
