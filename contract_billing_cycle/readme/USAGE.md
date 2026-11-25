# Usage

## Configurar el ciclo de facturación

En el contrato, pestaña **Ciclo de facturación**:

- **Día de facturación**: día del mes en que se emite la factura pospaga.
  Por defecto, 1. Si el mes no tiene ese día, se usa el último día del mes.
- **Períodos completos gratis**: cantidad de períodos completos con descuento
  de prueba. 0 = sin prueba.
- **Descuento de prueba (%)**: porcentaje del descuento de prueba. Normalmente
  100.
- **Omitir facturas en cero**: si se marca, no se crea la factura cuando el
  total es cero. Las fechas del contrato avanzan igualmente.

Los mismos campos están disponibles en la plantilla del contrato y se copian
al crear un contrato desde la plantilla.

Configure el día de facturación y la prueba antes de generar la primera
factura. Después de que la línea tenga facturas, la regla de prueba no se
regenera automáticamente para no alterar un contrato ya iniciado.

## Ejemplo: inicio el 15 de octubre, facturar el 1

Contrato mensual pospago, día de facturación 1:

```text
Primer período:  15 oct – 31 oct
Primera factura: 1 nov
Importe:         precio mensual × 17/31
Siguiente:       1 nov – 30 nov, factura 1 dic
```

El precio se prorratea y la cantidad permanece en 1.

## Ejemplo: primer mes completo gratis

Contrato mensual pospago, inicio 15 de octubre, día 1, un período completo
gratis:

```text
Factura 1 nov: 15 oct – 31 oct → cobra prorrateado
Factura 1 dic: 1 nov – 30 nov   → 100% descuento
Factura 1 ene: 1 dic – 31 dic   → cobra completo
```

La prueba empieza en el primer período completo, no en el período parcial
inicial.

Si el período de prueba calculado cae en el pasado, se desplaza al primer
período completo futuro. Ejemplo con hoy 25 de noviembre:

```text
Prueba original: 1 nov – 30 nov
Prueba aplicada: 1 dic – 31 dic
```

Así el cliente recibe un mes completo futuro y no un beneficio retroactivo.

Si el contrato inicia el día 1, el primer período ya es completo y la primera
factura es la gratuita.

## Recalcular fechas

La acción **Recalcular fechas** de la línea también respeta el día de
facturación configurado. Si no hay facturas, calcula la próxima fecha desde el
inicio del contrato; si hay facturas, calcula el siguiente día de facturación
después del último período facturado.

## Facturas en cero

- **Omitir facturas en cero desmarcado** (por defecto): la factura de prueba
  se crea con importe 0.
- **Omitir facturas en cero marcado**: la factura no se crea; las fechas del
  contrato avanzan y la siguiente factura cobrable se genera normalmente. La
  prueba se marca como consumida para no volver a regalarla en un período
  futuro.

## Límites

- El ciclo de facturación y la prueba gratuita aplican a líneas **pospago**.
- Para líneas prepago se mantiene el comportamiento estándar del contrato.
- El período inicial parcial se cobra prorrateado; no se regala.
- La prueba no se extiende automáticamente al pausar el contrato.
