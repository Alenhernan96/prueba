let todasLasObras = [];

document.addEventListener("DOMContentLoaded", async function () {
  const diaInput = document.getElementById("dia");
  const mesInput = document.getElementById("mes");
  const anioInput = document.getElementById("anio");
  const datalist = document.getElementById("obrasSociales");
  const obraInput = document.getElementById("obraSocial");
  const listaObras = document.getElementById("listaObras");

  // Precargar año actual
  if (anioInput) {
    const hoy = new Date();
    anioInput.value = hoy.getFullYear();
  }

  // Cargar lista de obras una vez
  try {
    const res = await fetch("/api/lista-obras");
    todasLasObras = await res.json();

    if (listaObras) {
      listaObras.innerHTML = "";
      todasLasObras.forEach((nombre) => {
        const div = document.createElement("div");
        div.textContent = nombre;
        div.classList.add("obra-social-item"); // Usá tu CSS personalizado
        div.style.cursor = "pointer";
        listaObras.appendChild(div);
      });

      // 🔹 Mostrar contador en el párrafo
      const p = document.querySelector(".requerimientos-listado p");
      if (p) {
        p.innerHTML = `Estas son las obras sociales actualmente disponibles en el sistema: <strong>${todasLasObras.length}</strong> obras sociales.`;
      }

      // Evento para completar input al hacer clic
      listaObras.addEventListener("click", (e) => {
        if (e.target && e.target.classList.contains("obra-social-item")) {
          obraInput.value = e.target.textContent.trim();

          // Evitar focus en móviles
          if (!/Mobi|Android/i.test(navigator.userAgent)) {
            obraInput.focus();
          }

          buscarRequisitos();
        }
      });
    }
  } catch (err) {
    console.error("No se pudo cargar la lista de obras sociales:", err);
    if (listaObras) {
      listaObras.innerHTML = `<div style="color: red;">❌ No se pudo cargar el listado.</div>`;
    }
  }
  // Autocompletado dinámico al tipear
  if (obraInput && datalist) {
    obraInput.addEventListener("input", () => {
      const valor = obraInput.value.trim().toUpperCase();
      datalist.innerHTML = "";

      if (valor.length >= 3) {
        const filtradas = todasLasObras.filter((nombre) =>
          nombre.toUpperCase().includes(valor)
        );

        filtradas.forEach((nombre) => {
          const option = document.createElement("option");
          option.value = nombre;
          datalist.appendChild(option);
        });
      }
    });

    obraInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && obraInput.value.trim().length >= 3) {
        e.preventDefault();
        buscarRequisitos();
      }
    });
  }

  // Teclas rápidas para avanzar entre campos
  if (diaInput) {
    diaInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && diaInput.value.length > 0) {
        e.preventDefault();
        mesInput?.focus();
      }
    });
  }

  if (mesInput) {
    mesInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && mesInput.value.length > 0) {
        e.preventDefault();
        anioInput?.focus();
      }
    });
  }

  if (anioInput) {
    anioInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && anioInput.value.length >= 4) {
        e.preventDefault();
        calcularCupon();
      }
    });
  }
});

async function calcularCupon() {
  const dia = document.getElementById("dia").value;
  const mes = document.getElementById("mes").value;
  const anio = document.getElementById("anio").value;
  const resultado = document.getElementById("resultado");

  resultado.innerHTML = `<div class="text-muted">⌛ Calculando...</div>`;

  const res = await fetch("/calcular-cupon", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dia, mes, anio }),
  });

  const data = await res.json();

  if (!res.ok) {
    resultado.innerHTML = `<div class="text-danger">❌ ${data.error}</div>`;
  } else {
    const cuponesNoValidos = data.no_validos
      .map((c) => `<div class="text-danger">❌ ${c}</div>`)
      .join("");

    resultado.innerHTML = `
      <div class="text-start">
        <div class="mb-2">📅 <strong>Fecha ingresada:</strong> ${data.fecha}</div>
        <div class="mb-2">🗓️ <strong>Días corridos:</strong> ${data.dias_corridos}</div>
        <div class="mb-2">💊 <strong style="color: green;">${data.cupon}</strong></div>
        ${cuponesNoValidos}
      </div>
    `;
  }
}

