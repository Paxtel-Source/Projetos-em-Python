"use strict";

// =========================================================
// Chat em tempo real: front-end em JavaScript puro
// Fala com o servidor por WebSocket, trocando mensagens JSON.
// =========================================================

const $ = (seletor) => document.querySelector(seletor);

const estado = {
  ws: null,
  apelido: "",
  sala: "geral",
  dentro: false,          // já recebeu o "bem_vindo" do servidor?
  reconectando: false,
  tentativas: 0,
  ultimoDigitando: 0,
  digitando: new Map(),   // apelido -> timer que apaga o aviso
  naoLidas: 0,
};

// ---------- Utilidades ----------

function guardar(chave, valor) {
  try { localStorage.setItem(chave, valor); } catch { /* navegador sem armazenamento */ }
}

function ler(chave) {
  try { return localStorage.getItem(chave) || ""; } catch { return ""; }
}

function hora(iso) {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

// Cada apelido ganha sempre a mesma cor
function corDoApelido(apelido) {
  let soma = 0;
  for (const letra of apelido.toLowerCase()) soma = (soma * 31 + letra.codePointAt(0)) % 360;
  return `hsl(${soma} 65% 68%)`;
}

function criar(tag, classe, texto) {
  const el = document.createElement(tag);
  if (classe) el.className = classe;
  if (texto !== undefined) el.textContent = texto;   // textContent: nunca interpreta HTML
  return el;
}

// ---------- Conexão ----------

function conectar() {
  const protocolo = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocolo}://${location.host}/ws`);
  estado.ws = ws;
  mostrarStatus("conectando", "conectando…");

  ws.addEventListener("open", () => {
    enviar({ tipo: "entrar", apelido: estado.apelido, sala: estado.sala });
  });

  ws.addEventListener("message", (evento) => tratar(JSON.parse(evento.data)));

  ws.addEventListener("close", () => {
    if (estado.ws !== ws) return;               // conexão antiga, já substituída
    estado.dentro = false;
    if (!estado.reconectando && $("#tela-chat").hidden) return;   // ainda na tela de entrada
    reconectarDepois();
  });
}

function reconectarDepois() {
  estado.reconectando = true;
  const espera = Math.min(1000 * 2 ** estado.tentativas, 15000);   // 1s, 2s, 4s... até 15s
  estado.tentativas += 1;
  mostrarStatus("desconectado", `sem conexão, tentando em ${Math.round(espera / 1000)}s`);
  setTimeout(conectar, espera);
}

function enviar(dados) {
  if (estado.ws && estado.ws.readyState === WebSocket.OPEN) {
    estado.ws.send(JSON.stringify(dados));
    return true;
  }
  return false;
}

function mostrarStatus(tipo, texto) {
  const status = $("#status");
  status.dataset.estado = tipo;
  status.textContent = texto;
}

// ---------- Mensagens que chegam do servidor ----------

function tratar(msg) {
  switch (msg.tipo) {
    case "bem_vindo": return aoEntrar(msg);
    case "mensagem": return adicionarMensagem(msg);
    case "sistema": return adicionarSistema(msg.texto);
    case "usuarios": return mostrarPessoas(msg.usuarios);
    case "salas": return mostrarSalas(msg.salas);
    case "digitando": return alguemDigitando(msg.apelido);
    case "erro": return mostrarErro(msg.texto);
  }
}

function aoEntrar(msg) {
  const primeiraVez = !estado.dentro && !estado.reconectando;
  estado.dentro = true;
  estado.reconectando = false;
  estado.tentativas = 0;
  estado.apelido = msg.apelido;
  estado.sala = msg.sala;
  guardar("chat-apelido", msg.apelido);
  history.replaceState(null, "", `#${msg.sala}`);

  $("#tela-entrada").hidden = true;
  $("#tela-chat").hidden = false;
  $("#meu-apelido").textContent = msg.apelido;
  $("#nome-sala").textContent = `#${msg.sala}`;
  document.title = `#${msg.sala} · Chat`;
  mostrarStatus("conectado", "conectado");
  fecharLateral();

  const lista = $("#mensagens");
  lista.replaceChildren();
  estado.digitando.forEach(clearTimeout);
  estado.digitando.clear();
  atualizarDigitando();

  if (msg.historico.length) {
    lista.append(criar("li", "divisor", "mensagens anteriores"));
    msg.historico.forEach(adicionarMensagem);
  }
  adicionarSistema(primeiraVez ? `Você entrou em #${msg.sala}.` : `Você está em #${msg.sala}.`);
  mostrarPessoas(msg.usuarios);
  $("#campo-mensagem").focus();
}

function adicionarMensagem(msg) {
  const lista = $("#mensagens");
  const pertoDoFim = lista.scrollHeight - lista.scrollTop - lista.clientHeight < 80;
  const minha = msg.apelido === estado.apelido;

  // Mensagens seguidas da mesma pessoa (em até 3 min) ficam agrupadas
  const anterior = lista.lastElementChild;
  const continuacao = anterior && anterior.dataset.apelido === msg.apelido &&
    new Date(msg.horario) - new Date(anterior.dataset.horario) < 3 * 60 * 1000;

  const item = criar("li", "msg");
  item.dataset.apelido = msg.apelido;
  item.dataset.horario = msg.horario;
  item.classList.toggle("minha", minha);
  item.classList.toggle("continuacao", Boolean(continuacao));
  item.style.setProperty("--cor", corDoApelido(msg.apelido));

  if (!continuacao) {
    const avatar = criar("span", "avatar", msg.apelido[0].toUpperCase());
    avatar.setAttribute("aria-hidden", "true");
    const topo = criar("div", "msg-topo");
    topo.append(criar("span", "autor", minha ? "você" : msg.apelido));
    const quando = criar("time", "", hora(msg.horario));
    quando.dateTime = msg.horario;
    topo.append(quando);
    item.append(avatar, topo);
  }
  item.append(criar("p", "texto", msg.texto));
  lista.append(item);

  if (pertoDoFim || minha) lista.scrollTop = lista.scrollHeight;
  removerDigitando(msg.apelido);

  if (document.hidden && !minha) {
    estado.naoLidas += 1;
    document.title = `(${estado.naoLidas}) #${estado.sala} · Chat`;
  }
}

