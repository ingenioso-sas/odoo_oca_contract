# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def post_init_hook(env):
    """Enable the OCA refund-on-stop behavior for existing companies.

    Pauses and terminations create a credit note when the contract was already
    invoiced for a period that is no longer served.
    """
    companies = env["res.company"].search([])
    companies.write({"enable_contract_line_refund_on_stop": True})
