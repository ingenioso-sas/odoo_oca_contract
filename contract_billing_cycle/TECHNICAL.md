# Technical documentation: `contract_billing_cycle`

## Purpose

Decouple the post-paid invoice date from the contract start date, prorate the
first partial period and configure a free trial for the first full periods.

## Dependencies

```python
depends = [
    "contract_invoice_discount",
    "contract_variable_qty_prorated",
]
```

## Contract fields

Added to `contract.template` and inherited by `contract.contract`:

| Field | Purpose |
|---|---|
| `billing_anchor_day` | Invoice day of the month (1–31, default 1) |
| `free_trial_periods` | Number of full periods with the trial discount |
| `free_trial_discount` | Trial discount percentage (default 100) |
| `skip_zero_invoices` | Skip invoices whose total is zero |

## Billing anchor

`contract.line._compute_recurring_next_date()` calls the standard computation
and then overrides the first invoice date when:

- the line is post-paid;
- the rule is monthly, quarterly, semesterly or yearly;
- there is no `last_date_invoiced`;
- the contract has a billing anchor.

The first invoice date is:

```text
first_anchor = next occurrence of billing_anchor_day after date_start
first_invoice_date = first_anchor - 1 day + invoicing_offset
```

For a post-paid monthly line the offset is 1, so the first invoice date is the
first anchor date. The period is `date_start` to `first_anchor - 1`.

The create values are also adjusted before the insert
(`_apply_billing_anchor_to_vals`) because `recurring_next_date` is a computed
field that Odoo does not recompute when it is explicitly provided.

`_get_anchor_invoice_date(next_period_start)` returns the anchor-aligned
invoice date for any period start. It is used by
`contract_invoice_regenerate` when recalculating dates, so the recalculation
respects the billing day before and after invoices exist.

## First-period price proration

`contract.line._prepare_invoice_line()` calls
`compute_prorated(period_start, period_end, invoice_date)` from
`contract_variable_qty_prorated`. When the ratio is lower than 1:

- `quantity` stays unchanged;
- `price_unit` is multiplied by the ratio;
- the line description gets a `(prorrateado XX%)` suffix.

This composes with `contract_invoice_discount`, because the discount is
applied on the prorated unit price. If the line uses the "Prorated Quantity"
formula, the price proration is skipped to avoid a double adjustment.

## Free trial

The trial applies to the first **full** periods, not to the initial partial
period.

- `_get_first_full_period_start()` returns `date_start` when it is an anchor
  date, otherwise the next anchor date.
- `_get_free_trial_end()` iterates the recurrence rule N times.
- `_sync_free_trial_discount()` creates or updates a
  `contract.invoice.discount` rule linked to the line:
  - `is_free_trial = True`;
  - `discount = free_trial_discount`;
  - `start_mode = fixed_date`;
  - `date_start = first full period start`;
  - `date_end = last day of the last free period`;
  - `max_invoices = 0`;
  - `pause_policy = calendar` (no extension on pause).

The rule is created on line create, updated when the line dates or the
contract trial fields change, and deactivated when the trial is disabled.
After the line has `last_date_invoiced`, the rule is not regenerated, to avoid
giving a new trial after the contract has started.

Lines with `predecessor_contract_line_id` (successors/renewals) do not receive
a new trial. `copy_data()` removes the trial rule from copied lines.

## Zero invoice policy

`contract.contract._prepare_recurring_invoices_values()` is called per
contract. When `skip_zero_invoices` is enabled:

1. the standard values are built (which advances `last_date_invoiced`);
2. the untaxed total of each invoice is computed from its product lines;
3. invoices whose total is zero are removed before `account.move.create()`.

A message is posted on the contract when an invoice is skipped.

## Views

- contract form: new **Ciclo de facturación** page in the base, customer and
  supplier forms;
- contract template form: same page;
- contract line form: billing anchor and trial dates in the base, customer
  and supplier forms.

## Tests

`tests/test_contract_billing_cycle.py` covers:

- first invoice moved to the anchor day;
- full period without proration;
- custom anchor day;
- pre-paid lines keep the standard behaviour;
- first full period free;
- start on the anchor day;
- zero invoice skipped or created;
- commercial discount on top of the prorated price;
- template field copy.
