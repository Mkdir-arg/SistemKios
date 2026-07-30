# Transferencias

La transferencia **no tiene pantalla propia**: se arma desde la de Stock
([REQ-STK-013](03-stock.md#req-stk-013--todo-el-stock-se-opera-desde-una-sola-pantalla)).
Acá viven las reglas del movimiento en sí; la app conserva el modelo, el servicio y el
historial.

### REQ-TRF-001 · Las transferencias mueven stock entre ubicaciones y las hace el Super Admin
**Estado:** implementado · **Dónde:** [stock/views.py](../../apps/stock/views.py) (`transferir`), [stock/ingreso.html](../../templates/stock/ingreso.html)

Se transfiere desde `/stock/`, en el modo «Transferir». El modo solo se le muestra al Super
Admin y el endpoint `stock:transferir` devuelve **403** a cualquier otro, sin importar lo que
mande el navegador.

**Por qué:** repartir mercadería es una decisión del dueño, no del que atiende. Si el vendedor
pudiera sacarse stock de encima, el control se pierde.

**Reemplaza a:** la pantalla `/transferencias/nueva/`, que quedó como redirect a `/stock/`.

### REQ-TRF-002 · Cada ítem genera una salida en origen y una entrada en destino
**Estado:** implementado · **Dónde:** [transferencias/services.py](../../apps/transferencias/services.py)

`crear_transferencia` es atómica: por cada ítem llama dos veces a `aplicar_movimiento`
(`transf_out` en origen, `transf_in` en destino), con la nota que identifica la transferencia
y la contraparte. Además valida que origen y destino existan y sean **distintos**, y que haya
al menos un producto.

**Por qué:** el kardex de cada punto tiene que explicar por sí solo de dónde salió o entró la
mercadería, sin tener que cruzar tablas.

### REQ-TRF-003 · Si falta stock de un ítem, no se transfiere nada
**Estado:** implementado · **Dónde:** [transferencias/services.py](../../apps/transferencias/services.py)

El `StockInsuficiente` del origen revierte la transacción completa: ni la transferencia ni los
movimientos ya aplicados quedan.

**Por qué:** una transferencia a medias deja los dos puntos mal contados y sin forma de saber
qué se envió realmente.

### REQ-TRF-004 · La transferencia es instantánea: no hay mercadería en tránsito
**Estado:** implementado · **Dónde:** [transferencias/models.py](../../apps/transferencias/models.py)

El único estado es `completada`. El stock sale del origen y entra al destino en el mismo
momento.

**Por qué:** los locales están cerca y el reparto lo hace el dueño en el día. Un estado «en
tránsito» exigiría que alguien confirme la recepción en el otro punto, y eso no va a pasar de
forma confiable. Si aparecen envíos que tardan días, esto se revisa.

### REQ-TRF-005 · Al escanear se ve el stock disponible en el origen
**Estado:** implementado · **Dónde:** [stock/views.py](../../apps/stock/views.py) (`buscar`), [stock/ingreso.html](../../templates/stock/ingreso.html)

El escaneo usa el mismo endpoint que el resto de la pantalla (`/stock/buscar/`), que ya
devuelve el stock en la ubicación de trabajo. Ese número es el **disponible** del ítem: el
`+` no deja pasarlo y cada escaneo repetido lo vuelve a leer, así que si otra caja vendió
mientras se armaba el envío, el tope se corrige.

**Por qué:** es el número que decide cuánto se puede mandar. Y no hacía falta un segundo
endpoint de búsqueda: el de stock ya daba esto y más.

### REQ-TRF-007 · Un envío es un solo remito con todos sus ítems
**Estado:** implementado · **Dónde:** [stock/ingreso.html](../../templates/stock/ingreso.html), [transferencias/services.py](../../apps/transferencias/services.py)

El origen es la ubicación de trabajo y el destino se elige **una vez**, antes de escanear.
Cada escaneo suma una unidad al envío; al confirmar se crea **una** `Transferencia` con todos
sus `TransferenciaItem`. Cambiar la ubicación de trabajo vacía el envío, porque los
disponibles eran de otro origen.

**Por qué:** el remito es la unidad real: «esto le mandé al local Centro el martes». Una
transferencia por producto llenaría el historial de ruido y no se podría reconstruir el envío.

## Pendientes

### REQ-TRF-006 · Ver el historial de transferencias en la app
**Estado:** pendiente

Se consulta solo desde el panel de Django. Falta el listado con origen, destino, fecha, quién
la hizo y sus ítems. Su lugar natural es la pantalla de Stock
([REQ-STK-013](03-stock.md#req-stk-013--todo-el-stock-se-opera-desde-una-sola-pantalla)): hoy
el «Recién hecho» muestra los envíos de la sesión, pero se pierden al recargar.
