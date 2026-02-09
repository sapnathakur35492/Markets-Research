from reports.utils import auto_format_content

test_text = """
MARKET OVERVIEW

**Key Highlights:**
- **Market Growth:** 35% CAGR
- *Global Impact:* High
- Innovative Solutions: Yes

1. Introduction
This is the beginning.

**Conclusion:**
This is the end.
"""

formatted = auto_format_content(test_text)
print(formatted)
