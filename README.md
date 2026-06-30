# Shiprocket ERPNext Integration

Frappe/ERPNext app that creates Shiprocket orders from submitted Delivery Notes and syncs tracking details back to the Delivery Note.

## What it does

- Adds Shiprocket configuration in **Shiprocket Settings**.
- Adds Shiprocket tracking fields to **Delivery Note**.
- On Delivery Note submit, creates an adhoc Shiprocket order.
- Optionally assigns AWB and requests pickup after order creation.
- Receives Shiprocket shipment webhooks for live tracking updates.
- Periodically syncs tracking status, courier, AWB, and tracking URL back to ERPNext as a fallback.

## Install

Copy this app into your bench apps folder, then run:

```bash
bench get-app /path/to/shiprocket_erpnext
bench --site your-site.local install-app shiprocket_erpnext
bench --site your-site.local migrate
bench restart
```

## Configure

Open **Shiprocket Settings** in ERPNext and set:

- API Email
- API Password
- Pickup Location
- Default dimensions and weight
- Whether to create orders automatically on Delivery Note submit
- Whether to auto assign AWB
- Whether to auto request pickup
- Webhook Secret, optional but recommended

## Shiprocket webhook

Add this URL in Shiprocket's webhook settings:

```text
https://your-erpnext-site.com/api/method/shiprocket_erpnext.integrations.webhook.shipment_status?secret=YOUR_SECRET
```

If your webhook setup supports headers, you can send the same secret in `X-Shiprocket-Webhook-Secret`, `X-Webhook-Secret`, or `Authorization: Bearer YOUR_SECRET` instead of putting it in the URL.

The receiver updates the submitted Delivery Note matched by AWB, shipment id, Shiprocket order id, or Delivery Note name. It updates AWB, courier, tracking status, tracking URL, last sync time, and last webhook time.

## Delivery Note requirements

For best results, each Delivery Note should have:

- Customer
- Customer Address or Shipping Address
- Contact with email/mobile
- Item rows with item code, item name, quantity, and rate
- Grand total

The integration falls back to reasonable defaults when optional data is missing, but Shiprocket can reject orders if mandatory shipping data such as phone, pincode, or address is incomplete.

## Manual actions

From Python/Frappe console:

```python
from shiprocket_erpnext.integrations.delivery_note import create_shiprocket_order
create_shiprocket_order("DN-00001")

from shiprocket_erpnext.integrations.tracking import sync_delivery_note_tracking
sync_delivery_note_tracking("DN-00001")
```
