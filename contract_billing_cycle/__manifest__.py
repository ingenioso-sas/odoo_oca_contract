# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Contract Billing Cycle",
    "summary": "Billing anchor day, first-period proration and free trial periods",
    "version": "19.0.1.0.1",
    "category": "Contract Management",
    "license": "AGPL-3",
    "author": "PayOnline Ing",
    "website": "https://www.odoo.com",
    "depends": [
        "contract_invoice_discount",
        "contract_variable_qty_prorated",
    ],
    "data": [
        "views/contract_views.xml",
        "views/contract_line_views.xml",
        "views/contract_template_views.xml",
    ],
    "installable": True,
    "application": False,
}
