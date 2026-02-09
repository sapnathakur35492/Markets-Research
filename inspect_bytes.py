import os

def check_hidden_chars():
    path = "templates/reports/report_list.html"
    with open(path, 'rb') as f:
        content = f.read()
        print(f"--- Byte Inspection of {path} ---")
        # Look for non-ascii or specific control chars
        for i, byte in enumerate(content):
            if byte > 127 or byte < 9:
                print(f"Suspicious byte at {i}: {byte} ({hex(byte)})")
        
        # Also print the area around "report.title"
        try:
            str_content = content.decode('utf-8')
            idx = str_content.find("report.title")
            if idx != -1:
                snippet = str_content[idx-10:idx+20]
                print(f"\nSnippet around report.title: {repr(snippet)}")
        except Exception as e:
            print(f"Decoding error: {e}")

if __name__ == "__main__":
    check_hidden_chars()
