// Botão "Copiar protocolo"
document.querySelectorAll("[data-copiar]").forEach(function (btn) {
  btn.addEventListener("click", function () {
    const texto = btn.getAttribute("data-copiar");
    const ok = () => { btn.textContent = "✓ Copiado"; };
    if (navigator.clipboard) navigator.clipboard.writeText(texto).then(ok);
  });
});
