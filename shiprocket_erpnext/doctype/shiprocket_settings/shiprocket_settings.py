import frappe
from frappe.model.document import Document


class ShiprocketSettings(Document):
    def validate(self):
        if self.enabled and (not self.api_email or not self.get_password("api_password")):
            frappe.throw("Shiprocket API Email and Password are required when the integration is enabled.")

        if self.enabled and not self.pickup_location:
            frappe.throw("Pickup Location is required when Shiprocket integration is enabled.")

        if self.auto_assign_awb and not self.enabled:
            frappe.throw("Enable the integration before enabling Auto Assign AWB.")

        if self.auto_request_pickup and not self.auto_assign_awb:
            frappe.throw("Auto Request Pickup requires Auto Assign AWB.")
