// Utilidades compartidas por las pantallas (POS, stock, jornada).
window.SK = {
  // Importe con formato argentino, sin el signo $: 1234.5 → "1.234,50".
  // Es el mismo formato que el filtro `|plata` del servidor.
  fmt(n) {
    return Number(n || 0).toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  },

  csrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : "";
  },

  // POST JSON; si la respuesta no es OK, tira un Error con el mensaje del servidor.
  async post(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": SK.csrf() },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || "Ocurrió un error.");
    return data;
  },

  // El lector teclea como un teclado. Si el foco quedó fuera de un campo (por ejemplo,
  // en un botón −/+ recién clickeado), el escaneo se perdería y su Enter activaría ese
  // botón. Esto manda cualquier tecla imprimible al campo de escaneo.
  // `campo()` devuelve el input; `activo()` dice si la pantalla está esperando escaneos.
  capturarLector(campo, activo) {
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey || e.key.length !== 1) return;
      const t = e.target;
      if (t && (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName))) return;
      const input = campo();
      if (!input || input.disabled || (activo && !activo())) return;
      input.focus();  // la tecla en curso cae en el campo que acaba de tomar el foco
    });
  },
};
