import os
from flask import Flask, request, Response
from bonus_db import PrivilegesDataBase
import requests
from os import environ as env
from dotenv import find_dotenv, load_dotenv


app = Flask(__name__)

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


@app.route('/')
def BS_hello_world():
    statement = 'Bonus service!'
    return statement


@app.route('/api/v1/privilege', methods=['GET'])
def BS_get_privilege():
    instance = PrivilegesDataBase()

    # Get username
    headers = {'content-type': "application/json", 'Authorization': f"{request.headers['Authorization']}"}
    resp = requests.get(f"https://{env.get('AUTH0_DOMAIN')}/userinfo", headers=headers)
    args = resp.json()['name']

    result = instance.db_get_privilege(args)
    instance.db_disconnect()
    if result is None:
        return Response(status=404)

    return result


@app.route('/api/v1/privilege/debit', methods=['POST'])
def BS_debit_bonus():
    instance = PrivilegesDataBase()
    args = request.json
    result = instance.db_debit_bonus(args)
    instance.db_disconnect()
    return result


@app.route('/api/v1/privilege/replenishment', methods=['POST'])
def BS_replenishment_bonus():
    instance = PrivilegesDataBase()
    args = request.json
    instance.db_replenishment_bonus(args)
    instance.db_disconnect()
    return Response(status=200)


@app.route('/api/v1/privilege/<string:ticketUid>', methods=['DELETE'])
def BS_refund_of_bonuses(ticketUid):
    instance = PrivilegesDataBase()
    # Get username
    headers = {'content-type': "application/json", 'Authorization': f"{request.headers['Authorization']}"}
    resp = requests.get(f"https://{env.get('AUTH0_DOMAIN')}/userinfo", headers=headers)
    username = resp.json()['name']

    instance.db_refund_of_bonuses(ticketUid, username)
    instance.db_disconnect()

    return Response(status=204)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=True, port=port, host="0.0.0.0")
