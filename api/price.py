import requests
import json
import logging 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YahooPrice:

    def __init__(self, symbol):
        self.symbol = symbol

    def request(self):
        try:
            headers = {
                'authority': 'query1.finance.yahoo.com',
                'accept': '*/*',
                'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
                'origin': 'https://finance.yahoo.com',
                'referer': f'https://finance.yahoo.com/quote/{self.symbol}=X?p={self.symbol}=X&.tsrc=fin-srch',
                'sec-ch-ua': '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Linux"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
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
                response = json.loads(response.text)
                for options in response['chart']['result']:
                    price = float(options['meta']['regularMarketPrice'])
                    return price
                        
        except Exception as e:
            logger.error(e)
            return None
