import hashlib
import frappe

def compute_hash(base64_data):
    """Compute SHA256 hash of base64 fingerprint data."""
    if not base64_data:
        return None
    return hashlib.sha256(base64_data.encode("utf-8")).hexdigest()

def validate_unique_fingerprint(doc, method):
    # Compute hashes
    doc.finger_1_hash = compute_hash(doc.finger_1_data)
    doc.finger_2_hash = compute_hash(doc.finger_2_data)

    # Check uniqueness
    if doc.finger_1_hash:
        existing = frappe.get_all(
            "Fingerprint",
            filters={"finger_1_hash": doc.finger_1_hash, "name": ("!=", doc.name)},
            fields=["name", "employee"]
        )
        if existing:
            frappe.throw(f"Finger 1 already exists for Employee {existing[0]['employee']} (Doc {existing[0]['name']})")

    if doc.finger_2_hash:
        existing = frappe.get_all(
            "Fingerprint",
            filters={"finger_2_hash": doc.finger_2_hash, "name": ("!=", doc.name)},
            fields=["name", "employee"]
        )
        if existing:
            frappe.throw(f"Finger 2 already exists for Employee {existing[0]['employee']} (Doc {existing[0]['name']})")
