app_name = "shiprocket_erpnext"
app_title = "Shiprocket ERPNext"
app_publisher = "Codex"
app_description = "Create Shiprocket orders from ERPNext Delivery Notes and sync tracking details."
app_email = "support@example.com"
app_license = "MIT"

after_install = "shiprocket_erpnext.install.after_install.execute"

doc_events = {
    "Delivery Note": {
        "on_submit": "shiprocket_erpnext.integrations.delivery_note.on_delivery_note_submit",
    }
}

scheduler_events = {
    "hourly": [
        "shiprocket_erpnext.integrations.tracking.sync_open_delivery_notes",
    ]
}

