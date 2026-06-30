import frappe
from frappe.utils import cint, flt, get_datetime, now_datetime

from shiprocket_erpnext.integrations.shiprocket_client import ShiprocketClient, ShiprocketError


def on_delivery_note_submit(doc, method=None):
    settings = frappe.get_single("Shiprocket Settings")
    if not settings.enabled or not settings.create_on_delivery_note_submit:
        return

    try:
        create_shiprocket_order(doc.name)
    except Exception as exc:
        frappe.db.set_value("Delivery Note", doc.name, "shiprocket_error", str(exc), update_modified=False)
        frappe.log_error(frappe.get_traceback(), "Shiprocket Delivery Note Submit Failed")


@frappe.whitelist()
def create_shiprocket_order(delivery_note_name):
    settings = frappe.get_single("Shiprocket Settings")
    if not settings.enabled:
        frappe.throw("Shiprocket integration is disabled.")

    doc = frappe.get_doc("Delivery Note", delivery_note_name)
    if cint(doc.docstatus) != 1:
        frappe.throw("Shiprocket orders can only be created for submitted Delivery Notes.")

    if doc.get("shiprocket_order_id"):
        return {
            "order_id": doc.shiprocket_order_id,
            "shipment_id": doc.get("shiprocket_shipment_id"),
            "awb_code": doc.get("shiprocket_awb_code"),
            "message": "Shiprocket order already exists for this Delivery Note.",
        }

    client = ShiprocketClient(settings)
    payload = build_order_payload(doc, settings)
    result = client.create_order(payload)

    updates = extract_order_updates(result)
    updates["shiprocket_error"] = None
    updates["shiprocket_last_sync"] = now_datetime()

    frappe.db.set_value("Delivery Note", doc.name, updates, update_modified=False)

    shipment_id = updates.get("shiprocket_shipment_id")
    if shipment_id and settings.auto_assign_awb:
        assign_result = client.assign_awb(shipment_id)
        awb_updates = extract_awb_updates(assign_result)
        if awb_updates:
            frappe.db.set_value("Delivery Note", doc.name, awb_updates, update_modified=False)

        if settings.auto_request_pickup:
            client.request_pickup(shipment_id)

    return result


def build_order_payload(doc, settings):
    customer = frappe.get_doc("Customer", doc.customer)
    billing_address = get_address(doc.get("customer_address") or doc.get("shipping_address_name"))
    shipping_address = get_address(doc.get("shipping_address_name") or doc.get("customer_address"))
    contact = get_contact(doc.get("contact_person"))

    billing = address_payload(billing_address, customer, contact, settings)
    shipping = address_payload(shipping_address, customer, contact, settings)
    order_items = [item_payload(row) for row in doc.items if flt(row.qty) > 0]

    if not order_items:
        raise ShiprocketError("Delivery Note must have at least one item with quantity.")

    return {
        "order_id": doc.name,
        "order_date": get_datetime(doc.posting_date).strftime("%Y-%m-%d"),
        "pickup_location": settings.pickup_location,
        "billing_customer_name": billing["first_name"],
        "billing_last_name": billing["last_name"],
        "billing_address": billing["address"],
        "billing_address_2": billing["address_2"],
        "billing_city": billing["city"],
        "billing_pincode": billing["pincode"],
        "billing_state": billing["state"],
        "billing_country": billing["country"],
        "billing_email": billing["email"],
        "billing_phone": billing["phone"],
        "shipping_is_billing": bool(
            shipping_address
            and billing_address
            and shipping_address.name == billing_address.name
        ),
        "shipping_customer_name": shipping["first_name"],
        "shipping_last_name": shipping["last_name"],
        "shipping_address": shipping["address"],
        "shipping_address_2": shipping["address_2"],
        "shipping_city": shipping["city"],
        "shipping_pincode": shipping["pincode"],
        "shipping_state": shipping["state"],
        "shipping_country": shipping["country"],
        "shipping_email": shipping["email"],
        "shipping_phone": shipping["phone"],
        "order_items": order_items,
        "payment_method": settings.cod_payment_method or "Prepaid",
        "shipping_charges": flt(doc.get("total_taxes_and_charges")),
        "giftwrap_charges": 0,
        "transaction_charges": 0,
        "total_discount": flt(doc.get("discount_amount")),
        "sub_total": flt(doc.get("grand_total") or doc.get("rounded_total") or doc.get("net_total")),
        "length": positive_float(settings.default_length_cm, 10),
        "breadth": positive_float(settings.default_breadth_cm, 10),
        "height": positive_float(settings.default_height_cm, 10),
        "weight": positive_float(settings.default_weight_kg, 0.5),
    }


def item_payload(row):
    return {
        "name": row.item_name or row.item_code,
        "sku": row.item_code,
        "units": flt(row.qty),
        "selling_price": flt(row.rate),
        "discount": flt(row.get("discount_amount")),
        "tax": flt(row.get("tax_amount")),
        "hsn": row.get("gst_hsn_code") or row.get("item_tax_template") or "",
    }


def get_address(address_name):
    if address_name and frappe.db.exists("Address", address_name):
        return frappe.get_doc("Address", address_name)
    return None


def get_contact(contact_name):
    if contact_name and frappe.db.exists("Contact", contact_name):
        return frappe.get_doc("Contact", contact_name)
    return None


def address_payload(address, customer, contact, settings):
    full_name = customer.customer_name or customer.name
    first_name, last_name = split_name(full_name)

    email = (
        getattr(contact, "email_id", None)
        or getattr(address, "email_id", None)
        or settings.fallback_email
        or "no-reply@example.com"
    )
    phone = (
        getattr(contact, "mobile_no", None)
        or getattr(contact, "phone", None)
        or getattr(address, "phone", None)
        or settings.fallback_phone
        or "9999999999"
    )

    return {
        "first_name": first_name,
        "last_name": last_name,
        "address": getattr(address, "address_line1", None) or "Address not provided",
        "address_2": getattr(address, "address_line2", None) or "",
        "city": getattr(address, "city", None) or "NA",
        "pincode": getattr(address, "pincode", None) or "000000",
        "state": getattr(address, "state", None) or "NA",
        "country": getattr(address, "country", None) or "India",
        "email": email,
        "phone": phone,
    }


def split_name(name):
    parts = (name or "").strip().split(" ", 1)
    if not parts or not parts[0]:
        return "Customer", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def positive_float(value, fallback):
    value = flt(value)
    return value if value > 0 else fallback


def extract_order_updates(result):
    order_id = result.get("order_id") or result.get("channel_order_id")
    shipment_id = result.get("shipment_id")
    return {
        "shiprocket_order_id": order_id,
        "shiprocket_shipment_id": shipment_id,
        "shiprocket_tracking_status": result.get("status") or result.get("message"),
    }


def extract_awb_updates(result):
    response = result.get("response") if isinstance(result.get("response"), dict) else result
    awb_code = response.get("awb_code") or response.get("awb")
    courier_name = response.get("courier_name") or response.get("courier_company_id")

    updates = {}
    if awb_code:
        updates["shiprocket_awb_code"] = awb_code
    if courier_name:
        updates["shiprocket_courier_name"] = courier_name
    return updates
