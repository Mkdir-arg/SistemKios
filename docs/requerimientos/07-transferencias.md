# Transferencias

### REQ-TRF-001 · Las transferencias mueven stock entre puntos y las hace el Super Admin
**Estado:** implementado · **Dónde:** [transferencias/views.py](../../apps/transferencias/views.py), [transferencias/urls.py](../../apps/transferencias/urls.py)

`/transferencias/nueva/`, con lector. La pantalla y los endpoints JSON rechazan a cualquiera
que no sea Super Admin (403 en los JSON).

**Por qué:** repartir mercadería es una decisión del dueño, no del que atiende. Si el vendedor
pudiera sacarse stock de encima, el control se pierde.

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
**Estado:** implementado · **Dónde:** [transferencias/views.py](../../apps/transferencias/views.py)

`/transferencias/buscar/` exige el punto de origen elegido y devuelve nombre, código y stock
en ese origen.

**Por qué:** es el número que decide cuánto se puede mandar.

## Pendientes

### REQ-TRF-006 · Ver el historial de transferencias en la app
**Estado:** pendiente

Se consulta solo desde el panel de Django. Falta el listado con origen, destino, fecha, quién
la hizo y sus ítems.
