from flask import Flask, jsonify, request
from flask_cors import CORS
from time import sleep
import threading
import logging
from playsound import playsound as play
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests

DORMANT_PERIOD = 7200  # 2 hours
CHECK_INTERVAL = 300 # 5 minutes
TP_VALUE = 3.0
SL_VALUE = 2.2

bot_thread = None
bot_running = False

# Set up logging to output to the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YahooPrice:
    def __init__(self, symbol):
        self.symbol = symbol

    def request(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
            }

            params = {
                'region': 'US',
                'lang': 'en-US',
                'includePrePost': 'false',
                'interval': '2m',
                'useYfid': 'true',
                'range': '1d',
                'corsDomain': 'finance.yahoo.com',
                '.tsrc': 'finance',
            }

            response = requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{self.symbol}', params=params, headers=headers)

            if response.ok:
                response_json = response.json()
                for options in response_json['chart']['result']:
                    price = float(options['meta']['regularMarketPrice'])
                    return price
                        
        except Exception as e:
            logger.error(e)
            return None

def check_candle_position(data, currency_name, ema):
    data = data.sort_index()
    recent_candle = data.iloc[-1]
    prev_candle = data.iloc[-2]

    if recent_candle['Low'] > recent_candle[ema]:
        if prev_candle['Close'] <= prev_candle[ema] and prev_candle['Low'] <= prev_candle[ema]:
            return f"sell {currency_name}"
            
        
    elif recent_candle['High'] < recent_candle[ema]:
        if prev_candle['Close'] >= prev_candle[ema] and prev_candle['High'] >= prev_candle[ema]:
            return f"buy {currency_name}"
        
    return "hold"

def ema_stochastic_strategy(data, currency_name):
    # Sort the data by index
    data = data.sort_index()
    
    # Calculate EMAs
    data['EMA_21'] = ta.ema(data['Close'], length=21)
    data['EMA_55'] = ta.ema(data['Close'], length=55)
    
    # Calculate Stochastic Oscillator
    stoch = ta.stoch(data['High'], data['Low'], data['Close'], k=14, d=3, smooth_k=3)
    data = data.join(stoch)
    
    # Drop rows with NaN values
    data.dropna(inplace=True)
    
    def is_bullish_engulfing(row):
        return row['Close'] > row['Open'] and row['Prev_Close'] < row['Prev_Open'] and row['Close'] > row['Prev_Open'] and row['Open'] < row['Prev_Close']
    
    def is_bearish_engulfing(row):
        return row['Close'] < row['Open'] and row['Prev_Close'] > row['Prev_Open'] and row['Close'] < row['Prev_Open'] and row['Open'] > row['Prev_Close']
    
    def is_hammer(row):
        body = abs(row['Close'] - row['Open'])
        lower_wick = row['Open'] - row['Low'] if row['Close'] > row['Open'] else row['Close'] - row['Low']
        upper_wick = row['High'] - row['Close'] if row['Close'] > row['Open'] else row['High'] - row['Open']
        return lower_wick > 2 * body and upper_wick < body
    
    def is_shooting_star(row):
        body = abs(row['Close'] - row['Open'])
        lower_wick = row['Open'] - row['Low'] if row['Close'] > row['Open'] else row['Close'] - row['Low']
        upper_wick = row['High'] - row['Close'] if row['Close'] > row['Open'] else row['High'] - row['Open']
        return upper_wick > 2 * body and lower_wick < body
    
    data['Prev_Close'] = data['Close'].shift(1)
    data['Prev_Open'] = data['Open'].shift(1)
    
    data['Bullish_Engulfing'] = data.apply(is_bullish_engulfing, axis=1)
    data['Bearish_Engulfing'] = data.apply(is_bearish_engulfing, axis=1)
    data['Hammer'] = data.apply(is_hammer, axis=1)
    data['Shooting_Star'] = data.apply(is_shooting_star, axis=1)
    
    # Drop rows with NaN values
    data.dropna(inplace=True)
    
    # Get the recent and previous candle data
    recent_candle = data.iloc[-1]
    prev_candle = data.iloc[-2]
    
    # Generate signals based on the strategy criteria
    if (recent_candle['EMA_21'] > recent_candle['EMA_55'] and
        recent_candle['STOCHk_14_3_3'] < 20 and
        recent_candle['STOCHk_14_3_3'] > prev_candle['STOCHk_14_3_3'] and
        (recent_candle['Bullish_Engulfing'] or recent_candle['Hammer'])):
        signal = f"buy {currency_name}"
    elif (recent_candle['EMA_21'] < recent_candle['EMA_55'] and
          recent_candle['STOCHk_14_3_3'] > 80 and
          recent_candle['STOCHk_14_3_3'] < prev_candle['STOCHk_14_3_3'] and
          (recent_candle['Bearish_Engulfing'] or recent_candle['Shooting_Star'])):
        signal = f"sell {currency_name}"
    else:
        signal = "hold"
    
    return signal

