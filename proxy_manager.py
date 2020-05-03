from bs4 import BeautifulSoup
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
import requests
import threading
import queue
import atexit

class ProxyManager:
    def __init__(self):
        self.proxy_stack = []
        self.psm_queue = queue.Queue()
        t = threading.Thread(target=self.proxy_stack_manager, daemon=True)
        t.start()

    def _stop_psm(self):
        self.psm_queue.put("stop")

    def request_new_proxy(self):
        while not self.proxy_stack:
            pass
        
        proxy = self.proxy_stack.pop(0) # get a new proxy off the stack
        self.psm_queue.put(None) # let the psm know that the stack may need to be refilled
        return proxy

    def proxy_stack_manager(self):
        while True:
            sig = self.psm_queue.get()
            if sig=="stop":
                return
            if len(self.proxy_stack) < 3:
                #print("[debug:psm] filling proxy stack")
                self.fill_proxy_stack()

    def fill_proxy_stack(self):
        working_proxies = []
        tasks = []
        with ThreadPoolExecutor(max_workers=64) as executor:
            for ip in self.get_proxy_list():
                tasks.append(executor.submit(self.test_proxy, ip))
            for task in as_completed(tasks):
                ip, result = task.result()
                if result:
                    working_proxies.append(ip)
        self.proxy_stack = self.proxy_stack+working_proxies

    def test_proxy(self, ip):
        try:
            r = requests.get("https://api.ipify.org",
                            proxies={"http": ip, "https": ip}, timeout=2)
            return ip, True
        except KeyboardInterrupt:
            quit()
        except Exception as e:
            return ip, False

    def get_proxy_list(require_https=True, verbose=False):
        r = requests.get("https://www.sslproxies.org/")
        soup = BeautifulSoup(r.text, "html.parser")

        proxies = []

        for row in soup.find(id="proxylisttable").find_all("tr"):
            row_data = list(map(lambda td: td.get_text(), row.find_all("td")))
            if not row_data:
                continue
            ip, port, code, country, anon, google, https, last_checked = row_data

            if https == "yes" and require_https:
                proxies.append(ip+":"+port)

        return proxies
