# Contract Billing Cycle

Adds a calendar billing cycle for post-paid contracts:

- a configurable **billing day** (default: the 1st of each month), independent
  from the contract start date;
- automatic **price proration** for the first partial period, keeping
  quantity at 1;
- a configurable **free trial** counted from the service start, with a
  percentage discount (default 100%) and prorated across the invoices that
  cover the trial range;
- an optional **zero invoice policy** to create or skip invoices whose total
  is zero.

The module is designed for post-paid contracts. It reuses
`contract_invoice_discount` for the trial and
`contract_variable_qty_prorated` for the proration ratio.
