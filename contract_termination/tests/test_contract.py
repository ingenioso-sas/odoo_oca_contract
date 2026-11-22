# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user

from odoo.addons.contract_line_successor.tests.test_contract import (
    TestContractSuccessor,
    to_date,
)


class TestContractTermination(TestContractSuccessor):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.terminate_reason = cls.env["contract.terminate.reason"].create(
            {"name": "terminate_reason"}
        )

    def test_action_terminate_contract(self):
        action = self.contract.action_terminate_contract()
        wizard = (
            self.env[action["res_model"]]
            .with_context(**action["context"])
            .create(
                {
                    "terminate_date": "2018-03-01",
                    "terminate_reason_id": self.terminate_reason.id,
                    "terminate_comment": "terminate_comment",
                }
            )
        )
        self.assertEqual(wizard.contract_id, self.contract)
        wizard.terminate_contract()
        self.assertTrue(self.contract.is_terminated)
        self.assertEqual(self.contract.terminate_date, to_date("2018-03-01"))
        self.assertEqual(self.contract.terminate_reason_id.id, self.terminate_reason.id)
        self.assertEqual(self.contract.terminate_comment, "terminate_comment")
        self.contract.action_cancel_contract_termination()
        self.assertFalse(self.contract.is_terminated)
        self.assertFalse(self.contract.terminate_reason_id)
        self.assertFalse(self.contract.terminate_comment)

    def test_terminate_date_before_last_date_invoiced(self):
        self.contract.recurring_create_invoice()
        self.assertEqual(self.acct_line.last_date_invoiced, to_date("2018-02-14"))
        with self.assertRaises(ValidationError):
            self.contract._terminate_contract(
                self.terminate_reason,
                "terminate_comment",
                to_date("2018-02-13"),
            )
        # Try terminate contract line with last_date_invoiced allowed
        self.contract._terminate_contract(
            self.terminate_reason,
            "terminate_comment",
            to_date("2018-02-13"),
            terminate_lines_with_last_date_invoiced=True,
        )
        self.assertTrue(self.contract.is_terminated)
        self.assertEqual(self.acct_line.date_end, to_date("2018-02-14"))

    def test_stop_and_update_recurring_invoice_date(self):
        self.acct_line.write(
            {
                "date_start": "2019-01-01",
                "date_end": "2019-12-31",
                "recurring_next_date": "2020-01-01",
                "recurring_invoicing_type": "post-paid",
                "recurring_rule_type": "yearly",
            }
        )
        self.acct_line.stop(to_date("2019-05-31"))
        self.assertEqual(self.acct_line.date_end, to_date("2019-05-31"))
        self.assertEqual(self.acct_line.recurring_next_date, to_date("2019-06-01"))

    def test_terminate_user_with_group_can_terminate_without_manager(self):
        term_user = new_test_user(
            self.env,
            login="term_only_user",
            groups="base.group_user,contract_termination.can_terminate_contract",
        )
        contract_as_user = self.contract.with_user(term_user)
        contract_as_user._terminate_contract(
            self.terminate_reason,
            "Terminated by specialized user",
            to_date("2018-03-01"),
        )
        self.assertTrue(self.contract.is_terminated)
        invoicing_user = new_test_user(
            self.env,
            login="invoice_only_user",
            groups="base.group_user,account.group_account_invoice",
        )
        with self.assertRaises(UserError):
            self.contract.with_user(invoicing_user).action_cancel_contract_termination()
