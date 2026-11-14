# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Copy the old notification mode before the fields are dropped."""
    if not version:
        return

    # The old inherited views reference fields that this version removes.
    # Delete them before the model update so the new views can be validated
    # without the stale arch still being part of the combined view.
    view_names = (
        "contract_contract_form_view_notify",
        "contract_template_form_view_notify",
        "contract_contract_form_view",
        "contract_template_form_view",
    )
    cr.execute(
        """
        SELECT res_id
          FROM ir_model_data
         WHERE module = 'contract_invoice_notify'
           AND model = 'ir.ui.view'
           AND name IN %s
        """,
        (view_names,),
    )
    view_ids = [row[0] for row in cr.fetchall()]
    if view_ids:
        cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (tuple(view_ids),))
        cr.execute(
            """
            DELETE FROM ir_model_data
             WHERE module = 'contract_invoice_notify'
               AND model = 'ir.ui.view'
               AND name IN %s
            """,
            (view_names,),
        )
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'contract_contract'
        """
    )
    columns = {row[0] for row in cr.fetchall()}
    if "send_notification_mode" not in columns:
        return
    wa_column = (
        "whatsapp_template_id"
        if "whatsapp_template_id" in columns
        else "NULL AS whatsapp_template_id"
    )
    cr.execute("DROP TABLE IF EXISTS contract_invoice_notify_legacy")
    cr.execute(
        "CREATE TABLE contract_invoice_notify_legacy AS "
        "SELECT id, send_notification_mode, %s FROM contract_contract"
        % wa_column
    )

    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'contract_template'
        """
    )
    template_columns = {row[0] for row in cr.fetchall()}
    if "send_notification_mode" in template_columns:
        cr.execute("DROP TABLE IF EXISTS contract_invoice_notify_template_legacy")
        cr.execute(
            "CREATE TABLE contract_invoice_notify_template_legacy AS "
            "SELECT id, send_notification_mode FROM contract_template"
        )
