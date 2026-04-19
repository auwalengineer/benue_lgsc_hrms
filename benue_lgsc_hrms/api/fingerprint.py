"""
FILE    : <your_app>/api/fingerprint.py
PURPOSE : Whitelisted endpoint called from the Employee form's
          Capture Fingerprint modal.  Upserts a Fingerprint
          record linked to the employee.

Assumed Fingerprint DocType fields
───────────────────────────────────
  employee        Link → Employee   (reqd, unique index recommended)
  finger_1_data   Long Text         base64url PNG sample
  finger_1_format Int               Fingerprint.SampleFormat value
  finger_2_data   Long Text         optional second finger
  finger_2_format Int               optional
  device_uid      Data              reader UID
  captured_at     Datetime          auto-set
  captured_by     Data              auto-set (logged-in user)
  capture_status  Data              human-readable summary

HOW TO EXPOSE THIS FILE
───────────────────────
In <your_app>/hooks.py make sure you have:
    # (no extra entry needed — Frappe whitelists via decorator)

Then call it from the client script as:
    method: "<your_app>.api.fingerprint.save_fingerprint"
"""

import frappe
from frappe import _
from frappe.utils import now_datetime
import base64, binascii


# ── Constants ─────────────────────────────────────────────────
VALID_FORMATS = {1: "Raw", 2: "Intermediate", 3: "Compressed", 5: "PngImage"}
PNG_MAGIC     = b"\x89PNG\r\n\x1a\n"


# ── Helpers ───────────────────────────────────────────────────

def _b64url_to_standard(b64url: str) -> str:
    """Convert base64-URL encoding to standard base64."""
    s = b64url.replace("-", "+").replace("_", "/")
    pad = (4 - len(s) % 4) % 4
    return s + "=" * pad


def _validate_sample(label: str, b64url: str, fmt: int) -> int:
    """
    Validate a single fingerprint sample.
    Returns the decoded byte-length on success; raises on failure.
    """
    if not b64url or not b64url.strip():
        frappe.throw(_(f"<b>{label}</b>: sample data is empty."))

    if fmt not in VALID_FORMATS:
        frappe.throw(_(
            f"<b>{label}</b>: unknown format code <code>{fmt}</code>. "
            f"Expected one of {list(VALID_FORMATS.keys())}."
        ))

    try:
        decoded = base64.b64decode(_b64url_to_standard(b64url))
    except (binascii.Error, ValueError) as exc:
        frappe.throw(_(f"<b>{label}</b>: invalid base64 data ({exc}). Re-capture."))

    # PNG magic-byte check for PngImage format
    if fmt == 5 and decoded[:8] != PNG_MAGIC:
        frappe.throw(_(
            f"<b>{label}</b>: declared as PngImage but PNG header not found. "
            "Re-capture and try again."
        ))

    return len(decoded)


# ── Public whitelisted endpoint ───────────────────────────────

@frappe.whitelist()
def save_fingerprint(
    employee      : str,
    finger_1_data : str,
    finger_1_format: int = 5,
    finger_2_data : str = "",
    finger_2_format: int = None,
    device_uid    : str = ""
) -> dict:
    """
    Upserts a Fingerprint record for the given employee.

    Returns a dict with:
        name      – Fingerprint document name
        employee  – employee ID
        fingers   – number of fingers stored (1 or 2)
        status    – human-readable capture_status string
    """

    # ── 1. Permission gate ────────────────────────────────────
    # Tighten this list to match your org's roles
    allowed_roles = {"System Manager", "HR Manager", "HR User"}
    if not (allowed_roles & set(frappe.get_roles())):
        frappe.throw(_("You do not have permission to save fingerprint data."),
                     frappe.PermissionError)

    # ── 2. Employee must exist ────────────────────────────────
    if not frappe.db.exists("Employee", employee):
        frappe.throw(_(f"Employee <b>{employee}</b> not found."))

    # ── 3. Validate finger 1 (mandatory) ─────────────────────
    fmt1 = int(finger_1_format or 5)
    size1 = _validate_sample("Finger 1", finger_1_data, fmt1)
    frappe.logger().info(
        f"[FP] Finger 1 OK  employee={employee} "
        f"format={VALID_FORMATS[fmt1]} bytes={size1}"
    )

    # ── 4. Validate finger 2 (optional) ──────────────────────
    fmt2 = None
    size2 = 0
    if finger_2_data and finger_2_data.strip():
        fmt2  = int(finger_2_format or 5)
        size2 = _validate_sample("Finger 2", finger_2_data, fmt2)
        frappe.logger().info(
            f"[FP] Finger 2 OK  employee={employee} "
            f"format={VALID_FORMATS[fmt2]} bytes={size2}"
        )

    # ── 5. Upsert logic ───────────────────────────────────────
    existing_name = frappe.db.exists(
        "Fingerprint",
        {"employee": employee, "docstatus": ["!=", 2]}   # not cancelled
    )

    if existing_name:
        doc = frappe.get_doc("Fingerprint", existing_name)
        action = "updated"
    else:
        doc = frappe.new_doc("Fingerprint")
        doc.employee = employee
        action = "created"

    # ── 6. Populate fields ────────────────────────────────────
    doc.finger_1_data   = finger_1_data.strip()
    doc.finger_1_format = fmt1
    doc.finger_2_data   = finger_2_data.strip() if finger_2_data else ""
    doc.finger_2_format = fmt2
    doc.device_uid      = (device_uid or "").strip()
    doc.captured_at     = now_datetime()
    doc.captured_by     = frappe.session.user

    fingers_count = 1 + (1 if finger_2_data and finger_2_data.strip() else 0)
    doc.capture_status  = (
        f"{fingers_count} finger(s) {action} via device "
        f"'{doc.device_uid or 'unknown'}' at {doc.captured_at} "
        f"by {doc.captured_by}"
    )

    # ── 7. Save ───────────────────────────────────────────────
    doc.save(ignore_permissions=False)
    frappe.db.commit()

    frappe.logger().info(
        f"[FP] Fingerprint record {action}: {doc.name}  "
        f"employee={employee}  fingers={fingers_count}"
    )

    return {
        "name"    : doc.name,
        "employee": doc.employee,
        "fingers" : fingers_count,
        "status"  : doc.capture_status,
        "action"  : action
    }
