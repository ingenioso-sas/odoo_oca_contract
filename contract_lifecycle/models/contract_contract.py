# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ContractContract(models.Model):
    _inherit = "contract.contract"

    is_paused = fields.Boolean(
        default=False,
        readonly=True,
        copy=False,
        help="Technical flag used to block invoice generation while paused.",
    )
    pause_ids = fields.One2many(
        comodel_name="contract.pause",
        inverse_name="contract_id",
        string="Pauses",
        copy=False,
    )
    current_pause_id = fields.Many2one(
        comodel_name="contract.pause",
        compute="_compute_current_pause_id",
        string="Current Pause",
    )
    can_resume = fields.Boolean(
        compute="_compute_current_pause_id",
        string="Can Resume",
    )
    lifecycle_state = fields.Selection(
        selection=[
            ("upcoming", "Upcoming"),
            ("running", "Running"),
            ("paused", "Paused"),
            ("terminated", "Terminated"),
            ("closed", "Closed"),
        ],
        compute="_compute_lifecycle_state",
        string="Lifecycle Status",
    )
    pause_count = fields.Integer(compute="_compute_current_pause_id")

    @api.depends("pause_ids.state", "pause_ids.is_indefinite")
    def _compute_current_pause_id(self):
        for contract in self:
            pause = contract.pause_ids.filtered(
                lambda item: item.state == "active"
            )[:1]
            contract.current_pause_id = pause
            contract.can_resume = bool(pause and pause.is_indefinite)
            contract.pause_count = len(contract.pause_ids)

    @api.depends(
        "is_terminated",
        "is_paused",
        "contract_line_ids.date_start",
        "contract_line_ids.date_end",
        "contract_line_ids.is_canceled",
    )
    def _compute_lifecycle_state(self):
        today = fields.Date.context_today(self)
        for contract in self:
            if contract.is_terminated:
                contract.lifecycle_state = "terminated"
                continue
            if contract.is_paused:
                contract.lifecycle_state = "paused"
                continue
            lines = contract._get_product_lines()
            if lines and all(
                line.date_start and line.date_start > today for line in lines
            ):
                contract.lifecycle_state = "upcoming"
            elif lines and all(
                line.date_end and line.date_end < today for line in lines
            ):
                contract.lifecycle_state = "closed"
            else:
                contract.lifecycle_state = "running"

    def _get_product_lines(self):
        self.ensure_one()
        return self.contract_line_ids.filtered(
            lambda line: not line.display_type and not line.is_canceled
        )

    def action_pause_contract(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Pause Contract"),
            "res_model": "contract.pause.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_contract_id": self.id},
        }

    def action_resume_contract(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Resume Contract"),
            "res_model": "contract.resume.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_contract_id": self.id,
                "default_pause_id": self.current_pause_id.id,
            },
        }

    def _pause_contract(
        self,
        start_date,
        end_date=False,
        is_indefinite=False,
        reason=False,
        comment=False,
    ):
        self.ensure_one()
        if self.is_terminated:
            raise UserError(self.env._("A terminated contract cannot be paused."))
        if self.is_paused:
            raise UserError(self.env._("The contract is already paused."))
        if not start_date:
            raise ValidationError(self.env._("The pause start date is required."))
        if is_indefinite:
            end_date = False
        elif not end_date:
            raise ValidationError(self.env._("The pause end date is required."))
        if end_date and end_date < start_date:
            raise ValidationError(
                self.env._("The pause end date cannot be before the start date.")
            )
        if reason.requires_comment and not comment:
            raise ValidationError(
                self.env._("The selected pause reason requires a comment.")
            )
        pause_days = 0 if is_indefinite else (end_date - start_date).days + 1
        pause = self.env["contract.pause"].create(
            {
                "contract_id": self.id,
                "start_date": start_date,
                "end_date": end_date,
                "is_indefinite": is_indefinite,
                "reason_id": reason.id,
                "comment": comment,
                "state": "active",
            }
        )
        self.is_paused = True
        for line in self._get_product_lines():
            if line.date_end and line.date_end < start_date:
                continue
            original = {
                "original_date_start": line.date_start,
                "original_date_end": line.date_end,
                "original_recurring_next_date": line.recurring_next_date,
            }
            action = "delayed"
            successor = self.env["contract.line"]
            if line.date_start and line.date_start >= start_date:
                if not is_indefinite:
                    old_start = line.date_start
                    line.stop_plan_successor(start_date, end_date, False)
                    shift_days = (
                        (line.date_start - old_start).days
                        if line.date_start and old_start
                        else 0
                    )
                    if shift_days:
                        self._shift_discount_rules(line, shift_days)
                # Indefinite future lines stay untouched; the paused flag
                # prevents the invoice cron from processing them.
            elif is_indefinite:
                if not line.is_stop_allowed:
                    continue
                line.stop(start_date - timedelta(days=1), manual_renew_needed=True)
                line.recurring_next_date = start_date
                action = "stopped"
            else:
                if not line.is_stop_plan_successor_allowed:
                    continue
                line.stop_plan_successor(start_date, end_date, False)
                successor = line.successor_contract_line_id
                if successor:
                    action = "stopped"
                    self._copy_discount_rules(line, successor, pause_days)
                    line.recurring_next_date = (
                        successor.recurring_next_date or successor.date_start
                    )
                else:
                    old_start = original["original_date_start"]
                    shift_days = (
                        (line.date_start - old_start).days
                        if line.date_start and old_start
                        else 0
                    )
                    if shift_days:
                        self._shift_discount_rules(line, shift_days)
            self.env["contract.pause.line"].create(
                {
                    "pause_id": pause.id,
                    "contract_line_id": line.id,
                    "action": action,
                    "successor_contract_line_id": successor.id,
                    **original,
                }
            )
        if not is_indefinite:
            self._add_referral_paused_days(pause_days)
        self.message_post(
            body=self.env._(
                "Contract paused from %(start)s%(end)s. Reason: %(reason)s",
                start=start_date,
                end=(
                    self.env._(" with no end date")
                    if is_indefinite
                    else self.env._(" to %(date)s", date=end_date)
                ),
                reason=reason.name,
            )
        )
        return pause

    def _resume_contract(self, pause, resume_date):
        self.ensure_one()
        if pause.state != "active" or not pause.is_indefinite:
            raise UserError(self.env._("This pause cannot be resumed manually."))
        if resume_date < pause.start_date:
            raise ValidationError(
                self.env._("The resume date cannot be before the pause start date.")
            )
        pause_days = (resume_date - pause.start_date).days
        for pause_line in pause.line_ids:
            line = pause_line.contract_line_id
            if not line.exists():
                continue
            if pause_line.action == "delayed":
                self._shift_line_dates(line, pause_days)
                self._shift_discount_rules(line, pause_days)
            elif not pause_line.successor_contract_line_id:
                original_end = pause_line.original_date_end
                new_end = (
                    original_end + timedelta(days=pause_days)
                    if original_end
                    else False
                )
                new_start = resume_date
                recurring_next_date = line.get_next_invoice_date(
                    new_start,
                    line.recurring_invoicing_type,
                    line.recurring_invoicing_offset,
                    line.recurring_rule_type,
                    line.recurring_interval,
                    max_date_end=new_end,
                )
                successor = line.plan_successor(
                    new_start,
                    new_end,
                    False,
                    recurring_next_date=recurring_next_date,
                )
                pause_line.successor_contract_line_id = successor
                self._copy_discount_rules(line, successor, pause_days)
                line.recurring_next_date = (
                    successor.recurring_next_date or successor.date_start
                )
        self._add_referral_paused_days(pause_days)
        pause.write(
            {
                "state": "resumed",
                "resume_date": resume_date,
            }
        )
        self.is_paused = False
        self.message_post(
            body=self.env._("Contract resumed on %(date)s.", date=resume_date)
        )
        return True

    def _shift_line_dates(self, line, days):
        if not days:
            return
        if line.date_start:
            line.date_start = line.date_start + timedelta(days=days)
        if line.date_end:
            line.date_end = line.date_end + timedelta(days=days)
        if line.recurring_next_date:
            line.recurring_next_date = (
                line.recurring_next_date + timedelta(days=days)
            )

    def _shift_discount_rules(self, line, days):
        if not days:
            return
        for rule in line.invoice_discount_ids.filtered("active"):
            if rule.pause_policy != "service":
                continue
            rule.date_start = rule.date_start + timedelta(days=days)
            if rule.date_end:
                rule.date_end = rule.date_end + timedelta(days=days)

    def _copy_discount_rules(self, source_line, target_line, pause_days):
        for rule in source_line.invoice_discount_ids.filtered("active"):
            if rule.max_invoices:
                remaining = rule.max_invoices - rule.applied_invoice_count
                if remaining <= 0:
                    continue
            else:
                remaining = 0
            date_start = rule.date_start
            date_end = rule.date_end
            if rule.pause_policy == "service":
                if pause_days:
                    date_start = date_start + timedelta(days=pause_days)
                    if date_end:
                        date_end = date_end + timedelta(days=pause_days)
            target_line.invoice_discount_ids = [
                Command.create(
                    {
                        "name": rule.name,
                        "discount": rule.discount,
                        "date_start": date_start,
                        "date_end": date_end,
                        "max_invoices": remaining,
                        "source": rule.source,
                        "referral_id": rule.referral_id.id,
                        "pause_policy": rule.pause_policy,
                    }
                )
            ]
            rule.active = False

    def _add_referral_paused_days(self, days):
        if not days:
            return
        referrals = self.env["contract.referral"].search(
            [
                ("referred_contract_id", "=", self.id),
                ("state", "=", "active"),
            ]
        )
        referrals._add_paused_days(days)

    def _close_active_pauses_for_termination(self, terminate_date):
        pauses = self.pause_ids.filtered(lambda item: item.state == "active")
        for pause in pauses:
            if (
                not pause.is_indefinite
                and terminate_date
                and terminate_date < pause.end_date
            ):
                actual_days = max((terminate_date - pause.start_date).days, 0)
                self._add_referral_paused_days(actual_days - pause.pause_days)
            pause.write({"state": "cancelled"})
        self.is_paused = False

    def _finish_referrals(self):
        referrals = self.env["contract.referral"].search(
            [
                ("referred_contract_id", "=", self.id),
                ("state", "=", "active"),
            ]
        )
        referrals.write({"state": "finished"})
        referrals.discount_rule_ids.write({"active": False})

    def _deactivate_discounts(self):
        rules = self.env["contract.invoice.discount"].search(
            [("contract_id", "=", self.id)]
        )
        rules.write({"active": False})

    def _terminate_contract(self, *args, **kwargs):
        self.ensure_one()
        if not self.env.user.has_group("contract_termination.can_terminate_contract"):
            raise UserError(self.env._("You are not allowed to terminate contracts."))
        self.check_access("read")
        self._check_company()
        terminate_date = kwargs.get("terminate_date")
        if not terminate_date and len(args) > 2:
            terminate_date = args[2]
        self.sudo()._close_active_pauses_for_termination(terminate_date)
        result = super()._terminate_contract(*args, **kwargs)
        contract_sudo = self.sudo()
        contract_sudo._finish_referrals()
        contract_sudo._deactivate_discounts()
        contract_sudo.is_paused = False
        return result

    def action_cancel_contract_termination(self):
        raise UserError(
            self.env._(
                "Contract termination is final and cannot be undone. Create a "
                "new contract if service must resume."
            )
        )

    @api.model
    def _get_contracts_to_invoice_domain(self, date_ref=None):
        domain = super()._get_contracts_to_invoice_domain(date_ref)
        return fields.Domain.AND(
            [domain, [("is_paused", "=", False)]]
        )

    def recurring_create_invoice(self):
        self.ensure_one()
        self.env["contract.pause"]._close_planned_pauses(
            fields.Date.context_today(self)
        )
        return super().recurring_create_invoice()

    @api.model
    def _cron_recurring_create(self, date_ref=False, create_type="invoice"):
        if not date_ref:
            date_ref = fields.Date.context_today(self)
        self.env["contract.pause"]._close_planned_pauses(date_ref)
        return super()._cron_recurring_create(date_ref, create_type)
