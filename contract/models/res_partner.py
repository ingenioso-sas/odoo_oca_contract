# Copyright 2017 Carlos Dauden <carlos.dauden@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ast import literal_eval

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sale_contract_count = fields.Integer(
        string="Sale Contracts",
        compute="_compute_contract_count",
    )
    purchase_contract_count = fields.Integer(
        string="Purchase Contracts",
        compute="_compute_contract_count",
    )
    contract_ids = fields.One2many(
        comodel_name="contract.contract",
        inverse_name="partner_id",
        string="Contracts",
    )

    def _get_partner_contract_domain(self):
        return [("partner_id", "child_of", self.ids)]

    def _compute_contract_count(self):
        if not self.ids:
            for partner in self:
                partner.sale_contract_count = 0
                partner.purchase_contract_count = 0
            return
        all_partners = self.env["res.partner"].search_fetch(
            [("id", "child_of", self.ids)], ["parent_id"]
        )
        parent_map = {p.id: p.parent_id.id for p in all_partners}
        fetch_data = self.env["contract.contract"].formatted_read_group(
            domain=[("partner_id", "in", all_partners.ids)],
            groupby=["partner_id", "contract_type"],
            aggregates=["__count"],
        )
        counts = {pid: {"sale": 0, "purchase": 0} for pid in self.ids}
        for row in fetch_data:
            ctype = row["contract_type"]
            if ctype not in ("sale", "purchase"):
                continue
            curr = row["partner_id"][0]
            count = row["__count"]
            visited = set()
            while curr and curr not in visited:
                visited.add(curr)
                if curr in counts:
                    counts[curr][ctype] += count
                curr = parent_map.get(curr)
        for partner in self:
            partner_counts = counts.get(partner.id, {})
            partner.sale_contract_count = partner_counts.get("sale", 0)
            partner.purchase_contract_count = partner_counts.get("purchase", 0)

    def act_show_contract(self):
        """This opens contract view
        @return: the contract view
        """
        self.ensure_one()
        contract_type = self.env.context.get("contract_type")

        res = self._get_act_window_contract_xml(contract_type)
        base_context = (
            literal_eval(res["context"].strip())
            if isinstance(res.get("context"), str)
            else dict(res.get("context") or {})
        )
        action_context = {
            **base_context,
            **{k: v for k, v in self.env.context.items() if k != "group_by"},
        }
        action_context["default_partner_id"] = self.id
        action_context["default_pricelist_id"] = self.property_product_pricelist.id
        res["context"] = action_context
        res["domain"] = (
            literal_eval(res["domain"]) + self._get_partner_contract_domain()
        )
        return res

    def _get_act_window_contract_xml(self, contract_type):
        if contract_type == "purchase":
            return self.env["ir.actions.act_window"]._for_xml_id(
                "contract.action_supplier_contract"
            )
        else:
            return self.env["ir.actions.act_window"]._for_xml_id(
                "contract.action_customer_contract"
            )
