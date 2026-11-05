// Registro do problema: localização, prévia/compressão da foto e contador (RF01, RNF03)
(function () {
  const botao = document.getElementById("usar-localizacao");
  const status = document.getElementById("status-localizacao");
  const lat = document.getElementById("id_latitude");
  const lon = document.getElementById("id_longitude");

  if (botao) {
    if (lat && lat.value) status.textContent = "✓ Localização marcada.";
    botao.addEventListener("click", function () {
      if (!navigator.geolocation) {
        status.textContent = "Seu celular não permite pegar a localização. Escreva a rua e um ponto de referência.";
        return;
      }
      status.textContent = "Buscando sua localização…";
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          lat.value = pos.coords.latitude.toFixed(6);
          lon.value = pos.coords.longitude.toFixed(6);
          status.textContent = "✓ Localização marcada.";
        },
        function () {
          status.textContent = "⚠ Não foi possível pegar a localização. Escreva a rua e um ponto de referência.";
        },
        { enableHighAccuracy: true, timeout: 15000 }
      );
    });
  }

  const desc = document.getElementById("id_descricao");
  const contador = document.getElementById("contador");
  if (desc && contador) {
    const atualizar = () => (contador.textContent = desc.value.length);
    desc.addEventListener("input", atualizar);
    atualizar();
  }

  // Comprime a foto no celular antes do envio (lado maior até 1280 px)
  const foto = document.getElementById("id_foto");
  const previa = document.getElementById("previa-foto");
  if (foto && window.DataTransfer && window.HTMLCanvasElement) {
    foto.addEventListener("change", function () {
      const arquivo = foto.files[0];
      if (!arquivo || !arquivo.type.startsWith("image/")) return;
      const img = new Image();
      img.onload = function () {
        const max = 1280;
        const escala = Math.min(1, max / Math.max(img.width, img.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * escala);
        canvas.height = Math.round(img.height * escala);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function (blob) {
          if (!blob) return;
          const dt = new DataTransfer();
          dt.items.add(new File([blob], "foto.jpg", { type: "image/jpeg" }));
          foto.files = dt.files;
          previa.src = URL.createObjectURL(blob);
          previa.hidden = false;
        }, "image/jpeg", 0.8);
        URL.revokeObjectURL(img.src);
      };
      img.src = URL.createObjectURL(arquivo);
    });
  }
})();
