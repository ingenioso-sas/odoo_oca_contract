# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ContractPause(models.Model):
    _name = "contract.pause"
    _description = "Contract Pause"
    _order = "start_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    contract_id = fields.Many2one(
        comodel_name="contract.contract",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="contract_id.company_id",
        store=True,
        index=True,
    )
    start_date = fields.Date(required=True)
    end_date = fields.Date()
    is_indefinite = fields.Boolean(
        string="Indefinite pause",
        help="If checked, the contract remains paused until it is resumed "
        "manually.",
    )
    reason_id = fields.Many2one(
        comodel_name="contract.pause.reason",
        string="Pause Reason",
        required=True,
        ondelete="restrict",
    )
    comment = fields.Text()
    state = fields.Selection(
        selection=[
            ("scheduled", "Scheduled"),
            ("active", "Active"),
            ("resumed", "Resumed"),
            ("cancelled", "Cancelled"),
        ],
        default="active",
        required=True,
        index=True,
    )
    resume_date = fields.Date(readonly=True)
    pause_days = fields.Integer(compute="_compute_pause_days")
    line_ids = fields.One2many(
        comodel_name="contract.pause.line",
        inverse_name="pause_id",
        string="Paused Lines",
        copy=False,
    )

    @api.depends("contract_id", "start_date")
    def _compute_name(self):
        for pause in self:
            pause.name = (
                f"{pause.contract_id.display_name or ''} - "
                f"{pause.start_date or ''}"
            ).strip(" -")

    @api.depends("start_date", "end_date", "is_indefinite", "state", "resume_date")
    def _compute_pause_days(self):
        today = fields.Date.context_today(self)
        for pause in self:
            if not pause.start_date:
                pause.pause_days = 0
            elif pause.state == "resumed" and pause.resume_date:
                pause.pause_days = (pause.resume_date - pause.start_date).days
            elif pause.state == "active" and pause.is_indefinite:
                pause.pause_days = max((today - pause.start_date).days, 0)
            elif pause.end_date:
                pause.pause_days = (pause.end_date - pause.start_date).days + 1
            else:
                pause.pause_days = 0

    @api.constrains("start_date", "end_date", "is_indefinite", "state", "contract_id")
    def _check_pause_consistency(self):
        for pause in self:
            if not pause.is_indefinite and not pause.end_date:
                raise ValidationError(
                    self.env._("An end date is required unless the pause is indefinite.")
                )
            if pause.end_date and pause.start_date and pause.end_date < pause.start_date:
                raise ValidationError(
                    self.env._("The pause end date cannot be before the start date.")
                )
            if pause.state in ("scheduled", "active") and pause.contract_id:
                overlap = self.search_count(
                    [
                        ("id", "!=", pause.id),
                        ("contract_id", "=", pause.contract_id.id),
                        ("state", "in", ("scheduled", "active")),
                    ]
                )
                if overlap:
                    raise ValidationError(
                        self.env._(
                            "A contract cannot have multiple active or scheduled pauses."
                        )
                    )

    def action_cancel_scheduled(self):
        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError(
                self.env._("Only accounting managers can cancel scheduled pauses.")
            )
        for pause in self:
            if pause.state != "scheduled":
                continue
            pause.sudo().write({"state": "cancelled"})
            pause.contract_id.message_post(
                body=self.env._("Scheduled pause (%s) cancelled.", pause.name)
            )
        return True

    @api.model
    def _activate_scheduled_pauses(self, date_ref=None, contract_ids=None):
        date_ref = date_ref or fields.Date.context_today(self)
        domain = [
            ("state", "=", "scheduled"),
            ("start_date", "<=", date_ref),
        ]
        if contract_ids is not None:
            domain.append(("contract_id", "in", list(contract_ids)))
        pauses = self.sudo().search(domain)
        for pause in pauses:
            if not pause.is_indefinite and pause.end_date and pause.end_date < date_ref:
                continue
            pause.write({"state": "active"})
            pause.contract_id.sudo().is_paused = True
        return pauses

    @api.model
    def _close_planned_pauses(self, date_ref=None, contract_ids=None):
        date_ref = date_ref or fields.Date.context_today(self)
        domain = [
            ("state", "in", ("scheduled", "active")),
            ("is_indefinite", "=", False),
            ("end_date", "<", date_ref),
        ]
        if contract_ids is not None:
            domain.append(("contract_id", "in", list(contract_ids)))
        pauses = self.sudo().search(domain)
        for pause in pauses:
            pause.write(
                {
                    "state": "resumed",
                    "resume_date": pause.end_date + timedelta(days=1),
                }
            )
            pause.contract_id.sudo().is_paused = False
            pause.contract_id.sudo().message_post(
                body=self.env._(
                    "Contract resumed automatically after the scheduled pause "
                    "ended on %(date)s.",
                    date=pause.end_date,
                )
            )
        return pauses


class ContractPauseLine(models.Model):
    _name = "contract.pause.line"
    _description = "Contract Pause Line"

    pause_id = fields.Many2one(
        comodel_name="contract.pause",
        required=True,
        ondelete="cascade",
        index=True,
    )
    contract_line_id = fields.Many2one(
        comodel_name="contract.line",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="pause_id.company_id",
        store=True,
    )
    action = fields.Selection(
        selection=[
            ("stopped", "Stopped"),
            ("delayed", "Delayed"),
        ],
        required=True,
    )
    original_date_start = fields.Date()
    original_date_end = fields.Date()
    original_recurring_next_date = fields.Date()
    original_is_auto_renew = fields.Boolean()
    successor_contract_line_id = fields.Many2one(
        comodel_name="contract.line",
        ondelete="set null",
    )
