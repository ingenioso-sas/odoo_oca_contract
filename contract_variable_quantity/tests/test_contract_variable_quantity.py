# Copyright 2016 Tecnativa - Pedro M. Baeza
# Copyright 2018 Tecnativa - Carlos Dauden
# Copyright 2018 ACSONE SA/NV
# Copyright 2024 Tecnativa - Carolina Fernandez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import exceptions
from odoo.tests import new_test_user, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestContractVariableQuantity(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test partner"})
        cls.product = cls.env["product.product"].create({"name": "Test product"})
        cls.contract = cls.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": cls.partner.id,
                "pricelist_id": cls.partner.property_product_pricelist.id,
            }
        )
        cls.formula = cls.env["contract.line.qty.formula"].create(
            {
                "name": "Test formula",
                # For testing each of the possible variables
                "code": 'env["res.users"]\n'
                'context.get("lang")\n'
                "user.id\n"
                "line.qty_type\n"
                "contract.id\n"
                "quantity\n"
                "period_first_date\n"
                "period_last_date\n"
                "invoice_date\n"
                "result = 12",
            }
        )
        cls.contract_line = cls.env["contract.line"].create(
            {
                "contract_id": cls.contract.id,
                "product_id": cls.product.id,
                "name": "Test",
                "qty_type": "variable",
                "qty_formula_id": cls.formula.id,
                "quantity": 1,
                "uom_id": cls.product.uom_id.id,
                "price_unit": 100,
                "discount": 50,
                "recurring_rule_type": "monthly",
                "recurring_interval": 1,
                "date_start": "2016-02-15",
                "recurring_next_date": "2016-02-29",
            }
        )

    def test_check_invalid_code(self):
        with self.assertRaises(exceptions.ValidationError):
            self.formula.code = "sdsds"

    def test_check_no_return_value(self):
        with self.assertRaises(exceptions.ValidationError):
            self.formula.code = "user.id"

    def test_check_variable_quantity(self):
        self.contract.recurring_create_invoice()
        invoice = self.contract._get_related_invoices()
        self.assertEqual(invoice.invoice_line_ids[0].quantity, 12)

    def test_check_skip_zero_qty(self):
        self.formula.code = "result=0"
        self.contract.skip_zero_qty = True
        invoice = self.contract.recurring_create_invoice()
        self.assertFalse(invoice.invoice_line_ids)
        self.contract.skip_zero_qty = False
        invoice = self.contract.recurring_create_invoice()
        self.assertAlmostEqual(invoice.invoice_line_ids[0].quantity, 0.0)

    def test_skip_zero_qty_keeps_sections_and_notes(self):
        """Sections and notes have no quantity, so they must stay on the
        invoice even when zero-quantity lines are skipped."""
        self.formula.code = "result=0"
        self.contract.skip_zero_qty = True
        self.env["contract.line"].create(
            {
                "contract_id": self.contract.id,
                "display_type": "line_section",
                "name": "Section header",
                "sequence": self.contract_line.sequence - 1,
            }
        )
        invoice = self.contract.recurring_create_invoice()
        self.assertTrue(
            invoice.invoice_line_ids.filtered(
                lambda line: line.display_type == "line_section"
            ),
            "The section line must be kept on the invoice",
        )

    def test_formula_security_batch_and_validation(self):
        manager = new_test_user(
            self.env,
            login="varqty_mgr",
            groups="base.group_user,account.group_account_manager",
        )
        with self.assertRaises(exceptions.AccessError):
            self.env["contract.line.qty.formula"].with_user(manager).create(
                {"name": "Forbidden", "code": "result = 1"}
            )
        with self.assertRaises(exceptions.AccessError):
            self.formula.with_user(manager).write({"code": "result = 2"})
        # Batch create + date arithmetic must work cleanly
        formulas = self.env["contract.line.qty.formula"].create(
            [
                {
                    "name": "Batch 1",
                    "code": "result = (period_last_date - period_first_date).days + 1",
                },
                {"name": "Batch 2", "code": "result = 5"},
            ]
        )
        self.assertEqual(len(formulas), 2)
        # Non-numeric result must be rejected
        with self.assertRaises(exceptions.ValidationError):
            self.formula.code = "result = True"
        with self.assertRaises(exceptions.ValidationError):
            self.formula.code = "result = 'bad'"
        # Side effects during validation must roll back
        before_count = self.env["res.partner"].search_count([("name", "=", "SideEffectPartner")])
        self.formula.code = (
            "env['res.partner'].create({'name': 'SideEffectPartner'})\nresult = 3"
        )
        after_count = self.env["res.partner"].search_count([("name", "=", "SideEffectPartner")])
        self.assertEqual(before_count, after_count)
