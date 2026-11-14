1. Abrir una línea de contrato.
2. Ir a la pestaña **Descuentos de factura**.
3. Crear una regla con:
   - nombre;
   - porcentaje;
   - modo de inicio: fecha fija, inicio del contrato o próxima factura;
   - fecha de inicio y fin;
   - máximo de facturas (0 = sin límite);
   - política de pausa: extender durante la pausa o mantener fechas.
4. Generar la factura desde el contrato.

Con **Próxima factura**, la regla empieza en el próximo período que se va a
facturar, aunque el contrato esté atrasado o tenga fecha de inicio anterior.
Con **Inicio del contrato**, empieza en la fecha de inicio de la línea. En
ambos casos la fecha se calcula al guardar la regla y queda visible en
**Fecha inicio**.

La factura muestra la columna estándar **Descuento** y, debajo de la
descripción de la línea, el nombre y la vigencia del descuento aplicado.

En la plantilla del contrato, la línea tiene los campos de promoción:

- nombre de la promoción;
- porcentaje;
- duración en meses;
- máximo de facturas.

Al crear un contrato desde la plantilla, esos valores se convierten en una
regla de descuento en la línea del contrato.
