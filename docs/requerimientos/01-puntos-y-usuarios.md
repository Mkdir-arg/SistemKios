# Puntos y usuarios

Ver también [REQ-GEN-001](00-generales.md#req-gen-001--el-negocio-son-varios-puntos-independientes) (multi-punto),
[REQ-GEN-002](00-generales.md#req-gen-002--el-depósito-es-un-punto-especial-y-hay-uno-solo) (Depósito) y
[REQ-GEN-003](00-generales.md#req-gen-003--solo-dos-roles-super-admin-y-vendedor) (roles).

## Puntos

### REQ-PTO-001 · El Super Admin administra los puntos desde la app
**Estado:** implementado · **Dónde:** [puntos/views.py](../../apps/puntos/views.py), [puntos/urls.py](../../apps/puntos/urls.py)

Alta y edición en `/puntos/` y `/puntos/nuevo/` y `/puntos/<pk>/editar/`. Campos: nombre,
dirección (opcional) y activo. El listado muestra cuántos vendedores tiene cada punto.

**Por qué:** abrir un local no puede depender de que alguien entre al panel de Django.

### REQ-PTO-002 · Un punto no se borra, se desactiva
**Estado:** implementado · **Dónde:** [puntos/views.py](../../apps/puntos/views.py)

No hay acción de borrado. Un punto con `activo=False` desaparece de los selectores de
usuarios, transferencias, precios y stock, pero su historial de ventas y movimientos
sigue existiendo.

**Por qué:** mismo criterio que [REQ-GEN-010](00-generales.md#req-gen-010--el-historial-no-se-pisa): el pasado no se toca.

### REQ-PTO-003 · Cada punto tiene su canal de tiempo real
**Estado:** implementado · **Dónde:** [puntos/models.py](../../apps/puntos/models.py)

`Punto.grupo_ws` devuelve `punto_{id}`, el nombre del grupo de WebSocket del punto.
Detalle en [REQ-RT-001](09-tiempo-real.md#req-rt-001--cada-punto-tiene-un-canal-en-vivo).

## Usuarios y acceso

### REQ-USR-001 · El Super Admin crea y edita usuarios desde la app
**Estado:** implementado · **Dónde:** [accounts/views.py](../../apps/accounts/views.py), [accounts/forms.py](../../apps/accounts/forms.py)

`/usuarios/`, `/usuarios/nuevo/`, `/usuarios/<pk>/editar/`. Campos: usuario, nombre,
apellido, rol, punto, contraseña y activo. No hay borrado: se desactiva con `is_active`.

### REQ-USR-002 · Un vendedor necesita un punto; el Super Admin no tiene ninguno
**Estado:** implementado · **Dónde:** [accounts/forms.py](../../apps/accounts/forms.py), [accounts/models.py](../../apps/accounts/models.py)

El formulario rechaza guardar un vendedor sin punto. Al Super Admin el punto se le deja en
blanco (y si además es superusuario de Django, `save()` lo fuerza a `None`). El selector de
punto solo lista puntos activos.

**Por qué:** el punto del vendedor es lo que determina qué stock ve, con qué precios vende
y en qué caja entra la plata. Sin punto no puede trabajar.

### REQ-USR-003 · La contraseña es obligatoria al crear y opcional al editar
**Estado:** implementado · **Dónde:** [accounts/forms.py](../../apps/accounts/forms.py)

En edición, dejarla vacía no la cambia. Se guarda con `set_password`.

**Por qué:** cambiarle el nombre o el punto a un vendedor no debería obligar a reasignarle
la clave.

### REQ-USR-004 · Se entra por `/ingresar/` y el sistema decide a dónde va cada rol
**Estado:** implementado · **Dónde:** [accounts/views.py](../../apps/accounts/views.py), [core/views.py](../../apps/core/views.py)

Login en `/ingresar/`, salida en `/salir/`. El dashboard (`/`) se arma según el rol: el
Super Admin ve los puntos activos y los módulos de administración; el vendedor ve su punto
y sus tres accesos (vender, stock, mi jornada). Los mensajes de error del login están en
español y no distinguen si falló el usuario o la contraseña.

### REQ-USR-005 · Las pantallas de administración rechazan al vendedor con un mensaje, no con un 403
**Estado:** implementado · **Dónde:** [core/decorators.py](../../apps/core/decorators.py)

`super_admin_required` manda al vendedor al inicio con un aviso («Necesitás permisos de
administrador para eso»). Los endpoints JSON de administración sí devuelven 403
([transferencias/views.py](../../apps/transferencias/views.py)).

**Por qué:** el vendedor está atendiendo gente; una pantalla de error de Django lo trabaría.
En cambio un endpoint JSON lo consume el propio front, y ahí el código HTTP es lo útil.
