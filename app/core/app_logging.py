import logging


class MemoryHandler(logging.Handler):
    def __init__(self, capacity):
        super().__init__()
        self.capacity = capacity
        self.buffer = []

    def emit(self, record):
        self.buffer.append(self.format(record))
        if len(self.buffer) > self.capacity:
            self.buffer.pop(0)

    def get_logs(self):
        return self.buffer.copy()


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
memory_handler = MemoryHandler(capacity=1000)
memory_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(memory_handler)