def forex_pair_position(position, close, last_atr, currency_name, algo):
    if position.startswith("sell"):
        tp = round(close - (last_atr * TP_VALUE), 4)
        sl = round(close + (last_atr * SL_VALUE), 4)
        play('not.mp3')
        message = {
            "action": "sell",
            "pair": currency_name,
            "entry": close,
            "takeProfit": tp,
            "stopLoss": sl,
            "algo":algo
        }

    elif position.startswith("buy"):
        tp = round(close + (last_atr * TP_VALUE), 4)
        sl = round(close - (last_atr * SL_VALUE), 4)
        play('not.mp3')
        message = {
            "action": "buy",
            "pair": currency_name,
            "entry": close,
            "takeProfit": tp,
            "stopLoss": sl,
            "algo":algo
        }

    elif position.startswith("hold"):
        message = {
            "action": "none",
            "pair": currency_name,
            "entry": 0.000,
            "takeProfit": 0.000,
            "stopLoss": 0.000,
            "algo":algo
        }

    logger.info(message)
    return message    

last_signal = {}  # Global variable to store the last signal for each pair

def bot_main():
    global bot_running, last_signal
    forex_pairs = [
        "JPY=X", "GBPJPY=X", "AUDJPY=X", "AUDCAD=X", "USDCAD=X",
        "CADJPY=X", "CHFJPY=X", "EURJPY=X", "EURCHF=X", "EURCAD=X",
        "EURAUD=X", "CADCHF=X", "AUDNZD=X", "AUDCHF=X", "BTC-USD"
    ]

    while bot_running:
        try:
            start_date_1h = (pd.Timestamp.now() - pd.DateOffset(days=14)).strftime('%Y-%m-%d')
            start_date_5m = (pd.Timestamp.now() - pd.DateOffset(days=14)).strftime('%Y-%m-%d')  # Shorter history for 5m data
            
            for forex_pair in forex_pairs:
                currency_name = forex_pair.replace("=X", "")

                # 1. Get 1-hour data and apply strategy
                data_1h = yf.download(tickers=forex_pair, start=start_date_1h, interval='1h')
                if data_1h.empty:
                    logger.warning(f"No 1-hour data fetched for {forex_pair}.")
                else:
                    data_1h['Ema_55'] = data_1h['Close'].ewm(span=55, adjust=False).mean()
                    data_1h['atr'] = ta.atr(data_1h['High'], data_1h['Low'], data_1h['Close'], length=14)

                    # Current values for 1-hour data
                    close_1h = round(float(data_1h['Close'].iloc[-1]), 4)
                    last_atr_1h = float(data_1h['atr'].iloc[-1])

                    # Run 1-hour strategy and save result
                    position_1h = ema_stochastic_strategy(data_1h, currency_name)
                    last_signal[f"{forex_pair}_1h_algo"] = forex_pair_position(position_1h, close_1h, last_atr_1h, currency_name, "1h algo")

                # 2. Get 5-minute data and apply strategy
                data_5m = yf.download(tickers=forex_pair, start=start_date_5m, interval='5m')
                if data_5m.empty:
                    logger.warning(f"No 5-minute data fetched for {forex_pair}.")
                else:
                    data_5m['Ema_55'] = data_5m['Close'].ewm(span=55, adjust=False).mean()
                    data_5m['atr'] = ta.atr(data_5m['High'], data_5m['Low'], data_5m['Close'], length=14)

                    # Current values for 5-minute data
                    close_5m = round(float(data_5m['Close'].iloc[-1]), 4)
                    last_atr_5m = float(data_5m['atr'].iloc[-1])

                    # Run 5-minute strategy and save result
                    position_5m = check_candle_position(data_5m, currency_name, "Ema_55")
                    last_signal[f"{forex_pair}_5m_algo"] = forex_pair_position(position_5m, close_5m, last_atr_5m, currency_name, "5m algo")

            # Wait for the defined interval before running again
            sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error occurred: {e}")
            sleep(60)  # Retry after a minute if an error occurs


app = Flask(__name__)
CORS(app)

@app.route('/get_price/<symbol>', methods=['GET'])
def get_price(symbol):
    yahoo_price = YahooPrice(symbol)
    price = yahoo_price.request()
    if price is not None:
        logger.info(f'Fetched price for {symbol}: {price}')
        return jsonify({'symbol': symbol, 'price': price})
    else:
        logger.error(f'Could not fetch price for {symbol}')
        return jsonify({'error': 'Could not fetch price'}), 500

@app.route('/start_bot', methods=['POST'])
def start_bot():
    global bot_thread, bot_running
    if not bot_running:
        bot_running = True
        bot_thread = threading.Thread(target=bot_main)
        bot_thread.start()
        logger.info('Bot started')
        return jsonify({"status": "Bot started"}), 200
    else:
        logger.warning('Bot already running')
        return jsonify({"status": "Bot already running"}), 400

@app.route('/stop_bot', methods=['POST'])
def stop_bot():
    global bot_running
    if bot_running:
        bot_running = False
        logger.info('Bot stopped')
        return jsonify({"status": "Bot stopped"}), 200
    else:
        logger.warning('Bot is not running')
        return jsonify({"status": "Bot is not running"}), 400

@app.route('/bot_status', methods=['GET'])
def bot_status():
    global bot_running
    return jsonify({"running": bot_running}), 200

@app.route('/last_signal', methods=['GET'])
def get_last_signal():
    global last_signal
    if last_signal is not None:
        return jsonify(last_signal), 200
    else:
        return jsonify({"error": "No signals available"}), 404
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5700)
