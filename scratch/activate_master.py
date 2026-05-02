import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from services import license_service

machine_id = license_service.get_machine_fingerprint()
print(f"Machine ID: {machine_id}")

success = license_service.activate("APEX-DIRECTOR")
if success:
    print("Sovereign Gate Activated. Welcome, Director.")
else:
    print("Activation Failed.")
