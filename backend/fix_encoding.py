with open('main.py', 'rb') as f:
    data = f.read()

# Find and fix problematic bytes
clean = data.replace(b'\xe2\x80\x94', b'--').replace(b'\xe2\x80\x99', b"'").replace(b'\xc2\xbb', b'>>').replace(b'\xc2\xab', b'<<')
clean = clean.replace(b'\x1d', b' ')

with open('main.py', 'wb') as f:
    f.write(clean)
print(f'Cleaned, new length: {len(clean)}')