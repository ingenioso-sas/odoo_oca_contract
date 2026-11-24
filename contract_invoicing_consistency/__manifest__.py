# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Contract Invoicing Consistency",
    "summary": "Validate contract invoice dates and warn about mixed invoicing types",
    "version": "19.0.1.0.0",
    "category": "Contract Management",
    "license": "AGPL-3",
    "author": "PayOnline Ing",
    "website": "https://www.odoo.com",
    "depends": ["contract"],
    "data": [
        "views/contract_views.xml",
    ],
    "installable": True,
    "application": False,
}
