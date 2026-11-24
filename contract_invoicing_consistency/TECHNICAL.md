# Technical documentation: `contract_invoicing_consistency`

## Purpose

Prevent contract lines from being saved with a next invoice date that
produces an invalid next period, and warn about contracts that mix Pre-paid
and Post-paid lines.

## Dependencies

```python
depends = ["contract"]
```

## Validation

`contract.line._check_next_invoice_date_matches_period()` is a constraint on
the fields that feed the next period:

- `recurring_next_date`
- `next_period_date_start`
- `recurring_invoicing_type`
- `recurring_invoicing_offset`
- `recurring_rule_type`
- `recurring_interval`
- `date_start`
- `date_end`
- `last_date_invoiced`

For recurring product lines it reads `next_period_date_end` and rejects:

```text
next_period_date_end < next_period_date_start
```

The error includes the current invoice date, the period, the invoicing type
and the date expected by the contract configuration.

The constraint skips:

- section and note lines;
- cancelled lines when `is_canceled` is available.

## Mixed invoicing warning

`contract.contract.mixed_invoicing_warning` is a non-stored computed text
field. It is filled when the contract has both:

- at least one recurring line with `recurring_invoicing_type = 'pre-paid'`;
- at least one recurring line with a different type (effectively Post-paid).

The warning lists the line names and is displayed as an alert in the contract
form. It is added to the base, customer and supplier forms.

## Views

`views/contract_views.xml` adds the warning alert before the contract
notebook in:

- `contract.contract_contract_form_view`;
- `contract.contract_contract_customer_form_view`;
- `contract.contract_contract_supplier_form_view`.

## Tests

`tests/test_invoicing_consistency.py` covers:

- invalid Post-paid invoice date;
- invalid Pre-paid invoice date;
- valid Post-paid invoice date;
- rejection on write;
- mixed-type warning;
- no warning when all lines share the type.
