import requests

import frappe
from frappe import _


class ShiprocketError(frappe.ValidationError):
    pass


class ShiprocketClient:
    base_url = "https://apiv2.shiprocket.in/v1/external"

    def __init__(self, settings=None):
        self.settings = settings or frappe.get_single("Shiprocket Settings")
        self.token = None

    def create_order(self, payload):
        return self._request("POST", "/orders/create/adhoc", json=payload)

    def assign_awb(self, shipment_id):
        return self._request(
            "POST",
            "/courier/assign/awb",
            json={"shipment_id": shipment_id},
        )

    def request_pickup(self, shipment_id):
        return self._request(
            "POST",
            "/courier/generate/pickup",
            json={"shipment_id": [shipment_id]},
        )

    def track_by_awb(self, awb_code):
        return self._request("GET", f"/courier/track/awb/{awb_code}")

    def track_by_shipment(self, shipment_id):
        return self._request("GET", f"/courier/track/shipment/{shipment_id}")

    def _request(self, method, path, **kwargs):
        headers = kwargs.pop("headers", {})
        if path != "/auth/login":
            headers["Authorization"] = f"Bearer {self._get_token()}"

        response = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            timeout=30,
            **kwargs,
        )

        try:
            data = response.json()
        except ValueError:
            data = {"message": response.text}

        if self.settings.debug:
            frappe.logger("shiprocket_erpnext").info(
                {
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "response": data,
                }
            )

        if response.status_code >= 400:
            message = data.get("message") or data.get("error") or response.text
            raise ShiprocketError(_("Shiprocket API error: {0}").format(message))

        return data

    def _get_token(self):
        cached = frappe.cache().get_value("shiprocket_erpnext:auth_token")
        if cached:
            return cached

        password = self.settings.get_password("api_password")
        if not self.settings.api_email or not password:
            raise ShiprocketError(_("Shiprocket API Email and Password are required."))

        data = self._request(
            "POST",
            "/auth/login",
            json={"email": self.settings.api_email, "password": password},
        )
        token = data.get("token")
        if not token:
            raise ShiprocketError(_("Shiprocket did not return an auth token."))

        frappe.cache().set_value("shiprocket_erpnext:auth_token", token, expires_in_sec=9 * 60 * 60)
        return token

