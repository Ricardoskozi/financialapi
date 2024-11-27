import requests
from flask import Flask, jsonify, request
from eodhd import APIClient
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit
import os
import threading
from datetime import datetime, date

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
socketio = SocketIO(app, async_mode='eventlet')

eodhd_api_key = os.getenv('EODHD_API_KEY')
your_api_key = os.getenv('MY_API_KEY')
client = APIClient(eodhd_api_key)

def check_api_key(request):
    api_key = request.headers.get('X-API-KEY') or request.args.get('api_key')
    if api_key != your_api_key:
        return {'error': 'Unauthorized'}, 401
    return None

@app.route('/economic_calendar', methods=['GET'])
def economic_calendar():
    auth_error = check_api_key(request)
    if auth_error:
        return jsonify(auth_error)

    # Get query parameters with default values
    date_from_str = request.args.get('date_from', date.today().isoformat())
    date_to_str = request.args.get('date_to', date.today().isoformat())
    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # Fetch economic events within the specified date range
    try:
        events = client.get_economic_events_data(date_from=f'{date_from}', date_to=f'{date_to}')
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    return jsonify(events)


@app.route('/end_of_day_data', methods=['GET'])
def end_of_day_data():
    auth_error = check_api_key(request)
    if auth_error:
        return jsonify(auth_error)

    # Get query parameters with default values
    date_from_str = request.args.get('date_from', date.today().isoformat())
    date_to_str = request.args.get('date_to', date.today().isoformat())

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400
    symbol = request.args.get('symbol', 'AAPL.US')
    try:
        data = client.get_eod_historical_stock_market_data(symbol,from_date=f'{date_from}', to_date=f'{date_to}')
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    return jsonify(data)

@app.route('/list_of_exchanges', methods=['GET'])
def list_of_exchanges():
    auth_error = check_api_key(request)
    if auth_error:
        return jsonify(auth_error)
    data = client.get_list_of_exchanges()
    return jsonify(data)

@app.route('/real_time_data', methods=['GET'])
def real_time_data():
    auth_error = check_api_key(request)
    if auth_error:
        return jsonify(auth_error)
    s = request.args.get('s')
    print(s)
    symbol = request.args.get('symbol', 'AAPL.US')
    try:
        data = client.get_live_stock_prices(ticker=symbol, s=s)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    return jsonify(data)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('start_stream')
def handle_start_stream(data):
    auth_error = check_api_key(request)
    if auth_error:
        emit('error', auth_error)
        return

    symbol = data.get('symbol', 'AAPL.US')
    def stream_data():
        try:
            for event in client.get_stream(symbol):
                emit('data', event)
        except Exception as e:
            emit('error', {'error': str(e)})

    threading.Thread(target=stream_data).start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)