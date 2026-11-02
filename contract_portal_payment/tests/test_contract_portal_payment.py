# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta

from odoo import fields

from odoo.addons.contract.tests.test_contract import TestContractBase


class TestContractPortalPayment(TestContractBase):
    def test_pending_invoices_helper(self):
        line = self.contract.contract_line_ids[:1]
        line.write(
            {
                "date_start": fields.Date.today() - timedelta(days=30),
                "recurring_next_date": fields.Date.today(),
                "recurring_rule_type": "monthly",
                "recurring_interval": 1,
            }
        )
        invoices = self.contract.recurring_create_invoice()
        self.assertTrue(invoices)
        # Draft invoices are not pending
        self.assertEqual(self.contract._get_pending_invoices().ids, [])
        invoices.action_post()
        pending = self.contract._get_pending_invoices()
        self.assertIn(invoices[0].id, pending.ids)
        self.assertGreater(self.contract.pending_invoices_total, 0)
