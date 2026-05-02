import hashlib
import sys

# THIS IS THE SECRET SALT. It MUST EXACTLY MATCH the salt in backend/services/license_service.py
# Do NOT distribute this script or this salt to your customers!
SECRET_SALT = "TomeMaster-2026-BennettConsulting-Salt"

def generate_key_for_machine(machine_id: str) -> str:
    """
    Takes a customer's Machine ID and generates an Activation Key that will ONLY work on their specific machine.
    """
    # 1. Combine their Machine ID with your secret salt
    combined = f"{machine_id}::{SECRET_SALT}"
    
    # 2. Hash it to create a secure one-way cryptographic footprint
    full_hash = hashlib.sha256(combined.encode()).hexdigest()
    
    # 3. Format it into a user-friendly product key format (e.g., TOME-A1B2-C3D4-E5F6)
    prefix = full_hash[:12].upper()
    product_key = f"TOME-{prefix[:4]}-{prefix[4:8]}-{prefix[8:]}"
    return product_key

if __name__ == "__main__":
    print("\n=============================================")
    print("   Tome-Master Offline License Key Generator ")
    print("=============================================\n")
    
    while True:
        machine_id = input("Enter the Customer's Machine ID (or type 'exit' to quit): ").strip()
        if machine_id.lower() == 'exit':
            break
        if not machine_id:
            continue
            
        activation_key = generate_key_for_machine(machine_id)
        print("\n---------------------------------------------")
        print(f"✅ Generated Activation Key: {activation_key}")
        print("---------------------------------------------\n")
        print("Copy/Paste the key above and email it back to the customer.\n")
