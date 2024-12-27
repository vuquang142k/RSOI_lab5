import os
from flask import Flask, request, Response, redirect, render_template, session, url_for
import requests

import json
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from auth0.v3.authentication.token_verifier import TokenVerifier, AsymmetricSignatureVerifier


# Preparing
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)

baseUrlBonus = 'http://bonus:8050'
baseUrlFlight = 'http://flight:8060'
baseUrlTickets = 'http://ticket:8070'


def validation(id_token):
    domain = env.get("AUTH0_DOMAIN")
    client_id = env.get("AUTH0_CLIENT_ID")

    jwks_url = 'https://{}/.well-known/jwks.json'.format(domain)
    issuer = 'https://{}/'.format(domain)

    try:
        sv = AsymmetricSignatureVerifier(jwks_url)  # Reusable instance
        tv = TokenVerifier(signature_verifier=sv, issuer=issuer, audience=client_id)
        tv.verify(id_token)
        return True
    except:
        return False


@app.route('/')
def GWS_hello_world():
    statement = 'Gateway service!'
    return statement


@app.route('/api/v1/flights', methods=['GET'])
def GWS_get_flights():

    if 'Authorization' not in request.headers:
        return Response(status=401)
    # if not validation(request.headers['Authorization'].split(' ')[1]):
    #     return Response(status=401)

    headers = {'Content-type': 'application/json'}
    param = dict(request.args)
    response = requests.get(baseUrlFlight + '/api/v1/flights', params=param, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return Response(status=404)


@app.route('/api/v1/privilege', methods=['GET'])
def GWS_get_privilege():

    if 'Authorization' not in request.headers:
        return Response(status=401)
    # if not validation(request.headers['Authorization'].split(' ')[1]):
    #     return Response(status=401)

    response = requests.get(baseUrlBonus + '/api/v1/privilege', headers=request.headers)

    if response.status_code == 200:
        return response.json()
    else:
        return Response(status=404)


@app.route('/api/v1/me', methods=['GET'])
def GWS_get_me_info():
    if 'Authorization' not in request.headers:
        return Response(status=401)
    # if not validation(request.headers['Authorization'].split(' ')[1]):
    #     return Response(status=401)

    result = dict()
    result['tickets'] = GWS_get_tickets()
    result['privilege'] = GWS_get_privilege()
    del result['privilege']['history']
    return result


@app.route('/api/v1/tickets', methods=['GET'])
def GWS_get_tickets():
    if 'Authorization' not in request.headers:
        return Response(status=401)
    # if not validation(request.headers['Authorization'].split(' ')[1]):
    #     return Response(status=401)

    # Get ticket Uid, flight number and status
    info_tickets = requests.get(baseUrlTickets + '/api/v1/tickets', headers=request.headers).json()

    for ticket in info_tickets:
        info_flights = requests.get(baseUrlFlight + '/api/v1/flights/exist', data=ticket['flightNumber']).json()
        ticket['fromAirport'] = info_flights['fromAirport']
        ticket['toAirport'] = info_flights['toAirport']
        ticket['date'] = info_flights['date']
        ticket['price'] = info_flights['price']

    return info_tickets


@app.route('/api/v1/tickets', methods=['POST'])
def GWS_post_tickets():
    if 'Authorization' not in request.headers:
        return Response(status=401)
    # if not validation(request.headers['Authorization'].split(' ')[1]):
    #     return Response(status=401)

    # Get purchase information
    buy_info = request.json

    # Get username
    headers = {'content-type': "application/json", 'Authorization': f"{request.headers['Authorization']}"}
    resp = requests.get(f"https://{env.get('AUTH0_DOMAIN')}/userinfo", headers=headers)

    username = resp.json()['name']

    # Checking the existing flight number
    flight_exist = requests.get(baseUrlFlight + '/api/v1/flights/exist', data=buy_info['flightNumber']).json()

    # Return Error: 404 Not Found if flight number don't exist
    if not flight_exist:
        return Response(status=404)

    # Information for the ticket database
    data = {'username': username,
            'flightNumber': flight_exist['flightNumber'],
            'price': flight_exist['price'],
            'status': 'PAID'}

    # Get ticket UID
    ticket_uid = requests.post(baseUrlTickets + '/api/v1/tickets/buy', json=data)

    # Fill the first part of the response
    response = dict()
    response['ticketUid'] = ticket_uid.text
    response['flightNumber'] = flight_exist['flightNumber']
    response['fromAirport'] = flight_exist['fromAirport']
    response['toAirport'] = flight_exist['toAirport']
    response['date'] = flight_exist['date']
    response['price'] = flight_exist['price']
    response['status'] = 'PAID'

    # Processing bonus points (the second part of the response)
    if buy_info['paidFromBalance']:
        # Debiting from the bonus account
        data = {'username': username, 'ticketUid': ticket_uid.text, 'price': int(flight_exist['price'])}
        paid_by_bonuses = int(requests.post(baseUrlBonus + '/api/v1/privilege/debit', json=data).text)

        response['paidByMoney'] = data['price'] - paid_by_bonuses
        response['paidByBonuses'] = paid_by_bonuses
    else:
        # Replenishment of the bonus account
        data = {'username': username, 'ticketUid': ticket_uid.text, 'price': int(flight_exist['price'])}
        requests.post(baseUrlBonus + '/api/v1/privilege/replenishment', json=data)

        response['paidByMoney'] = flight_exist['price']
        response['paidByBonuses'] = 0

    # Information about privileges after ticket purchase (the third part of the response)
    privilege_info = requests.get(baseUrlBonus + '/api/v1/privilege', headers=request.headers).json()
    del privilege_info['history']

    response['privilege'] = privilege_info

    return response


@app.route('/api/v1/tickets/<string:ticketUid>', methods=['GET'])
def GWS_get_ticket_by_uid(ticketUid):
    if 'Authorization' not in request.headers:
        return Response(status=401)
    # if not validation(request.headers['Authorization'].split(' ')[1]):
    #     return Response(status=401)

    # Get flight number and status
    info_tickets = requests.get(baseUrlTickets + f'/api/v1/tickets/{ticketUid}', headers=request.headers)

    if info_tickets.status_code != 200:
        return Response(status=404)

    info_tickets = info_tickets.json()

    # Get flight number and status
    info_flights = requests.get(baseUrlFlight + '/api/v1/flights/exist', data=info_tickets['flightNumber']).json()

    response = dict()
    response['ticketUid'] = ticketUid
    response['flightNumber'] = info_tickets['flightNumber']
    response['fromAirport'] = info_flights['fromAirport']
    response['toAirport'] = info_flights['toAirport']
    response['date'] = info_flights['date']
    response['price'] = info_flights['price']
    response['status'] = info_tickets['status']

    return response


@app.route('/api/v1/tickets/<string:ticketUid>', methods=['DELETE'])
def GWS_ticket_refund(ticketUid):
    if 'Authorization' not in request.headers:
        return Response(status=401)
    # if not validation(request.headers['Authorization'].split(' ')[1]):
    #     return Response(status=401)

    tickets_response = requests.delete(baseUrlTickets + f'/api/v1/tickets/{ticketUid}')
    if tickets_response.status_code != 204:
        return Response(status=404)

    privilege_response = requests.delete(baseUrlBonus + f'/api/v1/privilege/{ticketUid}', headers=request.headers)
    if privilege_response.status_code != 204:
        return Response(status=404)

    return Response(status=204)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, port=8080, host="0.0.0.0")
