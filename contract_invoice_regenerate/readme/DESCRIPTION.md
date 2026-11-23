# Contract Invoice Regenerate

Adds a controlled workflow for deleted contract invoices:

- recalculates `last_date_invoiced` and `recurring_next_date` from the
  invoices that still exist;
- regenerates a missing period with its original period and invoice date;
- prevents deleting posted contract invoices;
- recalculates the contract line automatically when a draft contract invoice
  is deleted.

The workflow is available only to administrators and uses the periods stored
by `contract_invoice_period`, so it does not depend on the `#START#` /
`#END#` markers.
