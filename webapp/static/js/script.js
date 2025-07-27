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
        // No le pongas clases de Bootstrap, solo usará tu CSS personalizado
        listaObras.appendChild(div);
      });
    }
  } catch (err) {
    console.error("No se pudo cargar la lista de obras sociales:", err);
    if (listaObras) {
      listaObras.innerHTML = `<div style="color: red;">❌ No se pudo cargar el listado.</div>`;
    }
  }

  // Cargar lista de obras una vez
  try {
    const res = await fetch("/api/lista-obras");
    todasLasObras = await res.json();
  } catch (err) {
    console.error("No se pudo cargar la lista de obras sociales:", err);
  }

  // Filtrado dinámico al tipear
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
  } else {
    let html = `<h4 class="requerimientos-titulo">📄 Requisitos para <strong>${data.obra}</strong></h4>`;
    html += `<div class="requerimientos-scroll">
      <table class="requerimientos-tabla">
        <thead>
          <tr><th>Normativa</th><th>Respuesta</th></tr>
        </thead>
        <tbody>`;

    data.requisitos.forEach((item) => {
      const valor = String(item.valor).toUpperCase().trim();
      const esAprobado =
        valor === "SI" ||
        valor === "T&S" ||
        valor === "DIRECTO" ||
        valor.includes("DIGITAL");
      const icono = esAprobado
        ? '<span class="requerimientos-check">✅</span>'
        : '<span class="requerimientos-cross">❌</span>';

      html += `<tr><td>${item.norma}</td><td>${icono} ${valor}</td></tr>`;
    });

    html += `</tbody></table></div>`;

    resultado.innerHTML = html;
  }
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

      fetch("enviar.php", {
        method: "POST",
        body: formData,
      })
        .then((respuesta) => {
          if (!respuesta.ok) throw new Error("Error en el envío.");
          return respuesta.text();
        })
        .then(() => {
          Swal.fire(
            "¡Gracias!",
            "Tu mensaje fue enviado correctamente.",
            "success"
          );
          formulario.reset();
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
