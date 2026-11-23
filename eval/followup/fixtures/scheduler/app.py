"""Small in-memory report scheduler; no HTTP, credentials, payments, or external I/O."""
import asyncio


class Scheduler:
    def __init__(self):
        self.jobs = {}
        self.queue = []
        self.lock = asyncio.Lock()

    async def write_job(self, request_id):
        await asyncio.sleep(0)
        self.queue.append(request_id)

    async def submit(self, request_id):
        if request_id in self.jobs:
            return self.jobs[request_id]
        await self.write_job(request_id)
        self.jobs[request_id] = 'queued'
        return self.jobs[request_id]

    async def guarded_submit(self, request_id):
        async with self.lock:
            if request_id in self.jobs:
                return self.jobs[request_id]
            await self.write_job(request_id)
            self.jobs[request_id] = 'queued'
            return self.jobs[request_id]
