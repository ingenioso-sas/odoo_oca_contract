Unifies auto-validation (`invoicing_mode` per contract) and adds
email/WhatsApp notification with portal payment link + overdue summary.
Overdue invoices are only reported, never merged (no debt consolidation).
WhatsApp provider is pluggable (`contract.whatsapp.driver`); without a
provider installed the message is logged and cron continues.
