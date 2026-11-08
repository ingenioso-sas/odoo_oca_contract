Unifies auto-validation (`invoicing_mode` per contract) and invoice
notification by one or more channels.

`notification_channel_ids` replaces the old `email` / `whatsapp` / `both`
mode. Selecting email and WhatsApp sends through both channels; the channel
list is ordered and can be extended by glue modules. `notification_template_ids`
allows per-contract template overrides by channel and purpose.

The base driver only sends email. A glue module can override
`contract.notification.driver` to delegate every channel to a channel
platform. The direct statement link is provided by the
`_get_notification_statement_url()` hook, so templates do not depend on string
replacement.

Overdue invoices are only reported, never merged (no debt consolidation).
