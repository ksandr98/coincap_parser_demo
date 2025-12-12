import requests
from bs4 import BeautifulSoup
import json
import csv
from datetime import datetime
from typing import List, Dict


class CMCParser:

    BASE_URL = "https://coinmarketcap.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_top_coins(self, limit: int = 100) -> List[Dict]:
        coins = []

        try:
            response = self.session.get(f"{self.BASE_URL}/")
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            scripts = soup.find_all('script')

            for script in scripts:
                if script.string and '__NEXT_DATA__' in str(script):
                    import re
                    json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                                          str(script), re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        listings = data.get('props', {}).get('initialState', {}).get('cryptocurrency', {}).get('listingLatest', {}).get('data', [])

                        for item in listings[:limit]:
                            if isinstance(item, dict):
                                coin = self._parse_coin_data(item)
                                if coin:
                                    coins.append(coin)

            if not coins:
                coins = self._parse_table(soup, limit)

        except Exception as e:
            print(f"Error fetching data: {e}")
            coins = self._fetch_via_api(limit)

        return coins

    def _parse_coin_data(self, item: dict) -> Dict:
        try:
            quote = item.get('quote', {}).get('USD', {})
            return {
                'rank': item.get('cmc_rank', item.get('rank')),
                'name': item.get('name'),
                'symbol': item.get('symbol'),
                'price': quote.get('price'),
                'change_1h': quote.get('percent_change_1h'),
                'change_24h': quote.get('percent_change_24h'),
                'change_7d': quote.get('percent_change_7d'),
                'market_cap': quote.get('market_cap'),
                'volume_24h': quote.get('volume_24h'),
                'circulating_supply': item.get('circulating_supply'),
            }
        except:
            return None

    def _parse_table(self, soup: BeautifulSoup, limit: int) -> List[Dict]:
        coins = []
        table = soup.find('table')

        if not table:
            return coins

        rows = table.find_all('tr')[1:limit+1]

        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 7:
                try:
                    coin = {
                        'rank': self._clean_number(cells[1].get_text(strip=True)),
                        'name': cells[2].get_text(strip=True).split('\n')[0],
                        'symbol': cells[2].find('p', class_='coin-item-symbol')
                                  or cells[2].get_text(strip=True).split('\n')[-1] if '\n' in cells[2].get_text() else '',
                        'price': self._clean_price(cells[3].get_text(strip=True)),
                        'change_24h': self._clean_percent(cells[4].get_text(strip=True)),
                        'change_7d': self._clean_percent(cells[5].get_text(strip=True)),
                        'market_cap': self._clean_price(cells[6].get_text(strip=True)),
                        'volume_24h': self._clean_price(cells[7].get_text(strip=True)) if len(cells) > 7 else None,
                    }
                    coins.append(coin)
                except Exception as e:
                    continue

        return coins

    def _fetch_via_api(self, limit: int) -> List[Dict]:
        coins = []
        try:
            api_url = "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing"
            params = {
                'start': 1,
                'limit': limit,
                'sortBy': 'market_cap',
                'sortType': 'desc',
                'convert': 'USD',
                'cryptoType': 'all',
                'tagType': 'all',
            }

            response = self.session.get(api_url, params=params)
            data = response.json()

            for item in data.get('data', {}).get('cryptoCurrencyList', []):
                quote = item.get('quotes', [{}])[0]
                coins.append({
                    'rank': item.get('cmcRank'),
                    'name': item.get('name'),
                    'symbol': item.get('symbol'),
                    'price': quote.get('price'),
                    'change_1h': quote.get('percentChange1h'),
                    'change_24h': quote.get('percentChange24h'),
                    'change_7d': quote.get('percentChange7d'),
                    'market_cap': quote.get('marketCap'),
                    'volume_24h': quote.get('volume24h'),
                    'circulating_supply': item.get('circulatingSupply'),
                })

        except Exception as e:
            print(f"API Error: {e}")

        return coins

    def _clean_number(self, text: str) -> int:
        try:
            return int(''.join(filter(str.isdigit, text)))
        except:
            return 0

    def _clean_price(self, text: str) -> float:
        try:
            cleaned = text.replace('$', '').replace(',', '').strip()
            return float(cleaned)
        except:
            return 0.0

    def _clean_percent(self, text: str) -> float:
        try:
            cleaned = text.replace('%', '').replace(',', '').strip()
            return float(cleaned)
        except:
            return 0.0

    def save_to_json(self, coins: List[Dict], filename: str = "coins.json"):
        output = {
            'timestamp': datetime.now().isoformat(),
            'count': len(coins),
            'data': coins
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(coins)} coins to {filename}")

    def save_to_csv(self, coins: List[Dict], filename: str = "coins.csv"):
        if not coins:
            return

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=coins[0].keys())
            writer.writeheader()
            writer.writerows(coins)
        print(f"Saved {len(coins)} coins to {filename}")


def main():
    parser = CMCParser()

    print("Fetching top 20 cryptocurrencies from CoinMarketCap...")
    coins = parser.get_top_coins(limit=20)

    if coins:
        print(f"\n{'='*80}")
        print(f"{'Rank':<6}{'Symbol':<10}{'Name':<20}{'Price':>15}{'24h %':>10}{'Market Cap':>20}")
        print(f"{'='*80}")

        for coin in coins:
            price = coin.get('price', 0)
            change = coin.get('change_24h', 0)
            mcap = coin.get('market_cap', 0)

            price_str = f"${price:,.2f}" if price else "N/A"
            change_str = f"{change:+.2f}%" if change else "N/A"
            mcap_str = f"${mcap/1e9:,.2f}B" if mcap else "N/A"

            print(f"{coin.get('rank', 'N/A'):<6}{coin.get('symbol', 'N/A'):<10}{coin.get('name', 'N/A'):<20}{price_str:>15}{change_str:>10}{mcap_str:>20}")

        print(f"{'='*80}\n")

        parser.save_to_json(coins, "coins_data.json")
        parser.save_to_csv(coins, "coins_data.csv")
    else:
        print("No data retrieved")


if __name__ == "__main__":
    main()
