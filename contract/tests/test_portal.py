# Copyright 2020 Tecnativa - Víctor Martínez
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

from odoo import Command, fields, http
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestContractPortal(HttpCase, BaseCommon):
    @mute_logger(
        "odoo.addons.contract.tests.test_portal.TestContractPortal.test_tour.browser"
    )
    def test_tour(self):
        partner = self.env["res.partner"].create({"name": "partner test contract"})
        contract = self.env["contract.contract"].create(
            {"name": "Test Contract", "partner_id": partner.id}
        )
        user_portal = self._create_new_portal_user(
            partner_id=partner.id, login="portal_contract", password="portal_contract"
        )
        self.start_tour("/", "contract_portal_tour", login="portal_contract")
        # Contract access
        self.authenticate("portal_contract", "portal_contract")
        http.root.session_store.save(self.session)
        url_contract = (
            f"/my/contracts/{contract.id}?access_token={contract.access_token}"
        )
        self.assertEqual(self.url_open(url=url_contract).status_code, 200)
        contract.message_unsubscribe(partner_ids=user_portal.partner_id.ids)
        self.assertEqual(self.url_open(url=url_contract).status_code, 200)

    def test_portal_rules_isolate_lines_and_modifications(self):
        partner_a = self.env["res.partner"].create({"name": "Portal A"})
        partner_b = self.env["res.partner"].create({"name": "Portal B"})
        user_a = self._create_new_portal_user(
            partner_id=partner_a.id, login="portal_a", password="portal_a"
        )
        contract_a = self.env["contract.contract"].create(
            {
                "name": "Contract A",
                "partner_id": partner_a.id,
                "contract_line_ids": [
                    Command.create({"name": "Line A", "quantity": 1, "price_unit": 10})
                ],
                "modification_ids": [
                    Command.create(
                        {"date": fields.Date.today(), "description": "Mod A"}
                    )
                ],
            }
        )
        contract_b = self.env["contract.contract"].create(
            {
                "name": "Contract B",
                "partner_id": partner_b.id,
                "contract_line_ids": [
                    Command.create({"name": "Line B", "quantity": 1, "price_unit": 20})
                ],
                "modification_ids": [
                    Command.create(
                        {"date": fields.Date.today(), "description": "Mod B"}
                    )
                ],
            }
        )
        visible_lines = self.env["contract.line"].with_user(user_a).search([])
        self.assertTrue(contract_a.contract_line_ids <= visible_lines)
        self.assertFalse(contract_b.contract_line_ids & visible_lines)
        visible_mods = self.env["contract.modification"].with_user(user_a).search([])
        self.assertTrue(contract_a.modification_ids <= visible_mods)
        self.assertFalse(contract_b.modification_ids & visible_mods)
        with self.assertRaises(AccessError):
            contract_b.contract_line_ids.with_user(user_a).read(["name"])
        with self.assertRaises(AccessError):
            contract_b.modification_ids.with_user(user_a).read(["description"])
