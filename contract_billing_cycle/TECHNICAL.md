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
| `free_trial_duration` | Trial duration from the service start (default 0) |
| `free_trial_unit` | Trial unit: days or months |
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

If the service starts exactly on the anchor and the recurrence period is
longer than one month, the first period is a **full recurrence period**. For
example, an annual line starting 1 November is first invoiced one year later
for the full year, not one month later.

For later periods, `_get_anchor_date_on_or_after()` is applied to the standard
recurrence date. If the billing day changed, the invoice moves to the next
anchor; otherwise the standard date is kept. This works for monthly,
quarterly, semesterly and yearly rules, including intervals different from 1
(for example, monthly every 12 months).

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

The trial is a date range counted from the **service start**:

```text
trial_start = date_start
trial_end   = date_start + duration - 1 day
```

`duration` is expressed in days or months according to `free_trial_unit`.
The range is not moved to the future if it is in the past.

- `_get_free_trial_dates()` returns the range, clamped to `date_end`.
- `_sync_free_trial_discount()` creates or updates a
  `contract.invoice.discount` rule linked to the line:
  - `is_free_trial = True`;
  - `discount = free_trial_discount`;
  - `start_mode = fixed_date`;
  - `date_start = trial_start`;
  - `date_end = trial_end`;
  - `max_invoices = 0`;
  - `pause_policy = calendar` (no extension on pause).

The rule is created on line create, updated when the line dates or the
contract trial fields change, and deactivated when the trial is disabled. It
is also synchronized before preparing each invoice line.

`contract_invoice_discount` prorates the percentage by the overlap between the
trial range and each invoice period. For a one-month trial starting 15 October:

```text
invoice 15 Oct – 31 Oct: 17/17 days → 100% discount
invoice 1 Nov – 30 Nov:  14/30 days → 46.67% discount
invoice 1 Dec – 31 Dec:   0/31 days → no discount
```

Lines with `predecessor_contract_line_id` (successors/renewals) do not receive
a new trial. `copy_data()` removes the trial rule from copied lines.

## Zero invoice policy

`contract.contract._prepare_recurring_invoices_values()` is called per
contract. When `skip_zero_invoices` is enabled:

1. the standard values are built (which advances `last_date_invoiced`);
2. the untaxed total of each invoice is computed from its product lines;
3. invoices whose total is zero are removed before `account.move.create()`.

The trial rule is not consumed or deactivated: if the trial continues into the
next invoice period, that invoice still receives the corresponding prorated
discount.

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
- yearly, quarterly, semesterly and monthly-interval recurrences;
- intervals different from 1 (quarterly every 2, monthly every 12, yearly every 2);
- start exactly on the anchor for quarterly and yearly rules;
- pre-paid lines keep the standard behaviour;
- trial from the service start prorated across invoices;
- trial starts on the service start;
- trial duration in days;
- entirely past trial still applied;
- zero invoice skipped or created;
- commercial discount on top of the prorated price;
- template field copy.
