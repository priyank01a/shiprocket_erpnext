import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_delivery_note_fields()
    set_default_settings()


def create_delivery_note_fields():
    custom_fields = {
        "Delivery Note": [
            {
                "fieldname": "shiprocket_section",
                "fieldtype": "Section Break",
                "label": "Shiprocket",
                "insert_after": "terms",
                "collapsible": 1,
            },
            {
                "fieldname": "shiprocket_order_id",
                "fieldtype": "Data",
                "label": "Shiprocket Order ID",
                "insert_after": "shiprocket_section",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "shiprocket_shipment_id",
                "fieldtype": "Data",
                "label": "Shiprocket Shipment ID",
                "insert_after": "shiprocket_order_id",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "shiprocket_awb_code",
                "fieldtype": "Data",
                "label": "Shiprocket AWB Code",
                "insert_after": "shiprocket_shipment_id",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "shiprocket_column_break",
                "fieldtype": "Column Break",
                "insert_after": "shiprocket_awb_code",
            },
            {
                "fieldname": "shiprocket_courier_name",
                "fieldtype": "Data",
                "label": "Shiprocket Courier",
                "insert_after": "shiprocket_column_break",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "shiprocket_tracking_status",
                "fieldtype": "Data",
                "label": "Shiprocket Tracking Status",
                "insert_after": "shiprocket_courier_name",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "shiprocket_tracking_url",
                "fieldtype": "Data",
                "label": "Shiprocket Tracking URL",
                "insert_after": "shiprocket_tracking_status",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "shiprocket_last_sync",
                "fieldtype": "Datetime",
                "label": "Shiprocket Last Sync",
                "insert_after": "shiprocket_tracking_url",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "shiprocket_last_webhook_at",
                "fieldtype": "Datetime",
                "label": "Shiprocket Last Webhook At",
                "insert_after": "shiprocket_last_sync",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "shiprocket_error",
                "fieldtype": "Small Text",
                "label": "Shiprocket Error",
                "insert_after": "shiprocket_last_webhook_at",
                "read_only": 1,
                "no_copy": 1,
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)


def set_default_settings():
    defaults = {
        "enabled": 0,
        "create_on_delivery_note_submit": 1,
        "default_length_cm": 10,
        "default_breadth_cm": 10,
        "default_height_cm": 10,
        "default_weight_kg": 0.5,
    }
    for fieldname, value in defaults.items():
        frappe.db.set_single_value("Shiprocket Settings", fieldname, value)
