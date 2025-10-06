async function updatePanels() {
  const tacPretty = document.getElementById("tac-pretty");
  const logs = document.getElementById("runtime-logs");

  try {
    const tacResp = await fetch("/tac");
    tacPretty.textContent = await tacResp.text();
    console.log(tacPretty.textContent);

    const logResp = await fetch("/logs");
    logs.textContent = await logResp.text();
    console.log(logResp.textContent);
  } catch (err) {
    console.error("Error actualizando paneles:", err);
  }
}

// refrescar cada 2 segundos
setInterval(updatePanels, 2000);
updatePanels();
