// Cliente de tiempo real: abre un WebSocket al grupo del punto y reconecta solo.
window.SKRealtime = {
  connect(puntoId, onEvent) {
    if (!puntoId) return () => {};
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}/ws/punto/${puntoId}/`;
    let socket;
    let cerrado = false;
    const abrir = () => {
      socket = new WebSocket(url);
      socket.onmessage = (e) => {
        try { onEvent(JSON.parse(e.data)); } catch (_) {}
      };
      socket.onclose = () => { if (!cerrado) setTimeout(abrir, 2000); };
    };
    abrir();
    return () => { cerrado = true; if (socket) socket.close(); };
  },
};
