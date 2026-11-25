# Technical documentation: `contract_invoice_regenerate`

## Purpose

Keep the recurring dates of a contract line consistent when an invoice is
deleted, and provide a controlled way to recreate the missing invoice.

## Dependencies

```python
depends = ["contract_invoice_period", "account"]
```

## Problem

`contract.line.last_date_invoiced` is readonly and only advances when an
invoice is generated. Deleting an invoice does not rewind it. The constraint
`recurring_next_date > last_date_invoiced` then blocks the user from setting
the next invoice date.

## Models

### `contract.line`

Helpers:

| Method | Purpose |
|---|---|
| `_get_contract_invoice_lines()` | Draft/posted invoice lines for the contract line |
| `_get_invoice_line_period(invoice_line)` | Period from the structured fields, with a fallback to the billing/invoice date |
| `_get_invoice_lines_for_period(start, end)` | Invoice lines that overlap a period |
| `_get_last_invoiced_period_end()` | End of the last invoiced period |
| `_get_recalculated_invoice_dates()` | Last date invoiced and next invoice date |
| `_recalculate_invoice_dates()` | Writes both dates in one operation |

`_get_recalculated_next_invoice_date()` uses the optional
`_get_anchor_invoice_date()` hook when the line provides it (installed by
`contract_billing_cycle`). Otherwise it falls back to the standard recurrence
date. This makes the recalculation respect the billing day both before and
after invoices exist.

Actions:

- `action_recalculate_invoice_dates()`: admin-only, writes the dates computed
  from the existing invoices and posts a message on the contract.
- `action_regenerate_invoice()`: admin-only, opens the regeneration wizard
  with the next missing period and the original invoice date.

`_get_period_to_invoice()` returns the explicit period when the context key
`contract_invoice_period_override` is present, so the quantity, the
`#START#`/`#END#` markers, discounts and other extensions use the regenerated
period instead of the line's current dates.

`_prepare_invoice_line()` also accepts the context key
`contract_invoice_period_override` to store the explicit period on the invoice
line:

```python
line.with_context(
    contract_invoice_period_override={
        "period_start": date(2026, 2, 1),
        "period_end": date(2026, 2, 28),
        "invoice_date": date(2026, 3, 1),
    }
)._prepare_invoice_line()
```

This allows the wizard to create an invoice for an explicit period without
moving the contract line dates first.

### `contract.regenerate.invoice`

Transient wizard with:

- `contract_line_id`;
- `period_start`, `period_end`;
- `invoice_date`;
- `post_invoice`;
- computed `existing_invoice_ids` / `existing_invoice_names`.

`action_regenerate_invoice()`:

1. Checks the admin group.
2. Blocks the period when an invoice already exists.
3. Builds the invoice with `contract._prepare_invoice()` and the line values
   with the explicit period.
4. Creates the invoice and optionally posts it.
5. Recalculates the contract line dates from the current invoices.
6. Posts a message on the contract.

The wizard never rewinds dates by itself. After creating the invoice, the
recalculation uses all draft/posted invoices of the line, so later periods
remain authoritative.

### `account.move`

`@api.ondelete(at_uninstall=False)` blocks deleting posted invoices that have
contract lines. The error points the user to cancellation, a credit note or
the regeneration wizard.

`unlink()` recalculates the affected contract lines after deleting draft
contract invoices. The context key `contract_skip_recalculate` skips this
recalculation, and `contract_allow_posted_invoice_delete` is reserved for
maintenance scripts.

## Period fallback

`contract_invoice_period` stores `contract_period_start`,
`contract_period_end` and `contract_billing_date` on invoice lines. Invoices
created before the module was installed do not have these fields. For those,
the period is derived from the billing date or the invoice date:

- pre-paid: the invoice date is the period start;
- post-paid: the period end is the invoice date minus the invoicing offset.

The structured fields always take precedence.

## Security

Group: `contract_invoice_regenerate.group_contract_invoice_regenerate`
("Contrato: Regenerar facturas"), implied by `base.group_system`.

The wizard ACL and the line actions are restricted to that group. The posted
invoice deletion block applies to every user.

## Tests

`tests/test_contract_invoice_regenerate.py` covers:

- recalculation after deleting the last draft invoice;
- regeneration with the original period and invoice date;
- duplicate period prevention;
- posted invoice deletion block;
- automatic recalculation after deleting a draft invoice;
- fallback for invoices without structured periods;
- admin-only access.