async function buscarRequisitos() {
  const obraInput = document.getElementById("obraSocial");
  const resultado = document.getElementById("resultadoRequisitos");

  if (!obraInput.value.trim()) {
    resultado.innerHTML = `<div class="text-danger">⚠️ Ingresá una obra social.</div>`;
    return;
  }

  resultado.innerHTML = `<div class="text-muted">⌛ Consultando requisitos...</div>`;

  const res = await fetch("/api/requisitos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ obra: obraInput.value }),
  });

  const data = await res.json();

  if (!res.ok) {
    resultado.innerHTML = `<div class="text-danger">❌ ${data.error}</div>`;
    return;
  }

  let html = `<h4 class="requerimientos-titulo">📄 Requisitos para <strong>${data.obra}</strong></h4>`;

  html += `<div class="requerimientos-scroll">
    <table class="requerimientos-tabla">
      <thead>
        <tr><th>Normativa</th><th>Respuesta</th></tr>
      </thead>
      <tbody>`;

  // Helpers
  const norm = (s) =>
    String(s || "")
      .toUpperCase()
      .trim();
  const aprobado = (v) =>
    v === "SI" || v === "T&S" || v === "DIRECTO" || v.includes("DIGITAL");

  // Detecta valores "de relleno" o vacíos
  const esVacioOUseless = (s) => {
    const t = String(s || "").trim();
    if (!t) return true;
    const up = t.toUpperCase();
    const basura = new Set([
      "...",
      "…",
      "-",
      "—",
      "N/A",
      "S/D",
      "NO APLICA",
      "SIN DATOS",
    ]);
    return basura.has(up);
  };

  // Mapeo de normativas -> emoji (usa includes, no exacto)
  function emojiPorNorma(norma, valor) {
    const n = norm(norma);
    const v = norm(valor);

    if (n.includes("DIGITAL")) return "💻"; // Formato/Receta digital
    if (n.includes("VALIDEZ")) return "📅"; // Días de vigencia
    if (n.includes("MONTO TOPE") || n.includes("TOPE")) return "💲"; // Límite $
    if (n.includes("TRATAMIENTO PROLONG")) return "⏳";
    if (n.includes("CANTIDAD")) return "🔢";
    if (n.includes("TROQUEL")) return "🏷️";
    if (n.includes("CORREGIR") || n.includes("ENMIENDA")) return "✏️";
    if (n.includes("CREDENCIAL") || n.includes("CUIL") || n.includes("DNI"))
      return "🪪";
    if (n.includes("RECETARIO") || n.includes("RECETA")) return "📜";
    if (n.includes("MANDATARIA") || n.includes("ENTIDAD")) return "🏢";
    if (n.includes("EMPRESA") || n.includes("NOMBRE DE LA EMPRESA"))
      return "🏢";
    if (n.includes("OTROS") || n.includes("OBSERVA")) return "📌";
    return aprobado(v) ? "✅" : "❌"; // Fallback
  }

  // 🔎 FILTRO: solo filas con contenido real en norma y valor
  const filasUtiles = (data.requisitos || []).filter((item) => {
    return !esVacioOUseless(item?.norma) && !esVacioOUseless(item?.valor);
  });

  if (filasUtiles.length === 0) {
    resultado.innerHTML = `
      ${html}
      <tr><td colspan="2" class="text-muted">Sin requisitos con contenido para mostrar.</td></tr>
      </tbody></table></div>`;
    return;
  }

  // Render de filas útiles
  filasUtiles.forEach((item) => {
    const valorUp = norm(item.valor);
    const icono = emojiPorNorma(item.norma, valorUp);

    // Para "monto tope" anteponer $ si no lo trae
    const mostrarValor =
      icono === "💲" && !/^[$€]/.test(String(item.valor).trim())
        ? `$ ${item.valor}`
        : item.valor;

    html += `
      <tr>
        <td>${item.norma}</td>
        <td><span class="req-ico">${icono}</span> ${String(mostrarValor)
      .toUpperCase()
      .trim()}</td>
      </tr>`;
  });

  html += `</tbody></table></div>`;
  resultado.innerHTML = html;
}

function abrirModalAyudaIOMA() {
  const modal = document.getElementById("modalAyudaIOMA");
  if (modal) modal.style.display = "block";
}

function cerrarModalAyudaIOMA() {
  const modal = document.getElementById("modalAyudaIOMA");
  if (modal) modal.style.display = "none";
}

window.addEventListener("click", function (event) {
  const modal = document.getElementById("modalAyudaIOMA");
  if (modal && event.target === modal) {
    modal.style.display = "none";
  }
});

// Modal personalizado: Guía de interpretación (Requisitos OS)
function abrirModalAyudaRequisitos() {
  document.getElementById("modalAyudaCustom").style.display = "block";
}

function cerrarModalAyudaRequisitos() {
  document.getElementById("modalAyudaCustom").style.display = "none";
}

window.addEventListener("click", function (event) {
  const modal = document.getElementById("modalAyudaCustom");
  if (event.target === modal) {
    modal.style.display = "none";
  }
});

// Descarga y reinicio tras procesamiento del archivo
function descargarYReiniciar(rutaZip) {
  const link = document.createElement("a");
  link.href = rutaZip;
  link.download = "";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  setTimeout(() => {
    window.location.href = "/galeno";
  }, 1000);
}

// Modal personalizado GALENO
function abrirModalInfoGaleno() {
  document.getElementById("modalInfoGaleno").style.display = "block";
}

function cerrarModalInfoGaleno() {
  document.getElementById("modalInfoGaleno").style.display = "none";
}

// Cerrar modal al hacer clic fuera de él
window.addEventListener("click", function (event) {
  const modal = document.getElementById("modalInfoGaleno");
  if (event.target === modal) {
    modal.style.display = "none";
  }
});

// Loader (todas las páginas)
window.addEventListener("load", function () {
  window.scrollTo(0, 0);
  const loaderWrapper = document.getElementById("loader-wrapper");
  if (loaderWrapper) {
    loaderWrapper.style.opacity = "0";
    setTimeout(() => {
      loaderWrapper.style.display = "none";
    }, 500);
  }
});

