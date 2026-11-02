# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.contract.controllers.main import PortalContract


class PortalContractPayment(PortalContract):
    @http.route(
        ["/my/contracts/<int:contract_contract_id>/pay-all"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_contract_pay_all(self, contract_contract_id, access_token=None, **kw):
        try:
            contract_sudo = self._document_check_access(
                "contract.contract", contract_contract_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        pending = contract_sudo._get_pending_invoices()
        if not pending:
            return request.redirect(
                contract_sudo.get_portal_url(query_string="&message=no_pending")
            )
        url = contract_sudo._create_pay_all_link()
        if url:
            return request.redirect(url)
        return request.redirect(
            contract_sudo.get_portal_url(query_string="&message=no_psp")
        )
