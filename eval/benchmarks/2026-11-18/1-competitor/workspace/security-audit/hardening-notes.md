- app/app.py:41: Require a parsed Bearer scheme if evolving the fixture; bare known tokens currently work but still require the same credential.

- app/run.py:5 and app/app.py:38: Add sanitized authentication/authorization event logging before any production adaptation; no alerts or access logging are configured.

- app/requirements.txt:1: Lock transitive versions with hashes for reproducibility; do not infer dependency safety from direct pins.

- app/app.py:35: In-memory orders have no durability or storage quota. len()+1 IDs are not a durable concurrent allocator; no concurrent harm was demonstrated or stress tested.