// Menú hamburguesa (todas las páginas)
document.addEventListener("DOMContentLoaded", () => {
  const menuToggle = document.getElementById("menuToggle");
  const menuContainer = document.getElementById("menuContainer");

  if (menuToggle && menuContainer) {
    menuToggle.addEventListener("click", () => {
      menuContainer.classList.toggle("activo");
    });
  }
});

// FAQ Toggle (faq.html)
document.addEventListener("DOMContentLoaded", () => {
  const botones = document.querySelectorAll(".faq-question");

  if (botones.length) {
    botones.forEach((btn) => {
      btn.addEventListener("click", () => {
        const item = btn.closest(".faq-item");
        const abierto = item.classList.contains("open");

        document.querySelectorAll(".faq-item").forEach((i) => {
          i.classList.remove("open");
          i.querySelector(".faq-question").classList.remove("active");
        });

        if (!abierto) {
          item.classList.add("open");
          btn.classList.add("active");
        }
      });
    });
  }
});

// Contacto (contacto.html)
document.addEventListener("DOMContentLoaded", () => {
  const formulario = document.getElementById("formulario-contacto");
  const spinner = document.getElementById("spinner");

  if (formulario) {
    formulario.addEventListener("submit", function (e) {
      e.preventDefault();

      const nombre = document.getElementById("nombre").value.trim();
      const email = document.getElementById("email").value.trim();
      const mensaje = document.getElementById("mensaje").value.trim();

      if (nombre.length < 5) {
        Swal.fire(
          "Error",
          "El nombre debe tener al menos 5 caracteres.",
          "error"
        );
        return;
      }

      if (!email.includes("@")) {
        Swal.fire(
          "Error",
          "El correo electrónico debe contener un @ válido.",
          "error"
        );
        return;
      }

      if (mensaje.length < 15) {
        Swal.fire(
          "Error",
          "El mensaje debe tener al menos 15 caracteres.",
          "error"
        );
        return;
      }

      if (spinner) spinner.style.display = "block";

      const formData = new FormData(formulario);

      fetch(formulario.getAttribute("action") || "/api/contacto", {
        method: "POST",
        body: formData,
      })
        .then((r) =>
          r
            .json()
            .catch(() => ({}))
            .then((j) => ({ ok: r.ok, ...j }))
        )
        .then(({ ok, error }) => {
          if (ok) {
            Swal.fire(
              "¡Gracias!",
              "Tu mensaje fue enviado correctamente.",
              "success"
            );
            formulario.reset();
          } else {
            Swal.fire(
              "Error",
              error || "No se pudo enviar el mensaje.",
              "error"
            );
          }
        })
        .catch(() => {
          Swal.fire(
            "Error",
            "Ocurrió un problema al enviar el formulario.",
            "error"
          );
        })
        .finally(() => {
          if (spinner) spinner.style.display = "none";
        });
    });
  }
});

// Home - Efecto de escritura y carruseles (index.html)
window.addEventListener("load", function () {
  const contenedor = document.getElementById("heroTextoEscritura");

  if (contenedor) {
    const escribirTexto = (elemento, texto, velocidad = 30, callback) => {
      let i = 0;
      const escribir = () => {
        if (i < texto.length) {
          elemento.innerHTML += texto.charAt(i);
          i++;
          setTimeout(escribir, velocidad);
        } else if (callback) callback();
      };
      escribir();
    };

    const h2 = document.createElement("h2");
    contenedor.appendChild(h2);
    escribirTexto(h2, "¡Bienvenido a Tecno CF!", 50, () => {
      const p = document.createElement("p");
      p.classList.add("subtitulo");
      contenedor.appendChild(p);
      escribirTexto(
        p,
        "Somos tu lugar de confianza para reparar, comprar y resolver todo lo que necesites en tecnología.",
        25,
        () => {
          contenedor.appendChild(document.createElement("br"));
          const ul = document.createElement("ul");
          ul.classList.add("confianza");
          contenedor.appendChild(ul);

          const items = [
            '<i class="fas fa-shield-alt"></i>La garantia de nuestros trabajos nos respalda',
            '<i class="fas fa-shipping-fast"></i>Envios a todo GBA',
            '<i class="fas fa-tools"></i>Más de 5 años de experiencia',
          ];

          const escribirItem = (index) => {
            if (index < items.length) {
              const li = document.createElement("li");
              li.innerHTML = items[index];
              ul.appendChild(li);
              setTimeout(() => escribirItem(index + 1), 400);
            } else {
              const a = document.createElement("a");
              const urlServicios =
                contenedor.dataset.urlServicios || "/servicios";
              a.href = urlServicios;
              a.className = "btn-ir-servicios";
              contenedor.appendChild(a);
              escribirTexto(a, "Conocé nuestros servicios", 30);
            }
          };

          escribirItem(0);
        }
      );
    });
  }

  // Carrusel testimonios
  const slidesTestimonios = document.querySelectorAll(".testimonios-slide");
  if (slidesTestimonios.length) {
    let current = 0;
    setInterval(() => {
      slidesTestimonios[current].classList.remove("activo");
      current = (current + 1) % slidesTestimonios.length;
      slidesTestimonios[current].classList.add("activo");
    }, 5000);
  }

  // Carrusel hero
  const heroSlides = document.querySelectorAll(".carrusel-hero .slide");
  if (heroSlides.length) {
    let current = 0;
    setInterval(() => {
      heroSlides[current].classList.remove("activo");
      current = (current + 1) % heroSlides.length;
      heroSlides[current].classList.add("activo");
    }, 4000);
  }
});

