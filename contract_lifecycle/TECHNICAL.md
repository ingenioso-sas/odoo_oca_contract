# Documentación técnica: `contract_lifecycle`

## Propósito

Agregar un ciclo de vida a nivel de contrato sobre las herramientas OCA por
línea:

- pausa planificada;
- pausa indefinida;
- reanudación;
- terminación definitiva.

## Dependencias

```text
contract_line_successor
contract_termination
contract_refund_on_stop
contract_invoice_discount
contract_referral
```

## Estado del contrato

`lifecycle_state` se calcula con:

- `is_terminated`;
- `is_paused`;
- fechas de las líneas de producto no canceladas.

Valores: `upcoming`, `running`, `paused`, `terminated`, `closed`.

## Pausa

1. Se crea un registro `contract.pause` con motivo, fechas y estado.
2. Se marca `is_paused=True`.
3. Por cada línea de producto:
   - línea ya iniciada y pausa planificada: `stop_plan_successor()`;
   - línea ya iniciada y pausa indefinida: `stop(manual_renew_needed=True)`;
   - línea futura: se deja intacta y se registra como `delayed`.
4. Se copian o desplazan las reglas de descuento según `pause_policy`.
5. En pausa planificada se suman los días de pausa al referido.
6. Se bloquea el cron con `is_paused`.

## Reanudación

- Pausa planificada: se cierra automáticamente al pasar `end_date`; la línea
  sucesora ya fue creada por OCA.
- Pausa indefinida: el asistente crea la línea sucesora con `plan_successor()`
  y ajusta fechas y reglas.

## Terminación

Se reutiliza `contract_termination`. Además:

- se cierran las pausas activas;
- se marcan los referidos como `finished`;
- se desactivan las reglas de descuento;
- se bloquea la reactivación.

## Notas de crédito

`contract_refund_on_stop` crea una nota de crédito si la línea se detiene
después de haber sido facturada. El módulo habilita esa opción por compañía.
Las notas de crédito del referido generan ajustes negativos de comisión.
