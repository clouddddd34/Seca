# Report scheduler

Two independent API candidates are shown in `app.py`; a deployment would choose one.
The required behavior is one queued report job per request identifier, even when a
client retries from two tabs. Within this example, one process and one asyncio event
loop share a Scheduler instance; there is no database or cross-process coordination.
`write_job` stands in for an asynchronous operation. No external I/O takes place.

The existing check calls each API twice sequentially and observes one queue entry.
That is the only test result supplied; no overlapping-call execution is supplied.
