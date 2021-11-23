import time, json, pprint, queue
from pycoingecko import CoinGeckoAPI
import threading

UPDATE_RATE = 45

class CryptoCurrency(object):
    _name = ""
    _fname = ""
    _code = ""
    lastPriceUSD = 0.0
    lastPriceBTC = 0.0
    lastPriceETH = 0.0
    priceUSDChange24Hr = 0.0
    volumeUSD = 0.0
    updateTime = 0.0
    lastError = 0.0
    apiref = None
    
    def __init__(self, apiref, _fname, _name, _code):
        self.apiref = apiref
        self._fname = str(_fname)
        self._name = str(_name)
        self._code = str(_code)

    def update_helper(self, dct):
        self.lastPriceUSD = dct['usd']
        self.lastPriceBTC = dct['btc']
        self.lastPriceETH = dct['eth']
        self.priceUSDChange24Hr = dct['usd_24h_change']
        self.volumeUSD = dct['usd_24h_vol']
        self.updateTime = time.time()
        
    def __repr__(self):
        return "<CryptoCurrency %s (%s %s) lastUSD=%.3f lastBTC=%.3f lastETH=%.3f priceUSDChange24Hr=%.3f volumeUSD=%.3f updateTimeDelta=%.1f>" % \
                   (self._fname, self._name, self._code, \
                    self.lastPriceUSD, self.lastPriceBTC, self.lastPriceETH, self.priceUSDChange24Hr, self.volumeUSD, time.time() - self.updateTime)

class CryptoFetch(threading.Thread):
    cache = {}
    apiref = None
    ev = None
    k = None
    respq = None

    def __init__(self):
        threading.Thread.__init__(self)
        self.apiref = CoinGeckoAPI()
        self.ev = threading.Event()
        self.k = threading.Event()  # kill signal
        self.last_fetch = 0
        self.respq = queue.Queue()
        self.k.clear()
    
    def add_monitor(self, fullName, shortName, currencyCode):
        if currencyCode in self.cache:
            return
        self.cache[shortName] = CryptoCurrency(self.apiref, fullName, shortName, currencyCode)

    def get_coin(self, shortName):
        return self.cache[shortName]

    def run(self):
        while not self.k.is_set():
            self.ev.wait()
            self.ev.clear()
            
            print("API fetch...")

            coins = []
            for coin in self.cache.items():
                coins.append(coin[0])

            try:
                res = self.apiref.get_price(\
                    ids=coins, \
                    vs_currencies=['usd', 'btc', 'eth'], include_market_cap=True, include_24hr_vol=True, include_24hr_change=True, include_last_updated_at=True)

                self.respq.put(res)
            except Exception as e:
                print("Can't fetch from API in async worker thread: %r" % e)

    def update(self):
        # Push an update request, the inner thread (us) listens and updates.  Any responses
        # are updated asynchronously.
        if (time.time() - self.last_fetch) > UPDATE_RATE:
            print("Pinging thread")
            self.ev.set()
            self.last_fetch = time.time()

        # Are there any pending responses?
        if not self.respq.empty():
            res = self.respq.get()

            for kv in res.items():
                print(kv)
                self.cache[kv[0]].update_helper(kv[1])

    def kill(self):
        # Push a kill request
        self.k.set()

# Testbench
if __name__ == "__main__":
    f = CryptoFetch()
    
    f.add_monitor('bitcoin', 'BTC')
    f.add_monitor('ethereum', 'ETH')
    f.add_monitor('dogecoin', 'DOGE')
    f.add_monitor('chia', 'XCH')
    f.add_monitor('litecoin', 'LTC')

    f.start()
    i = 0

    while True:
        f.update()
        time.sleep(0.0167)

        i += 1
        i %= 100

        if i == 0:
            for coin in f.cache.items():
                print(coin)

    