// Particles.js (index.html)
document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("particles-js")) {
    particlesJS("particles-js", {
      particles: {
        number: {
          value: 120, // ⬅️ Más partículas
          density: {
            enable: true,
            value_area: 800,
          },
        },
        color: {
          value: "#00ffc3", // Color neón
        },
        shape: {
          type: "circle",
          stroke: {
            width: 0,
            color: "#000000",
          },
        },
        opacity: {
          value: 0.5,
          random: false,
        },
        size: {
          value: 3,
          random: true,
        },
        line_linked: {
          enable: true,
          distance: 150,
          color: "#00ffc3",
          opacity: 0.3,
          width: 1,
        },
        move: {
          enable: true,
          speed: 2,
          direction: "none",
          straight: false,
          out_mode: "out",
        },
      },
      interactivity: {
        detect_on: "canvas",
        events: {
          onhover: { enable: false },
          onclick: { enable: false },
          resize: true,
        },
      },
      retina_detect: true,
    });
  }
});

// Mostrar logos de marcas con animación secuencial (sin scroll)
document.addEventListener("DOMContentLoaded", () => {
  const logos = document.querySelectorAll(".logos-marcas img");

  if (logos.length) {
    logos.forEach((logo, index) => {
      setTimeout(() => {
        logo.classList.remove("logo-escondido");
        logo.classList.add("logo-visible");
      }, index * 300);
    });
  }

  // Función reutilizable para sliders
  const iniciarSlider = (lista, idTarjeta, idTexto) => {
    const tarjeta = document.getElementById(idTarjeta);
    const parrafo = document.getElementById(idTexto);
    let index = 0;

    if (!tarjeta || !parrafo) return;

    const cambiar = () => {
      tarjeta.classList.remove("visible");
      setTimeout(() => {
        parrafo.textContent = lista[index];
        tarjeta.classList.add("visible");
        index = (index + 1) % lista.length;
      }, 400);
    };

    cambiar();
    setInterval(cambiar, 4000);
  };

  // Sliders por categoría
  iniciarSlider(
    [
      "Limpieza y mantenimiento / Cambio de fuente",
      "Cambio de placa / Cambio de pasta térmica",
      "Cambio de disco duro / Reparación de Joystick",
    ],
    "slider-consolas",
    "descripcion-consola"
  );

  iniciarSlider(
    [
      "Cambio de módulo / Cambio de pin de carga",
      "Cambio de batería / Actualización de software",
      "Problemas con la cámara / Problemas de audio",
    ],
    "slider-celulares",
    "descripcion-celular"
  );

  iniciarSlider(
    [
      "Actualización de hardware / Actualización de software",
      "Reparación de equipos / Formateo de equipos",
      "Mantenimiento y seguridad / Recuperación de datos",
    ],
    "slider-pc",
    "descripcion-pc"
  );
});

// Reseñas - Carrusel (reseñas.html)
document.addEventListener("DOMContentLoaded", () => {
  const slides = document.querySelectorAll(".reseña-slide");
  const dots = document.querySelectorAll(".reseña-dot");
  const prev = document.querySelector(".reseña-prev");
  const next = document.querySelector(".reseña-next");

  if (slides.length && dots.length && prev && next) {
    let current = 0;

    const mostrarSlide = (index) => {
      slides.forEach((slide, i) => {
        slide.classList.toggle("active", i === index);
        dots[i].classList.toggle("active", i === index);
      });
      current = index;
    };

    prev.addEventListener("click", () => {
      mostrarSlide((current - 1 + slides.length) % slides.length);
    });

    next.addEventListener("click", () => {
      mostrarSlide((current + 1) % slides.length);
    });

    dots.forEach((dot) => {
      dot.addEventListener("click", () => {
        mostrarSlide(Number(dot.dataset.index));
      });
    });

    setInterval(() => {
      mostrarSlide((current + 1) % slides.length);
    }, 7000);
  }
});

function rellenarFechaDesdeCalendario() {
  const fechaInput = document.getElementById("fecha_completa").value;
  if (!fechaInput) return;

  const [anio, mes, dia] = fechaInput.split("-");
  document.getElementById("dia").value = dia;
  document.getElementById("mes").value = mes;
  document.getElementById("anio").value = anio;
}

// Ajustar menú hamburguesa según el tamaño de pantalla
function ajustarMenuHamburguesa() {
  const menuContainer = document.getElementById("menuContainer");
  const menuToggle = document.getElementById("menuToggle");

  if (!menuContainer || !menuToggle) return;

  if (window.innerWidth >= 769) {
    menuContainer.classList.remove("active");
    menuToggle.style.display = "none";
  } else {
    menuToggle.style.display = "block";
  }
}

