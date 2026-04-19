import frappe
from frappe import _

@frappe.whitelist()
def verify_nin(employee, nin, method="VerifyMe"):
    emp = frappe.get_doc("Employee", employee)
    
    try:
        if method == "VerifyMe":
            result = verify_with_verifyme(nin)
        else:
            result = verify_with_nimc_official(nin)   # placeholder for now

        if result.get("success"):
            # Update Employee fields
            #emp.nin_verified = 1
            emp.custom_verfication_status = "Verified"
            emp.custom_verification_date = frappe.utils.now_datetime()
            emp.custom_last_verification_attempt = frappe.utils.now_datetime()
            
            # Name confirmation & matching
            provided_first = (emp.first_name or "").strip().upper()
            provided_last = (emp.last_name or "").strip().upper()
            provided_middle = (emp.middle_name or "").strip().upper()
            
            api_first = (result.get("first_name") or "").strip().upper()
            api_last = (result.get("last_name") or "").strip().upper()
            api_middle = (result.get("middle_name") or "").strip().upper()
            
            if provided_first == api_first and provided_last == api_last:
                match_status = "Full Match"
            elif provided_first == api_first or provided_last == api_last:
                match_status = "Partial Match"
            else:
                match_status = "Mismatch"
            
            emp.custom_name_match_status = match_status
            emp.custom_verification_remarks = f"Verified via {method}. Name: {match_status}"
            
            # Auto update Date of Birth if available
            if result.get("date_of_birth"):
                emp.date_of_birth = result.get("date_of_birth")
            
            # Auto fill passport photo if returned (base64 or URL)
            if result.get("photo"):
                # You can handle base64 image saving here if needed
                pass

            emp.save(ignore_permissions=True)
            frappe.db.commit()
            
            return {"success": True, "message": "Verification successful"}
        else:
            emp.custom_verfication_status = "Failed"
            emp.custom_last_verification_attempt = frappe.utils.now_datetime()
            emp.custom_verification_remarks = result.get("message", "Verification failed")
            emp.save(ignore_permissions=True)
            frappe.db.commit()
            return {"success": False, "message": result.get("message")}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "NIN Verification Error")
        return {"success": False, "message": str(e)}

# ================== VERIFYME IMPLEMENTATION ==================
def verify_with_verifyme(nin):
    # TODO: Put your VerifyMe API Key here
    api_key = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICIzaVgtaEFrS3RmNUlsYWhRcElrNWwwbFBRVlNmVnpBdG9WVWQ4UXZ1OHJFIn0.eyJleHAiOjE3NzQzMjI4MDgsImlhdCI6MTc3NDMxNTYwOCwianRpIjoiZGRmZmQ4MWItNzJjNi00ODMwLWIwZjktMGVhNDI5OGVlNzI5IiwiaXNzIjoiaHR0cHM6Ly9hdXRoLnFvcmVpZC5jb20vYXV0aC9yZWFsbXMvcW9yZWlkIiwiYXVkIjpbInFvcmVpZGFwaSIsImFjY291bnQiXSwic3ViIjoiMTg4YjBlNmUtZjNjNS00ZjA0LThhNjYtOTE0NjljZDQzZTc5IiwidHlwIjoiQmVhcmVyIiwiYXpwIjoiTVhKMzZJN1VaOVNaVEFBVVFYUEQiLCJhY3IiOiIxIiwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iLCJkZWZhdWx0LXJvbGVzLXFvcmVpZCJdfSwicmVzb3VyY2VfYWNjZXNzIjp7InFvcmVpZGFwaSI6eyJyb2xlcyI6WyJ2ZXJpZnlfdmlydHVhbF9uaW5fc3ViIl19LCJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6InByb2ZpbGUgZW1haWwiLCJlbnZpcm9ubWVudCI6InNhbmRib3giLCJjbGllbnRIb3N0IjoiMzQuMjQ1LjIwLjI3IiwiY2xpZW50SWQiOiJNWEozNkk3VVo5U1pUQUFVUVhQRCIsIm9yZ2FuaXNhdGlvbklkIjoxNzMxMTEsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwicHJlZmVycmVkX3VzZXJuYW1lIjoic2VydmljZS1hY2NvdW50LW14ajM2aTd1ejlzenRhYXVxeHBkIiwiYXBwbGljYXRpb25JZCI6MjgxMjcsImNsaWVudEFkZHJlc3MiOiIzNC4yNDUuMjAuMjcifQ.UvBW5F7gzlaEdqSI1VxJggqOmNbD5TjRlOZxhTq3xfShnSGvyBWzympULEZb8KPqF5i6q1GjW3lUsN4ipfJBIvvZHJX4AbX-GyrzNLVKSwdPeG57Q9zAgSZwbOFmyxiTOqxXRpq50yKUY6WWib50XzrBi1mHwPDywRmlw45PAt3TiJcmDgJfwUNLxVBxZbBixRloCXt8Xy9vM-p0eOH3Ziut2N0yGMVu4iA-J6ABVHrxCcS-IIgL4tQYqRhNJmzR3momIKHUdpwBrzEj5axhCAfS2CG-xPwlh8RbIgWfRPYEXmRJRWGUwVenho1tZNT4ymu8OpPG8_eR-n1cyIRC5w"    
    # Example using VerifyMe endpoint (adjust according to their latest docs)
    # You will need to use requests library
    import requests
    
    url = f"https://vapi.verifyme.ng/v1/verifications/identities/nin/{nin}"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    response = requests.post(url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "success" or data.get("success"):
            return {
                "success": True,
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "middle_name": data.get("middle_name"),
                "date_of_birth": data.get("date_of_birth"),
                "photo": data.get("photo")   # if available
            }
    
    return {"success": False, "message": response.text or "VerifyMe API failed"}

# ================== NIMC OFFICIAL PLACEHOLDER ==================
def verify_with_nimc_official(nin):
    # This will be filled once you get access to NINAuth API
    # For now it returns dummy for testing
    return {
        "success": True,
        "first_name": "Test",
        "last_name": "Employee",
        "middle_name": "",
        "date_of_birth": "1990-01-01"
    }