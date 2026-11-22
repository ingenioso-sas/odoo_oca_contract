# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Contract Lifecycle",
    "summary": "Pause, resume and finish contracts with credit notes",
    "version": "19.0.1.0.0",
    "category": "Contract Management",
    "website": "https://github.com/OCA/contract",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        "contract_line_successor",
        "contract_termination",
        "contract_refund_on_stop",
        "contract_invoice_discount",
        "contract_referral",
    ],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/contract_lifecycle_security.xml",
        "data/contract_terminate_reason_data.xml",
        "data/contract_pause_reason_data.xml",
        "views/contract_pause_reason_views.xml",
        "views/contract_pause_views.xml",
        "views/contract_views.xml",
        "views/contract_terminate_views.xml",
        "views/contract_portal_templates.xml",
        "wizards/contract_pause_wizard.xml",
        "wizards/contract_resume_wizard.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
