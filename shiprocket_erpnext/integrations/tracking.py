import frappe
from frappe.utils import now_datetime

from shiprocket_erpnext.integrations.shiprocket_client import ShiprocketClient


def sync_open_delivery_notes():
    settings = frappe.get_single("Shiprocket Settings")
    if not settings.enabled:
        return

    names = frappe.get_all(
        "Delivery Note",
        filters={"docstatus": 1, "shiprocket_shipment_id": ["is", "set"]},
        fields=["name", "shiprocket_tracking_status"],
        limit_page_length=100,
    )

    for row in names:
        if (row.shiprocket_tracking_status or "").lower() == "delivered":
            continue
        try:
            sync_delivery_note_tracking(row.name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Shiprocket Tracking Sync Failed: {row.name}")


@frappe.whitelist()
def sync_delivery_note_tracking(delivery_note_name):
    settings = frappe.get_single("Shiprocket Settings")
    if not settings.enabled:
        frappe.throw("Shiprocket integration is disabled.")

    doc = frappe.get_doc("Delivery Note", delivery_note_name)
    if not doc.get("shiprocket_shipment_id") and not doc.get("shiprocket_awb_code"):
        frappe.throw("Delivery Note does not have a Shiprocket shipment id or AWB.")

    client = ShiprocketClient(settings)
    if doc.get("shiprocket_awb_code"):
        result = client.track_by_awb(doc.shiprocket_awb_code)
    else:
        result = client.track_by_shipment(doc.shiprocket_shipment_id)

    updates = extract_tracking_updates(result)
    updates["shiprocket_last_sync"] = now_datetime()
    updates["shiprocket_error"] = None

    frappe.db.set_value("Delivery Note", doc.name, updates, update_modified=False)
    return updates


def extract_tracking_updates(result):
    tracking = first_tracking_record(result)
    shipment_track = first_item(tracking.get("shipment_track")) if isinstance(tracking, dict) else {}
    shipment_activity = first_item(tracking.get("shipment_track_activities")) if isinstance(tracking, dict) else {}

    awb_code = pick([tracking, shipment_track], ["awb_code", "awb", "awb_no"])
    courier_name = pick([tracking, shipment_track], ["courier_name", "courier_company_name", "courier"])
    status = pick(
        [tracking, shipment_track, shipment_activity],
        ["current_status", "shipment_status", "status", "activity"],
    )
    tracking_url = pick([tracking, shipment_track], ["track_url", "tracking_url", "track_link"])

    updates = {}
    if awb_code:
        updates["shiprocket_awb_code"] = awb_code
    if courier_name:
        updates["shiprocket_courier_name"] = courier_name
    if status:
        updates["shiprocket_tracking_status"] = status
    if tracking_url:
        updates["shiprocket_tracking_url"] = tracking_url
    return updates


def first_tracking_record(result):
    if isinstance(result, dict):
        for key in ("tracking_data", "shipment_status", "payload", "data", "response"):
            value = result.get(key)
            if isinstance(value, dict):
                return value
            if isinstance(value, list) and value:
                return value[0]
        return result
    if isinstance(result, list) and result:
        return result[0]
    return {}


def first_item(value):
    if isinstance(value, list) and value:
        return value[0]
    if isinstance(value, dict):
        return value
    return {}


def pick(sources, keys):
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in keys:
            value = source.get(key)
            if value:
                return value
    return None
