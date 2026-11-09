# Documentación técnica: `contract_referral`

## Propósito

Gestionar los dos beneficios de un referido:

- descuento para el cliente referido;
- comisión para el cliente referente.

## Modelo `contract.referral`

Campos principales:

- `referrer_id`, `referred_id`, `referred_contract_id`;
- `start_date`, `max_months`, `max_invoices`, `end_date`;
- `referrer_commission_percent`;
- `referred_discount_percent`;
- `commission_base` (`untaxed` o `total`);
- `state`;
- `referred_discount_lost` y `referred_discount_lost_date`.

Al crear o modificar un referido se sincronizan las reglas de descuento del
referido en todas las líneas de producto del contrato.

## Descuento del referido

Se crea una regla `contract.invoice.discount` por línea de contrato con:

- `source = referral`;
- `referral_id`;
- porcentaje;
- fecha de inicio y fin;
- máximo de facturas.

La condición del descuento se evalúa en cada factura:

- el referido debe tener contrato activo;
- no debe estar fuera del límite de meses;
- no debe tener facturas vencidas.

Si tiene una factura vencida, se marca `referred_discount_lost` y se
desactivan las reglas. El beneficio no se recupera.

## Comisión del referente

Al validar una factura de cliente:

1. Se busca el contrato de la factura.
2. Se busca un referido activo para ese contrato.
3. Se verifican contrato activo, fechas y máximo de facturas.
4. Se crea `contract.referral.commission` con:
   - factura del referido;
   - base (`amount_untaxed` o `amount_total`);
   - porcentaje;
   - monto calculado.

El estado de la comisión refleja el estado de cobro de la factura del
referido: borrador, pendiente, pagada o cancelada. No genera
automáticamente una factura de proveedor para pagar la comisión.

## Límites

- `max_months = 0`: sin límite de meses.
- `max_invoices = 0`: sin límite de facturas.
- Si ambos están definidos, se detiene lo primero que ocurra.
- Si el referido se atrasa, el descuento se pierde para siempre.
- La comisión del referente sigue mientras el contrato esté activo y dentro
  de los límites.

## Limitaciones

- No genera factura de proveedor para pagar la comisión.
- No recalcula facturas históricas.
- La comisión se calcula sobre la factura después de los descuentos.
- Un referido se asocia a un contrato específico.
