#!/usr/bin/env python3
"""Simple test to see if packaged executable can write files."""

if __name__ == "__main__":
    import sys

    # Try to write a test file
    try:
        with open("/tmp/test_write.txt", "w") as f:
            f.write(f"Test from frozen={getattr(sys, 'frozen', False)}\n")
        print("SUCCESS: Wrote test file")
    except Exception as e:
        print(f"ERROR: {e}")

    # Try to write to stdout
    print("This is stdout")
    print(f"sys.executable: {sys.executable}", flush=True)
    print(f"Frozen: {getattr(sys, 'frozen', False)}", flush=True)
