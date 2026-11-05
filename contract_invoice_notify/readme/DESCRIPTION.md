Unifies auto-validation (`invoicing_mode` per contract) and adds
email/WhatsApp notification with portal payment link + overdue summary.
Overdue invoices are only reported, never merged (no debt consolidation).
The WhatsApp text comes from a configurable `mail.template` per contract
(`WhatsApp Template`, default provided); links are sent as absolute URLs.
WhatsApp provider is pluggable (`contract.whatsapp.driver`); without a
provider installed the message is logged and cron continues.
