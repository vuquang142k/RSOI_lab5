import psycopg2
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class FlightsDataBase:
    def __init__(self):
        try:
            # Establishing a database connection
            self.connection = psycopg2.connect(
                database="flights",
                user="program",
                password="test",
                host="postgres",
                port="5432"
            )

            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            self.cursor = self.connection.cursor()

        except (Exception, Error) as error:
            print("Ошибка при работе с PostgreSQL", error)

        # Checking the existence of table 'airport'
        if not self.db_check_table('airport'):
            self.db_create_table_airport()

        # Checking the existence of table 'flight'
        if not self.db_check_table('flight'):
            self.db_create_table_flight()

    def db_check_table(self, db_name):
        self.cursor.execute(
            f"SELECT EXISTS (SELECT 1 AS result FROM pg_tables WHERE tablename = '{db_name}');")
        tableExists = self.cursor.fetchone()[0]
        return tableExists

    def db_create_table_airport(self):

        # Create a table 'airport'
        create_table_query = '''CREATE TABLE airport
                                (
                                    id      SERIAL PRIMARY KEY,
                                    name    VARCHAR(255),
                                    city    VARCHAR(255),
                                    country VARCHAR(255)
                                );'''
        self.cursor.execute(create_table_query)

        # Add the first test record ('Шереметьево', 'Москва', 'Россия')
        insert_query = "INSERT INTO airport (name, city, country) VALUES (%s,%s,%s);"
        insert_data = ('Шереметьево', 'Москва', 'Россия')
        self.cursor.execute(insert_query, insert_data)

        # Add the second test record ('Пулково', 'Санкт-Петербург', 'Россия')
        insert_query = "INSERT INTO airport (name, city, country) VALUES (%s,%s,%s);"
        insert_data = ('Пулково', 'Санкт-Петербург', 'Россия')
        self.cursor.execute(insert_query, insert_data)

        return

    def db_create_table_flight(self):

        # Create a table 'flight'
        create_table_query = '''CREATE TABLE flight
                                (
                                    id              SERIAL PRIMARY KEY,
                                    flight_number   VARCHAR(20)              NOT NULL,
                                    datetime        TIMESTAMP WITH TIME ZONE NOT NULL,
                                    from_airport_id INT REFERENCES airport (id),
                                    to_airport_id   INT REFERENCES airport (id),
                                    price           INT                      NOT NULL
                                );'''
        self.cursor.execute(create_table_query)

        # Add the first test record ('AFL031', '2021-10-08 20:00', 2, 1, 1500)
        insert_query = 'INSERT INTO flight (flight_number, datetime, from_airport_id, to_airport_id, price) ' \
                       'VALUES (%s,%s,%s,%s,%s);'
        insert_data = ('AFL031', '2021-10-08 20:00', 2, 1, 1500)
        self.cursor.execute(insert_query, insert_data)

        return

    def get_flights(self, page, size):

        # Getting data: flight_number, from_airport, to_airport, datetime, price
        query = """SELECT flight_number,
                    (SELECT city ||' '||name FROM airport WHERE flight.from_airport_id = airport.id) AS from_airport,
                    (SELECT city ||' '||name FROM airport WHERE flight.to_airport_id = airport.id) AS to_airport,
                    datetime, price
                    FROM flight;"""
        self.cursor.execute(query)
        flight_info = self.cursor.fetchall()

        # Displaying the amount of information on the page
        if (page - 1) * size > len(flight_info):
            return None
        elif page * size > len(flight_info):
            page_slice = len(flight_info) % size
            flight_info = flight_info[(page - 1) * size:(page - 1) * size + page_slice]
        else:
            flight_info = flight_info[(page - 1) * size:page * size]

        # Forming the response (page, pageSize, totalElements)
        response = {'page': page, 'pageSize': size, 'totalElements': len(flight_info), 'items': []}

        # Forming the response (items)
        for item in flight_info:
            d = dict()
            d['flightNumber'] = item[0]
            d['fromAirport'] = item[1]
            d['toAirport'] = item[2]
            d['date'] = item[3]
            d['price'] = item[4]
            response['items'].append(d)

        return response

    def get_flight_exist(self, flight_number):

        # Checking the flight number
        query = f"SELECT EXISTS(SELECT * FROM flight WHERE flight_number = '{flight_number}');"
        self.cursor.execute(query)
        result = self.cursor.fetchone()[0]

        # Flight Number Information
        if result:
            query = f"SELECT " \
                    f"(SELECT city ||' '||name FROM airport WHERE flight.from_airport_id = airport.id) AS from_airport, " \
                    f"(SELECT city ||' '||name FROM airport WHERE flight.to_airport_id = airport.id) AS to_airport, " \
                    f"datetime, price FROM flight WHERE flight_number = '{flight_number}';"
            self.cursor.execute(query)
            flight_info = self.cursor.fetchone()
            d = dict()
            d['flightNumber'] = flight_number
            d['fromAirport'] = flight_info[0]
            d['toAirport'] = flight_info[1]
            d['date'] = flight_info[2]
            d['price'] = flight_info[3]
            result = d
        return result

    def db_disconnect(self):
        self.cursor.close()
        self.connection.close()