// ===== Prestadores (scoped) =====
window.Prestadores = (function () {
  const ids = {
    root: "prestadores-root",
    obra: "prestadores-obra",
    q: "prestadores-q",
    search: "prestadores-search",
    total: "prestadores-total",
    tbody: "prestadores-tbody",
    helpOpen: "prestadores-help-open",
    help: "prestadores-help",
    helpClose: "prestadores-help-close",
    helpOk: "prestadores-help-ok",
  };

  function el(id) {
    return document.getElementById(id);
  }

  async function buscar() {
    const obra = el(ids.obra).value;
    const q = el(ids.q).value || "";
    const tbody = el(ids.tbody);
    const totalEl = el(ids.total);
    const btn = el(ids.search);

    btn.disabled = true;
    const prev = btn.textContent;
    btn.textContent = "Buscando…";
    tbody.innerHTML = `<tr><td class="prestadores-nores" colspan="2">Buscando…</td></tr>`;

    try {
      const url = `/api/prestadores?obra=${encodeURIComponent(
        obra
      )}&q=${encodeURIComponent(q)}`;
      const res = await fetch(url);
      const data = await res.json();

      totalEl.textContent = `${data.total || 0} resultados`;

      if (!data.items || !data.items.length) {
        tbody.innerHTML = `<tr><td class="prestadores-nores" colspan="2">Sin resultados</td></tr>`;
        return;
      }

      tbody.innerHTML = data.items
        .map(
          (r) => `
        <tr>
          <td>${r.prestador ?? ""}</td>
          <td style="white-space:nowrap; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">
            ${r.matricula ?? ""}
          </td>
        </tr>
      `
        )
        .join("");
    } catch (e) {
      console.error(e);
      tbody.innerHTML = `<tr><td class="prestadores-nores" colspan="2" style="color:#ff6b6b">Error consultando. Probá de nuevo.</td></tr>`;
    } finally {
      btn.disabled = false;
      btn.textContent = prev;
    }
  }

  function openHelp() {
    el(ids.help).style.display = "block";
  }
  function closeHelp() {
    el(ids.help).style.display = "none";
  }

  function init() {
    if (!el(ids.root)) return; // no estoy en esta página

    el(ids.search).addEventListener("click", buscar);
    el(ids.q).addEventListener("keydown", (e) => {
      if (e.key === "Enter") buscar();
    });

    const open = el(ids.helpOpen),
      close = el(ids.helpClose),
      ok = el(ids.helpOk);
    if (open) open.addEventListener("click", openHelp);
    if (close) close.addEventListener("click", closeHelp);
    if (ok) ok.addEventListener("click", closeHelp);

    setTimeout(() => el(ids.q).focus(), 150);
  }

  return { init };
})();

// auto-init sin romper otras páginas
document.addEventListener("DOMContentLoaded", () => {
  if (window.Prestadores && typeof window.Prestadores.init === "function") {
    window.Prestadores.init();
  }
});

