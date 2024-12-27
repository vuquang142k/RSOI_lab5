import os
from flask import Flask, request, Response
from ticket_db import TicketsDataBase
import requests
from dotenv import find_dotenv, load_dotenv
from os import environ as env

app = Flask(__name__)

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


@app.route('/')
def TS_hello_world():
    statement = 'Ticket service!'
    return statement


@app.route('/api/v1/tickets/buy', methods=['POST'])
def TS_buy_ticket():
    data = request.json
    instance = TicketsDataBase()
    ticket_uid = instance.db_buy_ticket(data=data)
    instance.db_disconnect()
    return ticket_uid


@app.route('/api/v1/tickets', methods=['GET'])
def TS_get_ticket():
    # Get username
    headers = {'content-type': "application/json", 'Authorization': f"{request.headers['Authorization']}"}
    resp = requests.get(f"https://{env.get('AUTH0_DOMAIN')}/userinfo", headers=headers)
    username = resp.json()['name']

    instance = TicketsDataBase()
    result = instance.db_get_tickets(username)
    instance.db_disconnect()
    return result


@app.route('/api/v1/tickets/<string:ticketUid>', methods=['GET'])
def TS_get_ticket_by_uid(ticketUid):
    # Get username
    headers = {'content-type': "application/json", 'Authorization': f"{request.headers['Authorization']}"}
    resp = requests.get(f"https://{env.get('AUTH0_DOMAIN')}/userinfo", headers=headers)
    username = resp.json()['name']

    instance = TicketsDataBase()
    result = instance.db_get_ticket_by_uid(ticketUid, username)
    instance.db_disconnect()
    if not result:
        return Response(status=404)
    return result


@app.route('/api/v1/tickets/<string:ticketUid>', methods=['DELETE'])
def TS_ticket_refund(ticketUid):
    instance = TicketsDataBase()
    result = instance.db_ticket_refund(ticketUid)
    instance.db_disconnect()
    if not result:
        return Response(status=404)
    return Response(status=204)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8070))
    app.run(debug=True, port=port, host="0.0.0.0")
