#!/usr/bin/env python3

import sys
import subprocess

def test_frotz():
    try:
        print("Starting dfrotz process...")
        
        # Run dfrotz directly
        process = subprocess.run(
            ['/opt/homebrew/bin/dfrotz', '905.z5'],
            input='look\ninventory\nquit\n',
            capture_output=True,
            text=True
        )
        
        print("Output:")
        print("-" * 40)
        print(process.stdout)
        print("-" * 40)
        
        if process.stderr:
            print("Errors:")
            print("-" * 40)
            print(process.stderr)
            print("-" * 40)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_frotz()
    sys.exit(0 if success else 1) 