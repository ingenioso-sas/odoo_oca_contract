# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Contract Invoice Period",
    "summary": "Store the billing period of invoices generated from contracts",
    "version": "19.0.1.0.1",
    "category": "Contract Management",
    "website": "https://github.com/OCA/contract",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["contract", "account"],
    "data": [
        "views/account_move_views.xml",
        "report/report_invoice.xml",
    ],
    "installable": True,
}
