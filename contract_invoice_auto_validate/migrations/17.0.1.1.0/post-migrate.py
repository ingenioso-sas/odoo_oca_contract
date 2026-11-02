# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Migrate legacy global flag to per-contract invoicing_mode.

Contracts in draft mode belonging to a company with
auto_post_contract_invoice=True move to invoicing_mode=validate,
so behaviour is preserved after unifying auto-validation in
contract.contract._auto_validate_invoices.
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE contract_contract AS cc
        SET invoicing_mode = 'validate'
        FROM res_company AS rc
        WHERE cc.company_id = rc.id
          AND rc.auto_post_contract_invoice IS TRUE
          AND cc.invoicing_mode = 'draft'
        """
    )
    cr.execute(
        """
        UPDATE contract_template AS ct
        SET invoicing_mode = 'validate'
        FROM res_company AS rc
        WHERE ct.company_id = rc.id
          AND rc.auto_post_contract_invoice IS TRUE
          AND ct.invoicing_mode = 'draft'
        """
    )
