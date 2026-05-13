import subprocess, sys

print("Fixing dashboard files...")

# Fix 1: Fix main.py inside container
fix_main = """
content = open('/app/api/main.py').read()
# Fix broken state_clause call
content = content.replace(
    "WHERE year_month = :ym {state_clause('state', 'state')}",
    "WHERE year_month = :ym"
)
content = content.replace(
    "WHERE year_month = :ym {state_clause}",
    "WHERE year_month = :ym"
)
open('/app/api/main.py', 'w').write(content)
print('main.py fixed')
"""

result = subprocess.run(
    ["docker", "exec", "sad_backend", "python3", "-c", fix_main],
    capture_output=True, text=True
)
print(result.stdout or result.stderr)

# Fix 2: Restart container
print("Restarting backend...")
subprocess.run(["docker", "restart", "sad_backend"], capture_output=True)
print("Done! Wait 10 seconds then try uploading again.")
input("Press Enter to exit...")
