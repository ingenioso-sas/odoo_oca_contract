# AGENTS.md — `contract_referral`

## Reglas

- Un referido tiene dos beneficios separados: descuento para el referido y
  comisión para el referente.
- El descuento del referido se implementa con reglas de
  `contract_invoice_discount`.
- La comisión del referente no es un descuento: es un registro de comisión
  sobre la factura del referido.
- Solo se aplica el mayor descuento; el módulo de descuentos resuelve la
  competencia entre promoción y referido.
- Si el referido tiene una factura vencida, el descuento del referido se
  pierde para siempre.
- La comisión del referente se mantiene mientras el contrato del referido
  esté activo y dentro de los límites.
- Los límites son acumulativos: máximo de meses y máximo de facturas; se
  detiene lo primero que ocurra.
- No recalcular facturas históricas.
- No permitir que un cliente se refiera a sí mismo.
- No permitir dos referidos activos para el mismo contrato.

## Archivos clave

- `models/contract_referral.py`: referido, reglas de descuento, condición de
  mora y límites.
- `models/contract_referral_commission.py`: comisión por factura del referido.
- `models/contract_invoice_discount.py`: condición del descuento por referido.
- `models/account_move.py`: creación de comisiones al validar la factura.
- `models/contract_line.py`: sincronización de reglas al crear líneas.
- `views/contract_referral_views.xml`: gestión del referido.
- `views/contract_referral_commission_views.xml`: comisiones.
