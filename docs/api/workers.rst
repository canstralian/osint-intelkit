Workers
=======

Background workers for OSINT collection and enrichment.

Collector Worker
----------------

Passive OSINT collection from public sources (crt.sh, etc.)

.. automodule:: app.workers.collector
   :members:
   :undoc-members:
   :show-inheritance:

VirusTotal Enricher
-------------------

VirusTotal enrichment worker with rate limiting and caching.

.. automodule:: app.workers.vt_enricher
   :members:
   :undoc-members:
   :show-inheritance:
