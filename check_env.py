import os
import re

# Check for config drift between environments
print('=== Environment Variable Usage ===')
for root, dirs, files in os.walk('backend'):
    if 'venv' in root or '__pycache__' in root or '.pytest_cache' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                    for match in re.finditer(r'os\.getenv\([\'"]([\'"]+)', content):
                        print(f'{path}: {match.group(1)}')
                    for match in re.finditer(r'os\.environ\[[\'"]([\'"]+)', content):
                        print(f'{path}: {match.group(1)}')
            except:
                pass