from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List
from itertools import permutations
import threading
import time

app = Flask(__name__)

# Global variable to store latest opportunities
latest_opportunities = []
latest_update_time = None
latest_pairs_count = 0

def get_binance_price(symbol_pair: str) -> float:
    """Fetch price for a given symbol pair from Binance"""
    try:
        response = requests.get(f'https://www.binance.com/en/trade/{symbol_pair}?type=spot')
        soup = BeautifulSoup(response.text, 'html.parser')
        element = soup.find("title")
        price_match = re.search(r'\d+\.\d+', element.get_text())
        return float(price_match.group()) if price_match else 0.0
    except Exception as e:
        print(f"Error fetching {symbol_pair} price: {e}")
        return 0.0

def get_all_trading_pairs() -> Dict[str, float]:
    """Get all possible trading pairs and their prices"""
    base_currencies = ['BTC', 'ETH', 'USDT', 'BNB', 'ADA', 'DOT', 'XRP', 'SOL', 'DOGE', 'MATIC']
    pairs = {}
    
    for base in base_currencies:
        for quote in base_currencies:
            if base != quote:
                pair = f"{base}_{quote}"
                price = get_binance_price(pair)
                if price > 0:
                    pairs[pair] = price
    
    return pairs

def find_arbitrage_cycles(prices: Dict[str, float], min_profit: float = 0.01) -> List[dict]:
    """
    Find all possible arbitrage cycles with profit above threshold
    Returns list of dictionaries containing cycle path and expected profit
    """
    # Extract unique currencies from trading pairs
    currencies = set()
    for pair in prices.keys():
        base, quote = pair.split('_')
        currencies.add(base)
        currencies.add(quote)
    
    opportunities = []
    
    # Check all possible 3-way cycles
    for cycle in permutations(currencies, 3):
        profit = calculate_cycle_profit(cycle, prices)
        if profit > min_profit:
            opportunities.append({
                'cycle': cycle,
                'profit_percent': (profit - 1) * 100,
                'path': ' → '.join(cycle + (cycle[0],))
            })
    
    return opportunities

def calculate_cycle_profit(cycle: tuple, prices: Dict[str, float]) -> float:
    """Calculate the profit multiplier for a given cycle"""
    total_multiplier = 1.0
    
    for i in range(len(cycle)):
        current = cycle[i]
        next_currency = cycle[(i + 1) % len(cycle)]
        
        # Try direct pair
        direct_pair = f"{current}_{next_currency}"
        inverse_pair = f"{next_currency}_{current}"
        
        if direct_pair in prices:
            total_multiplier *= prices[direct_pair]
        elif inverse_pair in prices:
            total_multiplier *= (1 / prices[inverse_pair])
        else:
            return 0.0  # If any pair is missing, cycle is invalid
    
    return total_multiplier

def background_task():
    """Background task to continuously update prices and opportunities"""
    global latest_opportunities, latest_update_time, latest_pairs_count
    
    while True:
        print("\nFetching current prices...")
        prices = get_all_trading_pairs()
        latest_pairs_count = len(prices)
        
        opportunities = find_arbitrage_cycles(prices)
        latest_opportunities = sorted(opportunities, key=lambda x: x['profit_percent'], reverse=True)
        latest_update_time = time.strftime('%Y-%m-%d %H:%M:%S')
        
        time.sleep(60)  # Wait 60 seconds before next update

@app.route('/')
def index():
    return render_template('index.html',
                         opportunities=latest_opportunities,
                         update_time=latest_update_time,
                         pairs_count=latest_pairs_count)

def main():
    # Start the background task in a separate thread
    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()
    
    # Run the Flask app
    app.run(debug=True, use_reloader=False)

if __name__ == "__main__":
    main()