import frappe
from frappe.utils import now_datetime

from shiprocket_erpnext.integrations.tracking import extract_tracking_updates, first_tracking_record, pick


@frappe.whitelist(allow_guest=True)
def shipment_status():
    settings = frappe.get_single("Shiprocket Settings")
    if not settings.enabled:
        frappe.local.response["http_status_code"] = 403
        return {"ok": False, "message": "Shiprocket integration is disabled."}

    if not is_valid_webhook_secret(settings):
        frappe.local.response["http_status_code"] = 401
        return {"ok": False, "message": "Invalid webhook secret."}

    payload = get_payload()
    if settings.debug:
        frappe.logger("shiprocket_erpnext").info({"webhook_payload": payload})

    delivery_note_name = find_delivery_note(payload)
    if not delivery_note_name:
        frappe.local.response["http_status_code"] = 404
        return {"ok": False, "message": "No matching Delivery Note found."}

    updates = extract_tracking_updates(payload)
    identifiers = extract_identifiers(payload)

    if identifiers.get("awb_code") and not updates.get("shiprocket_awb_code"):
        updates["shiprocket_awb_code"] = identifiers["awb_code"]
    if identifiers.get("shipment_id"):
        updates["shiprocket_shipment_id"] = identifiers["shipment_id"]
    if identifiers.get("order_id"):
        updates["shiprocket_order_id"] = identifiers["order_id"]

    updates["shiprocket_last_webhook_at"] = now_datetime()
    updates["shiprocket_last_sync"] = now_datetime()
    updates["shiprocket_error"] = None

    frappe.db.set_value("Delivery Note", delivery_note_name, updates, update_modified=False)
    return {"ok": True, "delivery_note": delivery_note_name, "updates": updates}


def get_payload():
    if frappe.request and frappe.request.is_json:
        return frappe.request.get_json(silent=True) or {}

    form_dict = frappe.local.form_dict or {}
    payload = dict(form_dict)
    payload.pop("cmd", None)
    return payload


def is_valid_webhook_secret(settings):
    expected = settings.get_password("webhook_secret")
    if not expected:
        return True

    provided = (
        frappe.get_request_header("X-Shiprocket-Webhook-Secret")
        or frappe.get_request_header("X-Webhook-Secret")
        or get_bearer_token()
        or (frappe.local.form_dict or {}).get("secret")
    )
    return provided == expected


def get_bearer_token():
    authorization = frappe.get_request_header("Authorization") or ""
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def find_delivery_note(payload):
    identifiers = extract_identifiers(payload)

    lookups = [
        ("shiprocket_awb_code", identifiers.get("awb_code")),
        ("shiprocket_shipment_id", identifiers.get("shipment_id")),
        ("shiprocket_order_id", identifiers.get("order_id")),
        ("name", identifiers.get("erpnext_delivery_note")),
    ]

    for fieldname, value in lookups:
        if not value:
            continue
        name = frappe.db.get_value("Delivery Note", {fieldname: value, "docstatus": 1}, "name")
        if name:
            return name

    return None


def extract_identifiers(payload):
    tracking = first_tracking_record(payload)
    shipment_track = {}
    if isinstance(tracking, dict):
        shipment_track = tracking.get("shipment_track")
        if isinstance(shipment_track, list):
            shipment_track = shipment_track[0] if shipment_track else {}
        if not isinstance(shipment_track, dict):
            shipment_track = {}

    sources = [payload, tracking, shipment_track]
    return {
        "awb_code": pick(sources, ["awb_code", "awb", "awb_no"]) or find_value(payload, ["awb_code", "awb", "awb_no"]),
        "shipment_id": pick(sources, ["shipment_id", "shiprocket_shipment_id"])
        or find_value(payload, ["shipment_id", "shiprocket_shipment_id"]),
        "order_id": pick(sources, ["order_id", "shiprocket_order_id", "channel_order_id"])
        or find_value(payload, ["order_id", "shiprocket_order_id", "channel_order_id"]),
        "erpnext_delivery_note": pick(sources, ["erpnext_delivery_note", "delivery_note", "delivery_note_name"])
        or find_value(payload, ["erpnext_delivery_note", "delivery_note", "delivery_note_name"]),
    }


def find_value(value, keys):
    if isinstance(value, dict):
        for key in keys:
            if value.get(key):
                return value.get(key)
        for child in value.values():
            found = find_value(child, keys)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_value(child, keys)
            if found:
                return found
    return None