// static/script.js
document
  .getElementById("uploadForm")
  .addEventListener("submit", async function (event) {
    event.preventDefault();
    const fileInput = document.getElementById("recetaFile");
    if (fileInput.files.length === 0) {
      showError("Por favor, selecciona un archivo.");
      return;
    }

    // ESTA LÍNEA ES LA CLAVE: Captura todos los campos del formulario automáticamente
    const formData = new FormData(event.target);

    setLoadingState(true);
    try {
      const response = await fetch("/extract", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(
          result.error || `Error del servidor: ${response.statusText}`
        );
      renderResults(result);
    } catch (error) {
      showError(`Ha ocurrido un error:\n\n${error.message}`);
    } finally {
      setLoadingState(false); // Finaliza el estado de carga
    }
  });

function renderResults(data) {
  const container = document.getElementById("results-display");
  document.getElementById("json-output").style.display = "none";

  const validation = data.validacion_normativa || {};
  const iaData = data.datos_extraidos_ia || {};
  const ticketData = data.datos_extraidos_ticket || {};
  const comparisonData = data.comparacion_con_ticket || null;
  const barcodeData = data.verificacion_vademecum || [];

  const statusMap = {
    CUMPLE: {
      class: "status-cumple",
      icon: "fa-check-circle",
      text: "Receta Válida",
    },
    "NO CUMPLE": {
      class: "status-no-cumple",
      icon: "fa-times-circle",
      text: "Receta NO Válida",
    },
    "NO VERIFICADO": {
      class: "status-no-verificado",
      icon: "fa-question-circle",
      text: "Verificación Incompleta",
    },
  };
  const statusInfo =
    statusMap[validation.estado_general] || statusMap["NO VERIFICADO"];

  container.innerHTML = `
    <div class="results-display-container">
      <div class="results-status ${statusInfo.class}">
        <i class="fas ${statusInfo.icon}"></i><span>${statusInfo.text}</span>
      </div>
      <div id="observations-container"></div>
      <div class="results-grid">
        <div class="results-column" id="results-column-left"></div>
        <div class="results-column" id="results-column-right"></div>
      </div>
      <div class="results-grid-full-width" id="results-grid-bottom"></div>
    </div>`;

  // Llenar las columnas y secciones
  const colLeft = document.getElementById("results-column-left");
  const colRight = document.getElementById("results-column-right");
  const bottomGrid = document.getElementById("results-grid-bottom");
  const observationsContainer = document.getElementById(
    "observations-container"
  );

  observationsContainer.innerHTML = generateObservationsHTML(
    validation.observaciones
  );

  // Columna Izquierda
  colLeft.innerHTML += createCard(
    '<i class="fas fa-user-circle"></i> Datos de la Receta',
    generatePatientDataHTML(iaData)
  );
  colLeft.innerHTML += createCard(
    '<i class="fas fa-pills"></i> Productos Prescriptos',
    generateProductsHTML(iaData.productos)
  );
  if (ticketData && Object.keys(ticketData).length > 0) {
    colLeft.innerHTML += createCard(
      '<i class="fas fa-receipt"></i> Datos del Ticket',
      generateTicketDataHTML(ticketData)
    );
  }

  // Columna Derecha
  colRight.innerHTML += createCard(
    '<i class="fas fa-tasks"></i> Checklist de Normativa',
    generateValidationTableHTML(validation)
  );
  if (barcodeData.length > 0) {
    colRight.innerHTML += generateBarcodeVerificationHTML(
      barcodeData,
      iaData.productos
    );
  }

  // Fila Inferior
  if (comparisonData) {
    bottomGrid.innerHTML += generateComparisonHTML(comparisonData);
  }

  // Al final de todos los resultados, añade el botón para subir nueva receta
  container.innerHTML += `
    <div class="center-content" style="margin-top: 30px;">
      <button id="uploadNewRecetaBtn" class="requerimientos-boton">
        <i class="fas fa-upload"></i> Subir Nueva Receta
      </button>
    </div>
  `;

  // Añade el event listener para el nuevo botón
  document
    .getElementById("uploadNewRecetaBtn")
    .addEventListener("click", resetApplication);
}

// Nueva función para reiniciar la aplicación
function resetApplication() {
  const formContainer = document.getElementById("form-container");
  const spinnerContainer = document.getElementById("spinner-container");
  const resultsContainer = document.getElementById("results-display");
  const jsonOutput = document.getElementById("json-output");

  // Limpia los contenidos
  resultsContainer.innerHTML = "";
  jsonOutput.textContent = "";
  jsonOutput.className = "";

  // Oculta resultados y spinner
  resultsContainer.style.display = "none";
  spinnerContainer.style.display = "none";
  jsonOutput.style.display = "none";

  // Muestra el formulario
  formContainer.style.display = "block";

  // Opcional: Limpiar el input de archivo
  document.getElementById("recetaFile").value = "";
}

function createCard(titleHTML, contentHTML, cardClasses = "") {
  return `<div class="results-card ${cardClasses}"><h3>${titleHTML}</h3>${contentHTML}</div>`;
}

// --- RESTO DE FUNCIONES (sin cambios significativos, excepto setLoadingState) ---

// setLoadingState está ahora mucho más limpia
function setLoadingState(isLoading) {
  const formContainer = document.getElementById("form-container");
  const spinnerContainer = document.getElementById("spinner-container");
  const resultsContainer = document.getElementById("results-display");

  if (isLoading) {
    formContainer.style.display = "none";
    spinnerContainer.style.display = "block";
    resultsContainer.style.display = "none";
    document.getElementById("json-output").style.display = "none";
  } else {
    spinnerContainer.style.display = "none";
    // Muestra el formulario de nuevo si no hay resultados (por ejemplo, en un error)
    if (resultsContainer.innerHTML.trim() === "") {
      formContainer.style.display = "block";
    } else {
      resultsContainer.style.display = "block";
    }
  }
}

function showError(message) {
  const preOutput = document.getElementById("json-output");
  const resultsContainer = document.getElementById("results-display");
  resultsContainer.style.display = "none"; // Oculta resultados si hay error
  preOutput.style.display = "block";
  preOutput.textContent = message;
  preOutput.className = "error";

  // Aseguramos que el formulario vuelva a aparecer en caso de error
  document.getElementById("form-container").style.display = "block";
}

function generatePatientDataHTML(iaData) {
  if (!iaData || Object.keys(iaData).length === 0)
    return "<p>No se extrajeron datos de la receta.</p>";

  const fields = [
    { icon: "fa-user", label: "Nombre del Paciente", value: iaData.paciente },
    {
      icon: "fa-id-card",
      label: "Nro de Afiliado",
      value: iaData.numero_afiliado,
    },
    {
      icon: "fa-address-card",
      label: "DNI del Paciente",
      value: iaData.dni_paciente,
    },
    {
      icon: "fa-briefcase-medical",
      label: "Obra Social",
      value: iaData.obra_social,
    },
    {
      icon: "fa-calendar-alt",
      label: "Fecha de Prescripción",
      value: iaData.fecha_receta,
    },
    {
      icon: "fa-file-medical-alt",
      label: "Diagnóstico",
      value: iaData.diagnostico,
    },
    {
      icon: "fa-user-md",
      label: "Nombre del Médico",
      value: iaData.medico_nombre,
    },
    {
      icon: "fa-id-badge",
      label: "Matrícula del Médico",
      value: iaData.medico_matricula,
    },
  ];

  return generateDataList(fields);
}

function generateProductsHTML(products) {
  if (!products || products.length === 0) {
    return "<p>No se encontraron productos.</p>";
  }
  return products
    .map(
      (product) =>
        // Ya no necesitamos la clase 'prescription-item'
        `<div class="product-block">${generateDataList([
          {
            icon: "fa-pills",
            label: "Descripción",
            value: product.descripcion,
          },
          { icon: "fa-hashtag", label: "Cantidad", value: product.cantidad },
        ])}</div>`
    )
    .join("");
}

function generateTicketDataHTML(ticketData) {
  if (!ticketData || Object.keys(ticketData).length === 0) return "";

  let html = generateDataList([
    {
      icon: "fa-calendar-alt",
      label: "Fecha del Ticket",
      value: ticketData.fecha_ticket,
    },
    {
      icon: "fa-id-card",
      label: "Nro Afiliado (detectado)",
      value: ticketData.numero_afiliado,
    },
    {
      icon: "fa-address-card",
      label: "DNI (detectado)",
      value: ticketData.dni_paciente,
    },
  ]);

  // Añadimos una clase para poder darle estilo
  html += `<h4 class="card-subtitle">Productos Comprados</h4>`;
  html += generateProductsHTML(ticketData.productos);
  return html;
}

function generateComparisonHTML(comparison) {
  if (!comparison) return "";
  const statusMap = {
    COINCIDENCIA_TOTAL: { class: "status-cumple", text: "Coincidencia Total" },
    COINCIDENCIA_PARCIAL: {
      class: "status-no-verificado",
      text: "Coincidencia Parcial",
    },
    SIN_COINCIDENCIAS: { class: "status-no-cumple", text: "Sin Coincidencias" },
    NO_SE_PROCESO_TICKET: {
      class: "status-no-cumple",
      text: "Ticket no procesado",
    },
  };
  const statusInfo = statusMap[comparison.estado_general] || {
    class: "status-no-cumple",
    text: "Estado Desconocido",
  };

  // --- MEJORA VISUAL: Reemplazamos los puntos con íconos ---
  const observationsHTML = (comparison.observaciones || [])
    .map((obs) => {
      // Si la observación es positiva, usa un ícono de check
      if (obs.startsWith("OK:")) {
        return `<li class="match-text"><i class="fas fa-check-circle"></i> ${obs.replace(
          "OK: ",
          ""
        )}</li>`;
      }
      // Si la observación es un error, usa un ícono de error
      if (obs.startsWith("ERROR:")) {
        return `<li class="no-match-text"><i class="fas fa-times-circle"></i> ${obs.replace(
          "ERROR: ",
          ""
        )}</li>`;
      }
      // Para cualquier otro caso, un ícono genérico
      return `<li><i class="fas fa-angle-right"></i> ${obs}</li>`;
    })
    .join("");

  const productsHTML = (comparison.detalle_productos || [])
    .map(
      (p) => `
        <tr>
            <td>${p.receta || "N/A"}</td>
            <td>${p.ticket || "N/A"}</td>
            <td class="${
              p.estado === "COINCIDE" ? "match-text" : "no-match-text"
            }">
              ${p.estado}
            </td>
        </tr>
    `
    )
    .join("");

  // Usamos la función createCard para mantener la consistencia
  return createCard(
    '<i class="fas fa-exchange-alt"></i> Comparación Receta vs. Ticket',
    `<div class="results-status ${statusInfo.class}">${statusInfo.text}</div>
       <div class="comparison-details">
         <h4>Observaciones:</h4>
         <ul class="comparison-observations">${observationsHTML}</ul>
         <h4>Detalle de Productos:</h4>
         <table class="comparison-table">
             <thead><tr><th>Producto Receta</th><th>Producto Ticket</th><th>Estado</th></tr></thead>
             <tbody>${productsHTML}</tbody>
         </table>
       </div>`,
    "comparison-card"
  );
}

function generateValidationTableHTML(validation) {
  const requisitos = validation.requisitos_normativa || {};
  const encontrados = validation.datos_encontrados || {};
  const ALL_REQUIREMENTS = {
    afiliado: { label: "DNI / Afiliado", foundKey: "afiliado_presente" },
    membrete: { label: "Membrete", foundKey: "membrete_presente" },
    firma: { label: "Firma Médico", foundKey: "firma_del_medico_presente" },
    sello: { label: "Sello Médico (Matrícula)", foundKey: "sello_presente" },
    diagnostico: { label: "Diagnóstico", foundKey: "diagnostico_presente" },
    monodroga: { label: "Monodroga", foundKey: "monodroga_presente" },
    validez_dias: {
      label: "Vigencia de Receta",
      foundKey: "estado_vencimiento",
    },
  };
  let tableRows = "";
  for (const key in ALL_REQUIREMENTS) {
    const reqData = ALL_REQUIREMENTS[key];
    const exigidoValue =
      requisitos[key] || (key === "validez_dias" ? "No aplica" : false);
    const encontradoValue = encontrados[reqData.foundKey] || false;
    tableRows += `<tr><td>${reqData.label}</td><td>${formatRequirement(
      key,
      exigidoValue
    )}</td><td>${formatFound(key, encontradoValue)}</td></tr>`;
  }
  if (!tableRows) return "<p>No se encontraron normativas.</p>";
  return `<table class="validation-table"><thead><tr><th>Requisito</th><th>Exigido</th><th>En Receta</th></tr></thead><tbody>${tableRows}</tbody></table>`;
}

function generateBarcodeVerificationHTML(barcodesData, prescribedProducts) {
  if (!barcodesData || barcodesData.length === 0) return "";
  const itemsHTML = barcodesData
    .map((item) => {
      const isFoundInVademecum = item.estado === "ENCONTRADO";
      let matchStatus = {
        class: "no-match",
        text: "NO COINCIDE CON LA PRESCRIPCIÓN",
      };

      if (isFoundInVademecum && prescribedProducts) {
        const vademecumMonodroga = (item.datos.MONODROGA || "")
          .toLowerCase()
          .trim();
        const vademecumDescripcion = (item.datos.DESCRIPCION || "")
          .toLowerCase()
          .trim();
        const isMatch = prescribedProducts.some((p) => {
          const prescribedDesc = p.descripcion.toLowerCase().trim();
          const vademecumBrand = vademecumDescripcion.split(" ")[0];
          const prescribedBrand = prescribedDesc.split(" ")[0];
          const matchesDescription =
            vademecumBrand &&
            prescribedBrand &&
            vademecumBrand === prescribedBrand;
          const drugComponents = vademecumMonodroga.split("+");
          const matchesMonodroga =
            vademecumMonodroga &&
            drugComponents.every((component) =>
              prescribedDesc.includes(component.trim())
            );
          return matchesDescription || matchesMonodroga;
        });
        if (isMatch) {
          matchStatus = {
            class: "match",
            text: "COINCIDE CON LA PRESCRIPCIÓN",
          };
        }
      }

      // --- ESTA ES LA PARTE CORREGIDA ---
      const vademecumDataHTML = isFoundInVademecum
        ? generateDataList([
            {
              icon: "fa-box-open",
              label: "Producto (Vademécum)",
              value: item.datos.DESCRIPCION,
            },
            {
              icon: "fa-flask",
              label: "Monodroga",
              value: item.datos.MONODROGA,
            },
          ])
        : "<p>Código no encontrado en Vademécum.</p>";

      return `
            <div class="barcode-item">
                <div class="barcode-item-header"><i class="fas fa-barcode"></i> Código: ${item.codigo}</div>
                ${vademecumDataHTML}
                <div class="comparison-status ${matchStatus.class}">${matchStatus.text}</div>
            </div>`;
    })
    .join("");

  return createCard(
    '<i class="fas fa-microchip"></i> Verificación de Productos (Troqueles)',
    itemsHTML
  );
}

function formatRequirement(key, value) {
  if (key === "validez_dias") {
    if (typeof value === "number") return `${value} días`;
    return value;
  }
  return value ? getIcon(true) : getIcon(false);
}

function formatFound(key, value) {
  if (key === "validez_dias") {
    if (value === "VIGENTE")
      return `<span style="color:var(--color-exito);">${value}</span>`;
    if (value === "VENCIDA")
      return `<span style="color:var(--color-error);">${value}</span>`;
    return value || getIcon("unknown");
  }
  return getIcon(value);
}

function getIcon(status) {
  if (status === true) return '<i class="fas fa-check-circle"></i>';
  if (status === false) return '<i class="fas fa-times-circle"></i>';
  return '<i class="fas fa-question-circle"></i>';
}

/**
 * REFACTORIZADO: Genera una lista de campos con íconos.
 * @param {Array<Object>} fields - Un array de objetos, donde cada objeto es {icon, label, value}.
 * @returns {string} - El HTML de la lista de datos.
 */
function generateDataList(fields) {
  let html = '<div class="data-list-container">';
  let hasContent = false;

  for (const field of fields) {
    if (field.value) {
      html += `
        <div class="data-item">
          <div class="data-item-label">
            <i class="fas ${field.icon} fa-fw"></i>
            <span>${field.label}</span>
          </div>
          <div class="data-item-value">${field.value}</div>
        </div>
      `;
      hasContent = true;
    }
  }

  if (!hasContent) return "<p>No se encontraron datos.</p>";
  html += "</div>";
  return html;
}

function generateObservationsHTML(observations) {
  if (
    !observations ||
    observations.length === 0 ||
    observations[0] === "Sin observaciones."
  )
    return "";
  return createCard(
    '<i class="fas fa-exclamation-triangle"></i> Observaciones',
    `<ul class="observations-list">${observations
      .map((obs) => `<li><i class="fas fa-angle-right"></i> ${obs}</li>`)
      .join("")}</ul>`,
    "observations"
  );
}

window.addEventListener("resize", ajustarMenuHamburguesa);
window.addEventListener("DOMContentLoaded", ajustarMenuHamburguesa);
