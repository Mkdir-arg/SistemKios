// Cliente de tiempo real: Supabase Realtime, canales privados `punto-{id}`.
// Django entrega la config y un token (/tiempo-real/token/) que solo deja escuchar los
// puntos que el usuario puede ver. supabase-js reconecta solo si se corta la conexión.
//
// Eventos que recibe `onEvent`: los de negocio ({tipo: "stock" | "venta" | "jornada", ...})
// y los de estado: "conectado", "desconectado" y "sin_tiempo_real" (no hay Supabase configurado).
window.SKRealtime = (function () {
  const URL_TOKEN = "/tiempo-real/token/";
  const URL_SDK = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js";
  const MARGEN_MS = 2 * 60 * 1000;  // renueva el token 2 minutos antes de que venza
  let promesaCliente = null;

  async function pedirConfig() {
    const r = await fetch(URL_TOKEN, { credentials: "same-origin", cache: "no-store" });
    if (!r.ok) throw new Error("No se pudo obtener el token de tiempo real (" + r.status + ").");
    return r.json();
  }

  function cargarSdk() {
    if (window.supabase) return Promise.resolve();
    return new Promise((resolver, rechazar) => {
      const s = document.createElement("script");
      s.src = URL_SDK;
      s.onload = resolver;
      s.onerror = () => rechazar(new Error("No se pudo cargar supabase-js."));
      document.head.appendChild(s);
    });
  }

  // Un solo cliente por página, compartido por todos los canales.
  function cliente() {
    if (!promesaCliente) {
      promesaCliente = (async () => {
        const config = await pedirConfig();
        if (!config.habilitado) return null;
        await cargarSdk();
        let token = config.token;
        let vence = Date.now() + config.vence_en * 1000 - MARGEN_MS;
        const c = window.supabase.createClient(config.url, config.anon_key, {
          // Realtime lo vuelve a pedir en cada reconexión: si está por vencer, se renueva.
          accessToken: async () => {
            if (Date.now() > vence) {
              const nueva = await pedirConfig();
              token = nueva.token;
              vence = Date.now() + nueva.vence_en * 1000 - MARGEN_MS;
            }
            return token;
          },
        });
        await c.realtime.setAuth(token);
        return c;
      })().catch((e) => {
        promesaCliente = null;  // el próximo connect() vuelve a intentar
        throw e;
      });
    }
    return promesaCliente;
  }

  return {
    connect(puntoId, onEvent) {
      if (!puntoId) return () => {};
      let canal = null;
      let cerrado = false;
      cliente()
        .then((c) => {
          if (cerrado) return;
          if (!c) { onEvent({ tipo: "sin_tiempo_real" }); return; }
          canal = c
            .channel("punto-" + puntoId, { config: { private: true } })
            .on("broadcast", { event: "*" }, (msg) => onEvent(msg.payload))
            .subscribe((estado) => {
              if (estado === "SUBSCRIBED") onEvent({ tipo: "conectado", punto_id: puntoId });
              else onEvent({ tipo: "desconectado", estado });
            });
        })
        .catch(() => onEvent({ tipo: "desconectado" }));
      return () => {
        cerrado = true;
        if (canal) canal.unsubscribe();
      };
    },
  };
})();
