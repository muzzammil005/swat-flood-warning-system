"""Swat Flood Early-Warning System backend package.

The package root intentionally imports nothing — the application is assembled
from the subpackages under :mod:`backend.src` by the delivery layer
(FastAPI/WSGI entrypoints). Keeping this file empty avoids circular import
hazards when both the test runner and the Docker entrypoint try to import
``backend`` before all sub-modules are on ``sys.path``.
"""

__version__ = "0.1.0"
