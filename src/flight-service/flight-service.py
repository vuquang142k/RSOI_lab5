import os
from flask import Flask, request, Response
from flight_db import FlightsDataBase 

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route('/')
def FS_hello_world():
    statement = 'Flight service!'
    return statement


@app.route('/api/v1/flights', methods=['GET'])
def FS_get_flights():
    instance = FlightsDataBase()
    args = dict(request.args)
    result = instance.get_flights(int(args['page']), int(args['size']))
    instance.db_disconnect()
    if result is None:
        return Response(status=404)
    return result


@app.route('/api/v1/flights/exist', methods=['GET'])
def FS_get_flight_exist():
    instance = FlightsDataBase()
    args = request.data.decode()
    result = instance.get_flight_exist(args)
    instance.db_disconnect()
    if result is False:
        return Response(status=404)
    return result


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8060))
    app.run(debug=True, port=port, host="0.0.0.0")
