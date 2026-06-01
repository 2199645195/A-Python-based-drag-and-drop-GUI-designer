import time, threading, random, math

class DataSource(threading.Thread):
    def __init__(self, data_binder):
        super().__init__(daemon=True)
        self.binder = data_binder
        self.running = True
    def run(self):
        t = 0
        while self.running:
            temp = 75 + 15 * math.sin(t * 0.5)
            self.binder.update_tag('temp_value', temp)
            time.sleep(0.5); t += 0.5
