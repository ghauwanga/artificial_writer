"""Sample article inputs shared across the test suite.

Plain constants rather than fixtures: they are inert data, and importing them
directly (``from tests.samples import SAMPLE_TEXT``) keeps ``conftest.py`` for
fixtures alone.
"""

from __future__ import annotations

SAMPLE_HTML = """
<html>
  <head><title>The Future of Solar Power</title></head>
  <body>
    <nav>home about contact</nav>
    <p>Solar power is growing rapidly across the world. Costs have fallen dramatically.</p>
    <p>Engineers improve panel efficiency every single year. Storage remains a key challenge.</p>
    <p>Governments now offer incentives. Adoption is accelerating in many countries.</p>
    <script>console.log("ignore me");</script>
    <footer>copyright 2026</footer>
  </body>
</html>
"""

SAMPLE_TEXT = (
    "Solar power is growing rapidly across the world. Costs have fallen dramatically. "
    "Engineers are improving panel efficiency every single year. Storage remains a key challenge. "
    "Governments now offer incentives. Adoption is accelerating in many countries. "
    "Researchers continue to study new materials for cheaper cells."
)
