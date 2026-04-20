import frappe
from frappe import _

def validate_fingerprint(doc, method):
    """
    Ensure that FMD templates are unique across all employees.
    """
    for field in ["finger_1_fmd", "finger_2_fmd"]:
        fmd_value = getattr(doc, field, None)
        if fmd_value:
            exists = frappe.db.exists("Fingerprint", {
                field: fmd_value,
                "name": ["!=", doc.name]  # exclude current doc
            })
            if exists:
                frappe.throw(_("Fingerprint already exists in the system."))