function adicionarSistema(texto) {
  const lista = $("#mensagens");
  lista.append(criar("li", "sistema", texto));
  lista.scrollTop = lista.scrollHeight;
}

function mostrarPessoas(apelidos) {
  $("#total-pessoas").textContent = apelidos.length;
  const lista = $("#lista-pessoas");
  lista.replaceChildren(...apelidos.map((apelido) => {
    const item = criar("li", "", apelido === estado.apelido ? `${apelido} (você)` : apelido);
    item.style.setProperty("--cor", corDoApelido(apelido));
    return item;
  }));
}

function mostrarSalas(salas) {
  const lista = $("#lista-salas");
  lista.replaceChildren(...salas.map(({ nome, pessoas }) => {
    const botao = criar("button", "sala");
    botao.type = "button";
    botao.append(criar("span", "", `#${nome}`), criar("span", "contador", pessoas));
    if (nome === estado.sala) botao.setAttribute("aria-current", "true");
    botao.addEventListener("click", () => trocarSala(nome));
    const item = criar("li");
    item.append(botao);
    return item;
  }));
}

function mostrarErro(texto) {
  if (!estado.dentro) {
    if (estado.reconectando) {
      // Ao reconectar, o servidor pode ainda não ter percebido a queda da conexão antiga
      estado.ws.close();
      return;
    }
    const erro = $("#erro-entrada");
    erro.textContent = texto;
    erro.hidden = false;
    $("#botao-entrar").disabled = false;
    estado.ws.close();
    return;
  }
  const aviso = $("#aviso");
  aviso.textContent = texto;
  aviso.hidden = false;
  clearTimeout(mostrarErro.timer);
  mostrarErro.timer = setTimeout(() => { aviso.hidden = true; }, 4000);
}

// ---------- "Fulano está digitando…" ----------

function alguemDigitando(apelido) {
  clearTimeout(estado.digitando.get(apelido));
  estado.digitando.set(apelido, setTimeout(() => removerDigitando(apelido), 3000));
  atualizarDigitando();
}

function removerDigitando(apelido) {
  if (!estado.digitando.has(apelido)) return;
  clearTimeout(estado.digitando.get(apelido));
  estado.digitando.delete(apelido);
  atualizarDigitando();
}

function atualizarDigitando() {
  const nomes = [...estado.digitando.keys()];
  let texto = "";
  if (nomes.length === 1) texto = `${nomes[0]} está digitando…`;
  else if (nomes.length === 2) texto = `${nomes[0]} e ${nomes[1]} estão digitando…`;
  else if (nomes.length > 2) texto = "Várias pessoas estão digitando…";
  $("#digitando").textContent = texto;
}

// ---------- Ações da pessoa ----------

function trocarSala(nome) {
  if (nome !== estado.sala) enviar({ tipo: "trocar_sala", sala: nome });
  fecharLateral();
}

function abrirLateral() {
  $("#lateral").classList.add("aberta");
  $("#fundo-lateral").hidden = false;
}

function fecharLateral() {
  $("#lateral").classList.remove("aberta");
  $("#fundo-lateral").hidden = true;
}

$("#form-entrada").addEventListener("submit", (evento) => {
  evento.preventDefault();
  estado.apelido = $("#campo-apelido").value.trim();
  estado.sala = $("#campo-sala").value;
  $("#erro-entrada").hidden = true;
  $("#botao-entrar").disabled = true;
  conectar();
});

$("#form-mensagem").addEventListener("submit", (evento) => {
  evento.preventDefault();
  const campo = $("#campo-mensagem");
  const texto = campo.value.trim();
  if (!texto) return;
  if (enviar({ tipo: "mensagem", texto })) {
    campo.value = "";
    estado.ultimoDigitando = 0;   // a próxima tecla já avisa que voltou a digitar
  }
});

$("#campo-mensagem").addEventListener("input", (evento) => {
  // Avisa que está digitando, no máximo uma vez a cada 2,5 segundos
  const agora = Date.now();
  if (evento.target.value.trim() && agora - estado.ultimoDigitando > 2500) {
    estado.ultimoDigitando = agora;
    enviar({ tipo: "digitando" });
  }
});

$("#form-sala").addEventListener("submit", (evento) => {
  evento.preventDefault();
  const campo = $("#campo-nova-sala");
  const nome = campo.value.trim().toLowerCase().replace(/\s+/g, "-");
  if (!nome) return;
  trocarSala(nome);
  campo.value = "";
});

$("#botao-menu").addEventListener("click", abrirLateral);
$("#fundo-lateral").addEventListener("click", fecharLateral);

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && estado.dentro) {
    estado.naoLidas = 0;
    document.title = `#${estado.sala} · Chat`;
  }
});

// ---------- Início ----------

$("#campo-apelido").value = ler("chat-apelido");
const salaDoEndereco = decodeURIComponent(location.hash.slice(1));
if (salaDoEndereco) {
  const opcao = [...$("#campo-sala").options].find((o) => o.value === salaDoEndereco);
  if (!opcao) $("#campo-sala").add(new Option(`#${salaDoEndereco}`, salaDoEndereco));
  $("#campo-sala").value = salaDoEndereco;
}
$("#campo-apelido").focus();
