import subprocess
import sys
from pathlib import Path
result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'assessment', '-p', 'test_security.py', '-v'], capture_output=True, text=True)
Path('assessment/after.txt').write_text(result.stdout + result.stderr + '\nExit status: ' + str(result.returncode) + '\n', encoding='utf-8')
print(result.stdout + result.stderr)
print('Exit status:', result.returncode)
sys.exit(result.returncode)
