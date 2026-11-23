let filter = "all";
let query = "";
let currentProduct = null;
let selectedShade = "";
let searchTimer = null;
let renderVersion = 0;

const grid = document.querySelector("#products");
const detailDialog = document.querySelector("#detail");
const detailImage = document.querySelector("#detailImage");
const sessionId = getSessionId();

function getSessionId() {
  let id = localStorage.getItem("rabanistore-session");
  if (!id) {
    id = globalThis.crypto?.randomUUID?.() || `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem("rabanistore-session", id);
  }
  return id;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

function formatPrice(price) {
  return `C$${new Intl.NumberFormat("es-NI", { maximumFractionDigits: 0 }).format(price)}`;
}

function productImagePath(filename) {
  return `/assets/productos/${encodeURIComponent(filename || "")}`;
}

function imageHTML(product, filename = product.img) {
  const image = filename || product.img;
  return `
    <img src="${productImagePath(image)}" alt="${escapeHTML(product.name)}"
      onerror="this.style.display='none';this.nextElementSibling.style.display='block'">
    <div class="placeholder" style="display:none">
      ${escapeHTML(product.name)}<small>RABANISTORE</small>
    </div>
  `;
}

async function requestJSON(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "No se pudo completar la solicitud.");
  return payload;
}

async function loadFilters() {
  const container = document.querySelector("#filters");
  try {
    const data = await requestJSON("/api/categories");
    const buttons = [{ id: "all", label: "Todos" }, ...data.filters];
    container.innerHTML = buttons.map(category => `
      <button class="filter ${category.id === filter ? "active" : ""}"
        data-filter="${escapeHTML(category.id)}" type="button">${escapeHTML(category.label)}</button>
    `).join("");
  } catch (error) {
    container.innerHTML = '<p class="api-message">No se pudieron cargar las categorías.</p>';
  }
}

async function render() {
  const thisRender = ++renderVersion;
  const params = new URLSearchParams({ category: filter, q: query });
  grid.setAttribute("aria-busy", "true");
  try {
    const products = await requestJSON(`/api/products?${params}`);
    if (thisRender !== renderVersion) return;
    grid.innerHTML = products.length ? products.map(product => `
      <article class="card" data-id="${escapeHTML(product.id)}" tabindex="0" role="button"
        aria-label="Ver ${escapeHTML(product.name)}">
        <div class="photo">
          <span class="tag">${escapeHTML(product.label)}</span>
          ${imageHTML(product)}
          <span class="quick">Ver tonos y detalles ↗</span>
        </div>
        <div class="meta">
          <small>${escapeHTML(product.label)}</small>
          <h3>${escapeHTML(product.name)}</h3>
          <h4>${formatPrice(product.price)}</h4>
          <p>${product.shades.length} ${product.shades.length === 1 ? "tono disponible" : "tonos disponibles"}</p>
        </div>
      </article>
    `).join("") : "<p>No encontramos productos con esa búsqueda.</p>";
  } catch (error) {
    if (thisRender === renderVersion) grid.innerHTML = '<p class="api-message">No se pudo conectar con el catálogo. Inicia el servidor Python.</p>';
  } finally {
    if (thisRender === renderVersion) grid.removeAttribute("aria-busy");
  }
}

function renderMiniProducts(container, products, emptyMessage) {
  if (!products.length) {
    container.innerHTML = emptyMessage ? `<p class="empty-note">${escapeHTML(emptyMessage)}</p>` : "";
    return;
  }
  container.innerHTML = products.map(product => `
    <button class="mini-product" type="button" data-id="${escapeHTML(product.id)}">
      ${imageHTML(product)}
      <span>${escapeHTML(product.name)}</span>
      <small>${formatPrice(product.price)}</small>
    </button>
  `).join("");
}

async function loadHistory() {
  try {
    const params = new URLSearchParams({ session: sessionId });
    const products = await requestJSON(`/api/history?${params}`);
    renderMiniProducts(document.querySelector("#recentlyViewed"), products,
      "Los productos que abras aparecerán aquí.");
  } catch (error) {
    document.querySelector("#recentlyViewed").innerHTML = '<p class="empty-note">No se pudo cargar el historial.</p>';
  }
}

async function openProduct(id) {
  try {
    const product = await requestJSON(`/api/products/${encodeURIComponent(id)}`);
    currentProduct = product;
    selectedShade = product.shades[0]?.name || "";
    document.querySelector("#detailCat").textContent = product.label;
    document.querySelector("#detailName").innerHTML = `${escapeHTML(product.name)}<br>${formatPrice(product.price)}`;
    document.querySelector("#detailDesc").textContent = product.desc;

    const shadesContainer = document.querySelector("#shades");
    shadesContainer.innerHTML = product.shades.map((shade, index) => `
      <button class="shade ${index === 0 ? "selected" : ""}" type="button"
        data-shade-index="${index}" aria-pressed="${index === 0 ? "true" : "false"}">
        ${escapeHTML(shade.name)}
      </button>
    `).join("");
    selectShade(product, 0);
    detailDialog.showModal();

    requestJSON("/api/history", {
      method: "POST", body: JSON.stringify({ session: sessionId, product_id: product.id })
    }).then(products => renderMiniProducts(document.querySelector("#recentlyViewed"), products))
      .catch(() => {});
    loadRecommendations(product.id);
  } catch (error) {
    grid.insertAdjacentHTML("afterbegin", `<p class="api-message">${escapeHTML(error.message)}</p>`);
  }
}

function selectShade(product, shadeIndex) {
  const shade = product.shades[shadeIndex];
  if (!shade) return;
  selectedShade = shade.name;
  detailImage.innerHTML = imageHTML(product, shade.img || product.img);
  document.querySelector("#selectedShade").textContent = `Tono seleccionado: ${shade.name}`;
}

async function loadRecommendations(productId) {
  const container = document.querySelector("#recommendations");
  try {
    const products = await requestJSON(`/api/recommendations/${encodeURIComponent(productId)}`);
    renderMiniProducts(container, products, "Pronto habrá más combinaciones para descubrir.");
  } catch (error) {
    container.innerHTML = '<p class="empty-note">No se pudieron cargar las recomendaciones.</p>';
  }
}

async function loadCart() {
  const params = new URLSearchParams({ session: sessionId });
  const items = await requestJSON(`/api/cart?${params}`);
  const count = items.reduce((total, item) => total + item.quantity, 0);
  document.querySelector("#cartCount").textContent = count;
  const list = document.querySelector("#cartItems");
  list.innerHTML = items.length ? items.map(item => `
    <li class="cart-item">
      <span><b>${escapeHTML(item.name)}</b><small>${escapeHTML(item.shade)} · ${item.quantity} × ${formatPrice(item.unit_price)}</small></span>
      <button type="button" class="remove-cart-item" data-key="${escapeHTML(item.key)}" aria-label="Quitar ${escapeHTML(item.name)}">×</button>
    </li>
  `).join("") : '<li class="empty-note">Tu bolsa está vacía.</li>';
  const total = items.reduce((sum, item) => sum + item.unit_price * item.quantity, 0);
  document.querySelector("#cartTotal").textContent = `Total: ${formatPrice(total)}`;
}

async function addCurrentProduct() {
  if (!currentProduct || !selectedShade) return;
  const button = document.querySelector("#addToCart");
  try {
    await requestJSON("/api/cart", {
      method: "POST",
      body: JSON.stringify({ session: sessionId, product_id: currentProduct.id, shade: selectedShade })
    });
    await loadCart();
    button.textContent = "Agregado a la bolsa ✓";
    window.setTimeout(() => { button.textContent = "Agregar a la bolsa"; }, 1600);
  } catch (error) {
    button.textContent = error.message;
    window.setTimeout(() => { button.textContent = "Agregar a la bolsa"; }, 2200);
  }
}

async function recordCartInquiries() {
  try {
    const items = await requestJSON(`/api/cart?session=${encodeURIComponent(sessionId)}`);
    await Promise.all(items.map(item => requestJSON("/api/inquiries", {
      method: "POST",
      body: JSON.stringify({ session: sessionId, product_id: item.product_id, shade: item.shade }),
      keepalive: true
    })));
  } catch (error) {
    // El enlace de Instagram sigue disponible aunque la cola local no responda.
  }
}

document.querySelector("#filters").addEventListener("click", event => {
  const button = event.target.closest("button[data-filter]");
  if (!button) return;
  filter = button.dataset.filter;
  document.querySelectorAll(".filter").forEach(item => item.classList.toggle("active", item === button));
  render();
});

document.querySelector("#search").addEventListener("input", event => {
  query = event.target.value.trim();
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(render, 180);
});

grid.addEventListener("click", event => {
  const card = event.target.closest(".card[data-id]");
  if (card) openProduct(card.dataset.id);
});

grid.addEventListener("keydown", event => {
  if ((event.key === "Enter" || event.key === " ") && event.target.matches(".card[data-id]")) {
    event.preventDefault();
    openProduct(event.target.dataset.id);
  }
});

document.querySelector("#shades").addEventListener("click", event => {
  const button = event.target.closest("button[data-shade-index]");
  if (!button || !currentProduct) return;
  const index = Number(button.dataset.shadeIndex);
  selectShade(currentProduct, index);
  document.querySelectorAll("#shades .shade").forEach(other => {
    const selected = other === button;
    other.classList.toggle("selected", selected);
    other.setAttribute("aria-pressed", String(selected));
  });
});

document.querySelector("#recommendations").addEventListener("click", event => {
  const button = event.target.closest("button[data-id]");
  if (button) openProduct(button.dataset.id);
});

document.querySelector("#recentlyViewed").addEventListener("click", event => {
  const button = event.target.closest("button[data-id]");
  if (button) openProduct(button.dataset.id);
});

document.querySelector("#undoVisit").addEventListener("click", async () => {
  try {
    const products = await requestJSON("/api/history/undo", {
      method: "POST", body: JSON.stringify({ session: sessionId })
    });
    renderMiniProducts(document.querySelector("#recentlyViewed"), products,
      "Los productos que abras aparecerán aquí.");
  } catch (error) {}
});

document.querySelector("#addToCart").addEventListener("click", addCurrentProduct);
document.querySelector("#cartButton").addEventListener("click", async () => {
  try {
    await loadCart();
    document.querySelector("#cartDialog").showModal();
  } catch (error) {}
});
document.querySelector("#closeCart").addEventListener("click", () => document.querySelector("#cartDialog").close());
document.querySelector("#cartItems").addEventListener("click", async event => {
  const button = event.target.closest("button[data-key]");
  if (!button) return;
  await requestJSON(`/api/cart?session=${encodeURIComponent(sessionId)}`, {
    method: "DELETE", body: JSON.stringify({ key: button.dataset.key })
  });
  await loadCart();
});

document.querySelector("#consultInstagram").addEventListener("click", () => {
  if (!currentProduct) return;
  requestJSON("/api/inquiries", {
    method: "POST",
    body: JSON.stringify({ session: sessionId, product_id: currentProduct.id, shade: selectedShade }),
    keepalive: true
  }).catch(() => {});
});
document.querySelector("#cartInstagram").addEventListener("click", recordCartInquiries);

document.querySelector(".close").addEventListener("click", () => detailDialog.close());
detailDialog.addEventListener("click", event => {
  if (event.target === detailDialog) detailDialog.close();
});
document.querySelector("#cartDialog").addEventListener("click", event => {
  if (event.target === event.currentTarget) event.currentTarget.close();
});
document.querySelector("#menu").addEventListener("click", () => {
  document.querySelector("#nav").classList.toggle("open");
});

loadFilters();
render();
loadHistory();
loadCart().catch(() => {});
