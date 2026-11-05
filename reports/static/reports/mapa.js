// RF07 – mapa das demandas no painel (Leaflet + OpenStreetMap)
document.addEventListener("DOMContentLoaded", function () {
  const el = document.getElementById("mapa");
  const dados = document.getElementById("pontos-mapa");
  if (!el || !dados || !window.L) return;
  const pontos = JSON.parse(dados.textContent);
  const mapa = L.map(el).setView([-2.53, -44.15], 15);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(mapa);
  const marcas = pontos.map(function (p) {
    const m = L.circleMarker([p.lat, p.lon], { radius: 9, color: p.cor, fillOpacity: 0.85 }).addTo(mapa);
    const link = document.createElement("a");
    link.href = p.url;
    link.textContent = p.titulo;
    m.bindPopup(link);
    return m;
  });
  if (marcas.length) mapa.fitBounds(L.featureGroup(marcas).getBounds().pad(0.3));
});
