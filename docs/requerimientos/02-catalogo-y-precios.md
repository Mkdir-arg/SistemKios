# Catálogo y precios

## Producto

### REQ-CAT-001 · El catálogo de productos es común a todos los puntos
**Estado:** implementado · **Dónde:** [catalogo/models.py](../../apps/catalogo/models.py)

Un `Producto` existe una sola vez para todo el negocio (nombre, categoría, costo de
referencia, alícuota de IVA, imagen, activo). Lo que cambia por punto es el **precio**
([REQ-CAT-005](#req-cat-005--el-precio-por-punto-se-carga-como-margen--sobre-el-precio-base)) y el
**stock** ([REQ-STK-001](03-stock.md#req-stk-001--el-stock-se-lleva-por-producto-y-punto)).

**Por qué:** el mismo alfajor no se carga tres veces. Si se cargara por punto, un cambio de
nombre o de código habría que hacerlo N veces.

### REQ-CAT-002 · La categoría es opcional y se puede crear al vuelo
**Estado:** implementado · **Dónde:** [catalogo/forms.py](../../apps/catalogo/forms.py), [catalogo/views.py](../../apps/catalogo/views.py)

El formulario de producto tiene un campo «…o crear nueva categoría» que hace
`get_or_create` sobre `Categoria`. Un producto sin categoría es válido.

**Por qué:** obligar a definir el árbol de categorías antes de cargar el primer producto
frena la carga inicial, que es cuando el sistema tiene que ser más liviano.

### REQ-CAT-003 · Un producto puede tener varios códigos de barras y uno es el principal
**Estado:** implementado · **Dónde:** [catalogo/models.py](../../apps/catalogo/models.py), [catalogo/views.py](../../apps/catalogo/views.py)

`CodigoBarras.codigo` es único en todo el sistema. El primero de la lista queda como
`principal=True` (es el que se muestra en listados). Al guardar, los códigos que se
sacaron del formulario se borran y los nuevos se crean; si un código ya lo usa otro
producto, el guardado se rechaza con el mensaje del código en conflicto.

**Por qué:** el mismo producto viene con código de unidad y de pack, y a veces cambia de
código entre lotes. Escanear cualquiera tiene que encontrarlo.

### REQ-CAT-004 · La imagen del producto se reduce al subirla
**Estado:** implementado · **Dónde:** [catalogo/views.py](../../apps/catalogo/views.py)

Si el lado más largo supera 800 px, se redimensiona con Pillow al guardar. Si el archivo no
se puede procesar, el guardado sigue igual (no rompe el alta).

**Por qué:** las fotos salen del celular y pesan varios MB; el POS y el stock las muestran
en miniatura. Y una foto que falla no puede impedir cargar el producto.

## Precios

### REQ-CAT-005 · El precio por punto se carga como margen % sobre el precio base
**Estado:** implementado · **Dónde:** [catalogo/models.py](../../apps/catalogo/models.py), [catalogo/views.py](../../apps/catalogo/views.py)

- `precio_base` = costo + IVA (propiedad del producto).
- En el formulario se carga un **margen %** por punto y el precio final se calcula solo:
  `precio_con_margen(base, margen)`.
- El precio que llega del navegador se ignora: se recalcula en el servidor
  ([REQ-GEN-009](00-generales.md#req-gen-009--el-navegador-no-decide-ningún-número)).
- Si el margen deja el precio en negativo, el guardado se rechaza.

**Por qué:** el dueño piensa en «cuánto le gano», no en el precio final. Y cuando cambia el
costo del proveedor quiere que los precios se muevan solos.

### REQ-CAT-006 · Un producto sin costo mantiene el precio que se le cargó a mano
**Estado:** implementado · **Dónde:** [catalogo/views.py](../../apps/catalogo/views.py)

Si el producto no tiene costo, no hay base sobre la que aplicar margen: se respeta el
precio tipeado y se guarda el margen que resulte (`margen_desde_precio`).

**Por qué:** hay productos que se cargan apurados, sin costo, y tienen que poder venderse igual.

### REQ-CAT-007 · Sin precio en un punto, el producto no se vende ahí
**Estado:** implementado · **Dónde:** [catalogo/views.py](../../apps/catalogo/views.py), [ventas/views.py](../../apps/ventas/views.py)

`PrecioPunto` es único por (producto, punto). Si el formulario deja el precio vacío para un
punto, el `PrecioPunto` de ese punto **se borra**. Al escanearlo en el POS de ese punto, el
sistema responde con error explícito («no tiene precio en …») en vez de mandarlo al carrito
en $0.

**Por qué:** una venta en $0 es plata perdida y sin rastro. Mejor trabar el escaneo y que
alguien cargue el precio.

## Servicios

### REQ-CAT-008 · Un producto puede ser un servicio: se cobra pero no lleva stock
**Estado:** implementado · **Dónde:** [catalogo/models.py](../../apps/catalogo/models.py), [ofertas/services.py](../../apps/ofertas/services.py)

`Producto.es_servicio=True` marca recargas, SUBE y similares. Un servicio:

- **no tiene `PrecioPunto`**: el vendedor ingresa el monto en el momento;
- su precio de venta es **monto ingresado + `costo`**, donde el `costo` es la comisión que
  gana el local;
- **no descuenta stock** al venderse ([REQ-VEN-008](05-ventas-pos.md#req-ven-008--los-servicios-no-descuentan-stock));
- no aparece en la tabla de stock ni se puede ingresar mercadería de él
  ([REQ-STK-008](03-stock.md#req-stk-008--los-servicios-quedan-afuera-del-stock)).

**Por qué:** una recarga de $2000 con $100 de comisión es una venta real que tiene que
entrar a la caja, pero no es mercadería: no se compra, no se transfiere y no se cuenta.

## ABM

### REQ-CAT-009 · Los productos los administra solo el Super Admin
**Estado:** implementado · **Dónde:** [catalogo/views.py](../../apps/catalogo/views.py)

`/productos/` con alta, edición y baja, todo detrás de `super_admin_required`. La excepción
es el **alta rápida** desde la pantalla de stock, que también puede hacer un vendedor
([REQ-STK-006](03-stock.md#req-stk-006--se-puede-dar-de-alta-un-producto-desde-el-lector)).

### REQ-CAT-010 · Borrar un producto con historial lo desactiva
**Estado:** implementado · **Dónde:** [catalogo/views.py](../../apps/catalogo/views.py)

Ver [REQ-GEN-010](00-generales.md#req-gen-010--el-historial-no-se-pisa). El `ProtectedError`
se captura y se transforma en `activo=False` con un mensaje que explica qué pasó.
