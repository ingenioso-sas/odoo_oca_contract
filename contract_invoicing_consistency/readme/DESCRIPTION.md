# Contract Invoicing Consistency

Protects the contract recurrence configuration:

- rejects a next invoice date that would leave the next period without days;
- warns when a contract mixes Pre-paid and Post-paid lines.

The validation is especially useful after manually changing the next invoice
date: the period end is recalculated from that date, and an incoherent value
can make it earlier than the period start.
