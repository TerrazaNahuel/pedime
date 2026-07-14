/**
 * Lógica del carrito de compras y menú público.
 *
 * Funcionalidades:
 *   - Carga datos del menú desde la API
 *   - Renderiza productos, categorías y búsqueda
 *   - Carrito con suma/resta de productos
 *   - Selector de entrega (domicilio/retiro)
 *   - Selector de método de pago
 *   - Comentario del pedido
 *   - Envío del pedido por WhatsApp
 *   - Modo solo lectura cuando el local está cerrado
 */

const API_BASE = "";

/** Genera la clave única para almacenar el carrito en localStorage según el slug del local. */
function storageKey() { return "pedime_cart_" + (currentSlug || "default"); }

let storeData = null;
let productMap = null;
let cart = {};
let currentSlug = "";
let selectedDelivery = false;
let selectedPayment = null;
let deliveryAddress = "";
let deliveryReference = "";
let orderComment = "";
let expandedCategories = new Set();

const CART_VERSION = 2;

/** Combina ID y variante en una clave única para el carrito. */
function cartKey(id, variantIndex) {
    return variantIndex != null ? id + "_" + variantIndex : String(id);
}

/** Descompone una clave del carrito en ID de producto e índice de variante. */
function parseCartKey(key) {
    const parts = key.split("_");
    if (parts.length === 2 && !isNaN(parts[1])) {
        return { id: parseInt(parts[0]), variantIndex: parseInt(parts[1]) };
    }
    return {     id: parseInt(key), variantIndex: null };
}

/** Crea los botones +/− para agregar o quitar un producto del carrito, respetando stock. */
function createQtyControls(id, variantIndex, plusCallback) {
    const key = cartKey(id, variantIndex);
    const div = document.createElement("div");
    div.className = "qty-controls flex items-center gap-2";
    if (cart[key]) {
        const minus = document.createElement("button");
        minus.className = "w-8 h-8 rounded-full bg-white/10 text-white font-bold hover:bg-white/20 transition text-lg flex items-center justify-center";
        minus.textContent = "\u2212";
        minus.onclick = () => removeFromCart(id, variantIndex);
        div.appendChild(minus);
        const count = document.createElement("span");
        count.className = "text-white font-bold w-6 text-center";
        count.textContent = cart[key].qty;
        div.appendChild(count);
    }
    const limit = getStockLimit(id, variantIndex);
    const atLimit = limit <= 0;
    const addBtn = document.createElement("button");
    addBtn.className = "w-8 h-8 rounded-full font-bold transition text-lg flex items-center justify-center " + (atLimit ? "bg-white/5 text-gray-600 cursor-not-allowed" : "bg-emerald-500 text-white hover:bg-emerald-600");
    addBtn.textContent = "+";
    addBtn.disabled = atLimit;
    addBtn.onclick = atLimit ? null : () => { plusCallback(); updateProductQtyInDOM(id); };
    div.appendChild(addBtn);
    return div;
}

/** Persiste el estado completo del carrito en localStorage. */
function saveCartState() {
    try {
        localStorage.setItem(storageKey(), JSON.stringify({
            _version: CART_VERSION,
            cart,
            selectedDelivery,
            selectedPayment,
            deliveryAddress,
            deliveryReference,
            orderComment,
        }));
    } catch {
        console.error("Pedime: no se pudo guardar el estado del carrito en localStorage");
    }
}

/** Restaura el estado del carrito desde localStorage, con validación de versión. */
function loadCartState() {
    try {
        const saved = localStorage.getItem(storageKey());
        if (!saved) return;
        const data = JSON.parse(saved);
        if (data._version !== CART_VERSION) {
            cart = {};
            saveCartState();
            return;
        }
        if (data.cart) {
            cart = data.cart;
            Object.values(cart).forEach(item => {
                if (item.variant === undefined) item.variant = null;
                if (item.variantIndex === undefined) item.variantIndex = null;
            });
        }
        if (data.selectedDelivery !== undefined) selectedDelivery = data.selectedDelivery;
        if (data.selectedPayment) selectedPayment = data.selectedPayment;
        if (data.deliveryAddress) deliveryAddress = data.deliveryAddress;
        if (data.deliveryReference) deliveryReference = data.deliveryReference;
        if (data.orderComment) orderComment = data.orderComment;
    } catch {
        console.warn("Pedime: no se pudo cargar el estado del carrito desde localStorage");
    }
}

/**
 * Verifica si el local está abierto según horario configurado.
 * Soporta horarios que cruzan medianoche (ej: 20:00 - 02:00).
 * @returns {boolean} True si el local está abierto actualmente.
 */
function isStoreOpen() {
    if (!storeData.opening_time || !storeData.closing_time) return true;
    const now = new Date();
    // working_days: 1=Lunes...7=Domingo. JS getDay(): 0=Dom,1=Lun...6=Sáb
    const today = now.getDay() === 0 ? 7 : now.getDay();
    const days = (storeData.working_days || "1,2,3,4,5,6,7").split(",").map(Number);
    if (!days.includes(today)) return false;
    const mins = now.getHours() * 60 + now.getMinutes();
    const [openH, openM] = storeData.opening_time.split(":").map(Number);
    const [closeH, closeM] = storeData.closing_time.split(":").map(Number);
    const openMins = openH * 60 + openM;
    const closeMins = closeH * 60 + closeM;
    if (closeMins <= openMins) {
        return mins >= openMins || mins <= closeMins;
    }
    return mins >= openMins && mins <= closeMins;
}

/**
 * Inicializa la app extrayendo el slug de la URL y cargando el menú.
 * Es el punto de entrada principal del frontend público.
 */
function init() {
    currentSlug = window.location.pathname.split("/menu/")[1];
    if (!currentSlug) { showError(); return; }
    loadCartState();
    fetchMenu();
}

/**
 * Obtiene los datos del menú desde la API y prepara el renderizado.
 * Convierte precios a número, parsea variantes y envía tracking de visita.
 */
async function fetchMenu() {
    try {
        const res = await fetch(`${API_BASE}/api/menu/${currentSlug}`);
        if (!res.ok) throw new Error("Not found");
        storeData = await res.json();
        // Convierte precios de string a número y parsea variants de una vez
        storeData.delivery_price = Number(storeData.delivery_price);
        productMap = {};
        for (const cat of storeData.categories) {
            for (const p of cat.products) {
                p.price = Number(p.price);
                try {
                    const v = JSON.parse(p.variants || "[]");
                    p._variantsArr = Array.isArray(v) && v.length ? v : null;
                } catch (e) {
                    console.warn("Pedime: error parseando variants del producto", p.id, e);
                    p._variantsArr = null;
                }
                productMap[p.id] = p;
            }
        }
        renderMenu();
        // Tracking de visita (fire-and-forget)
        navigator.sendBeacon(`${API_BASE}/api/track/view/${currentSlug}`, "");
    } catch { console.warn("fetchMenu falló"); showError(); }
}

/**
 * Renderiza los datos del local: nombre, logo, colores, métodos de pago y envío.
 * También oculta el loader y muestra el meta-información.
 */
function renderStoreDetails() {
    document.getElementById("loading").classList.add("hidden");
    document.getElementById("store-name").textContent = storeData.store_name;
    document.title = storeData.store_name + " - Pedime";
    const color = storeData.primary_color || "#10b981";
    document.documentElement.style.setProperty("--accent", color);
    const logo = document.getElementById("store-logo");
    if (storeData.logo_url) {
        logo.src = storeData.logo_url;
        logo.classList.remove("hidden");
        logo.onerror = () => logo.classList.add("hidden");
    } else {
        logo.classList.add("hidden");
    }
    const meta = document.getElementById("store-meta");
    meta.innerHTML = "";
    const parts = [];
    if (storeData.delivery_available) {
        const cost = storeData.delivery_price > 0 ? "$" + storeData.delivery_price.toLocaleString("es-AR") : "Gratis";
        parts.push("🚚 Envío: " + cost);
    } else {
        parts.push("🚚 Solo retiro");
    }
    const methods = [];
    if (storeData.payment_transfer) methods.push("Transferencia");
    if (storeData.payment_cash) methods.push("Efectivo");
    if (methods.length) parts.push("💳 " + methods.join(" / "));
    meta.innerHTML = parts.join(" · ");
    meta.classList.remove("hidden");
}

/** Muestra u oculta el banner de "local cerrado / modo lectura". */
function renderClosedBanner(container) {
    const closedBanner = document.getElementById("closed-banner");
    if (!isStoreOpen()) {
        if (!closedBanner) {
            const banner = document.createElement("div");
            banner.id = "closed-banner";
            banner.className = "bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm rounded-xl px-4 py-3 mb-4 flex items-center gap-2";
            banner.textContent = '📖 Menú en modo lectura — volvemos a las ' + storeData.opening_time;
            container.parentNode.insertBefore(banner, container);
        }
    } else if (closedBanner) {
        closedBanner.remove();
    }
}

/** Construye la tarjeta visual de un producto individual con imagen, nombre, descripción, precio y controles de cantidad. */
function renderProductCard(prod, variantsArr, select) {
    const card = document.createElement("div");
    card.className = "product-card flex items-center justify-between bg-[#1a1a1a] rounded-xl p-4 border border-white/5 gap-3";
    card.dataset.id = prod.id;
    card.setAttribute("data-name", prod.name.toLowerCase());
    if (prod.image_url) {
        const img = document.createElement("img");
        img.className = "w-16 h-16 rounded-xl object-cover shrink-0";
        img.src = prod.image_url;
        img.alt = prod.name;
        img.onerror = () => img.style.display = "none";
        card.appendChild(img);
    }
    const info = document.createElement("div");
    info.className = "flex-1 min-w-0 mr-3";
    const name = document.createElement("h3");
    name.className = "text-white font-semibold";
    name.textContent = prod.name;
    info.appendChild(name);
    if (prod.description) {
        const desc = document.createElement("p");
        desc.className = "text-sm text-gray-500 mt-0.5";
        desc.textContent = prod.description;
        info.appendChild(desc);
    }
    if (variantsArr) {
        select = document.createElement("select");
        select.className = "w-full bg-[#0a0a0a] border border-white/10 rounded-lg px-2 py-1 text-white text-sm mt-1";
        select.onchange = () => updateProductQtyInDOM(prod.id);
        variantsArr.forEach((v, i) => {
            const opt = document.createElement("option");
            opt.value = i;
            opt.textContent = v.name + " - $" + Number(v.price).toLocaleString("es-AR");
            select.appendChild(opt);
        });
        info.appendChild(select);
    } else {
        const price = document.createElement("p");
        price.className = "text-emerald-400 font-bold mt-1";
        price.textContent = "$" + prod.price.toLocaleString("es-AR");
        info.appendChild(price);
    }
    if (prod.stock > 0) {
        const stockBadge = document.createElement("span");
        stockBadge.className = "text-xs text-gray-500 mt-1 block";
        stockBadge.textContent = "Stock: " + prod.stock;
        info.appendChild(stockBadge);
    }
    card.appendChild(info);

    if (isStoreOpen()) {
        const qtyDiv = createQtyControls(prod.id, null, () => addToCart(prod.id, prod.name, prod.price));
        if (variantsArr) {
            const idx = parseInt(select.value);
            const key = cartKey(prod.id, idx);
            const oldDiv = qtyDiv.cloneNode(false);
            oldDiv.className = "qty-controls flex items-center gap-2";
            if (cart[key]) {
                const minus = document.createElement("button");
                minus.className = "w-8 h-8 rounded-full bg-white/10 text-white font-bold hover:bg-white/20 transition text-lg flex items-center justify-center";
                minus.textContent = "\u2212";
                minus.onclick = () => removeFromCart(prod.id, idx);
                oldDiv.appendChild(minus);
                const count = document.createElement("span");
                count.className = "text-white font-bold w-6 text-center";
                count.textContent = cart[key].qty;
                oldDiv.appendChild(count);
            }
            const limit = getStockLimit(prod.id, idx);
            const atLimit = limit <= 0;
            const addBtn = document.createElement("button");
            addBtn.className = "w-8 h-8 rounded-full font-bold transition text-lg flex items-center justify-center " + (atLimit ? "bg-white/5 text-gray-600 cursor-not-allowed" : "bg-emerald-500 text-white hover:bg-emerald-600");
            addBtn.textContent = "+";
            addBtn.disabled = atLimit;
            addBtn.onclick = atLimit ? null : () => { const i = parseInt(select.value); const v = variantsArr[i]; addToCart(prod.id, prod.name, Number(v.price), v, i); updateProductQtyInDOM(prod.id); };
            oldDiv.appendChild(addBtn);
            card.appendChild(oldDiv);
        } else {
            card.appendChild(qtyDiv);
        }
    } else {
        const badge = document.createElement("span");
        badge.className = "text-xs text-gray-500 shrink-0";
        badge.textContent = "No disponible ahora";
        card.appendChild(badge);
    }
    return card;
}

/** Renderiza una categoría completa: header colapsable, pills de navegación y tarjetas de productos. */
function renderCategorySection(cat, pillsContainer, container) {
    if (!cat.products.length) return;
    const sectionId = "cat-" + cat.id;
    const isExpanded = expandedCategories.has(cat.id);
    const section = document.createElement("div");
    section.className = "space-y-2";
    section.id = sectionId;
    const header = document.createElement("div");
    header.className = "flex items-center justify-between cursor-pointer select-none py-1";
    header.onclick = () => toggleCategory(cat.id);
    const title = document.createElement("h2");
    title.className = "text-sm font-semibold text-gray-400 uppercase tracking-wider";
    title.textContent = cat.name;
    header.appendChild(title);
    const headerRight = document.createElement("div");
    headerRight.className = "flex items-center gap-2";
    const count = document.createElement("span");
    count.className = "text-xs text-gray-600";
    count.textContent = cat.products.length + " productos";
    headerRight.appendChild(count);
    const chevron = document.createElement("span");
    chevron.className = "chevron text-gray-500 transition-transform duration-200 " + (isExpanded ? "rotate-180" : "");
    chevron.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>';
    headerRight.appendChild(chevron);
    header.appendChild(headerRight);
    section.appendChild(header);
    const productsWrapper = document.createElement("div");
    productsWrapper.className = "products-wrapper space-y-3" + (isExpanded ? "" : " hidden");
    productsWrapper.id = "products-" + cat.id;
    const pill = document.createElement("button");
    pill.className = "shrink-0 px-3 py-1.5 rounded-full text-sm font-medium bg-[#1a1a1a] text-gray-400 hover:text-white hover:bg-white/10 transition border border-white/5";
    pill.textContent = cat.name;
    pill.onclick = () => {
        if (!expandedCategories.has(cat.id)) toggleCategory(cat.id);
        document.getElementById(sectionId).scrollIntoView({ behavior: "smooth", block: "start" });
    };
    pillsContainer.appendChild(pill);
    cat.products.forEach((prod) => {
        const variantsArr = prod._variantsArr;
        let select = null;
        const card = renderProductCard(prod, variantsArr, select);
        productsWrapper.appendChild(card);
    });
    section.appendChild(productsWrapper);
    container.appendChild(section);
}

/** Renderiza el menú completo: datos del local, categorías, productos, búsqueda y navegación. */
function renderMenu() {
    renderStoreDetails();
    const container = document.getElementById("menu-content");
    container.innerHTML = "";
    renderClosedBanner(container);
    const pillsContainer = document.getElementById("category-pills");
    pillsContainer.innerHTML = "";
    storeData.categories.forEach((cat) => renderCategorySection(cat, pillsContainer, container));
    container.classList.remove("hidden");
    document.getElementById("search-section").classList.remove("hidden");
    document.getElementById("category-nav").classList.remove("hidden");
    updateCartUI();
}

/**
 * Expande o colapsa una categoría por su ID.
 * Actualiza el Set de categorías expandidas y la rotación del chevron.
 */
function toggleCategory(catId) {
    const wrapper = document.getElementById("products-" + catId);
    const chevron = document.querySelector("#cat-" + catId + " .chevron");
    if (!wrapper) return;
    const isHidden = wrapper.classList.contains("hidden");
    wrapper.classList.toggle("hidden");
    if (chevron) chevron.classList.toggle("rotate-180");
    if (isHidden) {
        expandedCategories.add(catId);
    } else {
        expandedCategories.delete(catId);
    }
}

/** Filtro de búsqueda en tiempo real: oculta productos que no coinciden y auto-expande categorías relevantes. */
document.getElementById("search-input").addEventListener("input", function() {
    const q = this.value.toLowerCase().trim();
    // Filtra cada tarjeta de producto por el nombre
    document.querySelectorAll(".product-card").forEach(card => {
        const name = card.getAttribute("data-name") || "";
        card.style.display = (!q || name.includes(q)) ? "" : "none";
    });
    // Oculta/muestra secciones de categoría y auto-expande durante la búsqueda
    document.querySelectorAll("#menu-content > div[id^='cat-']").forEach(section => {
        const visibleCards = section.querySelectorAll('.product-card[style*="display: none"]');
        const allCards = section.querySelectorAll(".product-card");
        section.style.display = (allCards.length === visibleCards.length && q) ? "none" : "";
        if (q && allCards.length > visibleCards.length) {
            const wrapper = section.querySelector(".products-wrapper");
            const chevron = section.querySelector(".chevron");
            if (wrapper && wrapper.classList.contains("hidden")) {
                wrapper.classList.remove("hidden");
                if (chevron) chevron.classList.add("rotate-180");
            }
        }
    });
});

/**
 * Actualiza los controles de cantidad de un producto en el DOM sin re-renderizar todo.
 * Reemplaza el bloque de controles +/− según el estado actual del carrito y las variantes seleccionadas.
 */
function updateProductQtyInDOM(id) {
    const card = document.querySelector(`.product-card[data-id="${id}"]`);
    if (!card) { renderMenu(); return; }
    const oldQtyDiv = card.querySelector(".qty-controls");
    if (oldQtyDiv) oldQtyDiv.remove();
    if (!isStoreOpen()) return;

    const select = card.querySelector("select");
    const variantIndex = select ? parseInt(select.value) : null;
    const prod = findProduct(id);

    let qtyDiv;
    if (select && prod) {
        qtyDiv = document.createElement("div");
        qtyDiv.className = "qty-controls flex items-center gap-2";
        const key = cartKey(id, variantIndex);
        if (cart[key]) {
            const minus = document.createElement("button");
            minus.className = "w-8 h-8 rounded-full bg-white/10 text-white font-bold hover:bg-white/20 transition text-lg flex items-center justify-center";
            minus.textContent = "\u2212";
            minus.onclick = () => removeFromCart(id, variantIndex);
            qtyDiv.appendChild(minus);
            const count = document.createElement("span");
            count.className = "text-white font-bold w-6 text-center";
            count.textContent = cart[key].qty;
            qtyDiv.appendChild(count);
        }
        const limit = getStockLimit(id, variantIndex);
        const atLimit = limit <= 0;
        const addBtn = document.createElement("button");
        addBtn.className = "w-8 h-8 rounded-full font-bold transition text-lg flex items-center justify-center " + (atLimit ? "bg-white/5 text-gray-600 cursor-not-allowed" : "bg-emerald-500 text-white hover:bg-emerald-600");
        addBtn.textContent = "+";
        addBtn.disabled = atLimit;
        addBtn.onclick = atLimit ? null : () => {
            const idx = parseInt(select.value);
            const v = (prod._variantsArr || [])[idx];
            if (v) addToCart(id, prod.name, Number(v.price), v, idx);
        };
        qtyDiv.appendChild(addBtn);
    } else {
        qtyDiv = createQtyControls(id, null, () => addToCart(id, prod ? prod.name : "Producto", prod ? prod.price : 0));
    }
    card.appendChild(qtyDiv);
    updateCartUI();
}

/**
 * Busca un producto por ID en O(1) vía productMap.
 * @returns {Object|null} El producto encontrado o null.
 */
function findProduct(id) {
    return productMap ? productMap[id] || null : null;
}

/**
 * Retorna la cantidad máxima que se puede agregar de un producto según su stock.
 * 0 = sin límite (stock negativo o sin stock definido = Infinity).
 * @returns {number} Cantidad disponible o Infinity si no hay tope.
 */
function getStockLimit(id, variantIndex) {
    const prod = findProduct(id);
    if (!prod || !prod.stock || prod.stock <= 0) return Infinity;
    const key = cartKey(id, variantIndex);
    const inCart = cart[key] ? cart[key].qty : 0;
    return prod.stock - inCart;
}

/**
 * Agrega un producto al carrito. Verifica stock, persiste y actualiza la UI.
 * @param {number} id - ID del producto.
 * @param {string} name - Nombre del producto.
 * @param {number} price - Precio unitario.
 * @param {Object|null} variant - Datos de la variante seleccionada.
 * @param {number|null} variantIndex - Índice de la variante seleccionada.
 */
function addToCart(id, name, price, variant = null, variantIndex = null) {
    if (!isStoreOpen()) return;
    const limit = getStockLimit(id, variantIndex);
    if (limit <= 0) {
        showToast("Stock agotado");
        return;
    }
    const key = cartKey(id, variantIndex);
    if (!cart[key]) cart[key] = { qty: 0, name, price, variant, variantIndex };
    cart[key].qty++;
    saveCartState();
    updateProductQtyInDOM(id);
    showToast(variant ? name + " (" + variant.name + ")" : name);
}

/**
 * Reduce la cantidad de un producto en el carrito. Si llega a 0, lo elimina del carrito.
 * @param {number} id - ID del producto.
 * @param {number|null} variantIndex - Índice de variante (opcional).
 */
function removeFromCart(id, variantIndex = null) {
    const key = cartKey(id, variantIndex);
    if (cart[key]) {
        cart[key].qty--;
        if (cart[key].qty <= 0) delete cart[key];
    }
    saveCartState();
    updateProductQtyInDOM(id);
}

/**
 * Muestra un toast animado indicando que se agregó un producto al carrito.
 * Se oculta automáticamente después de 1.2 segundos.
 */
function showToast(name) {
    const toast = document.getElementById("toast");
    toast.querySelector("div").textContent = "\u2713 " + name + " agregado";
    toast.classList.remove("hidden");
    toast.classList.add("animate-bounce");
    setTimeout(() => {
        toast.classList.add("hidden");
        toast.classList.remove("animate-bounce");
    }, 1200);
}

/** Cuenta la cantidad total de productos (sumando cantidades) en el carrito. */
function getCartCount() {
    return Object.values(cart).reduce((sum, item) => sum + item.qty, 0);
}

/** Calcula el subtotal del carrito (precio × cantidad de cada item). */
function getSubtotal() {
    return Object.values(cart).reduce((sum, item) => sum + item.price * item.qty, 0);
}

/** Retorna el costo de envío si aplica, o 0 si es retiro o no hay delivery. */
function getDeliveryCost() {
    if (!selectedDelivery || !storeData.delivery_available) return 0;
    return storeData.delivery_price;
}

/** Calcula el total del pedido (subtotal + costo de envío). */
function getTotal() {
    return getSubtotal() + getDeliveryCost();
}

/**
 * Actualiza la visibilidad del FAB (botón flotante) del carrito.
 * Solo se muestra si hay productos en el carrito y el local está abierto.
 */
function updateCartUI() {
    const count = getCartCount();
    const fab = document.getElementById("cart-fab");
    const countEl = document.getElementById("cart-count");
    if (count > 0 && isStoreOpen()) {
        fab.classList.remove("hidden");
        countEl.textContent = count;
    } else {
        fab.classList.add("hidden");
    }
}

/** Muestra la pantalla de error cuando no se puede cargar el menú. */
function showError() {
    document.getElementById("loading").classList.add("hidden");
    document.getElementById("error").classList.remove("hidden");
}

// Referencias a elementos del drawer del carrito
// Se obtienen una vez al inicio para evitar búsquedas repetidas en el DOM
const cartBtn = document.getElementById("cart-btn");
const cartDrawer = document.getElementById("cart-drawer");
const cartOverlay = document.getElementById("cart-overlay");
const cartClose = document.getElementById("cart-close");
const cartItems = document.getElementById("cart-items");
const cartTotal = document.getElementById("cart-total");
const whatsappBtn = document.getElementById("whatsapp-btn");
const deliverySection = document.getElementById("delivery-section");
const paymentSection = document.getElementById("payment-section");
const commentSection = document.getElementById("comment-section");

// Vincula eventos de apertura y cierre del drawer
cartBtn.onclick = () => openCart();
cartOverlay.onclick = () => closeCartAndSave();
cartClose.onclick = () => closeCartAndSave();

/**
 * Abre el drawer del carrito y renderiza sus secciones.
 * Inicializa el método de pago si es la primera vez.
 */
function openCart() {
    if (!selectedPayment) initPayment();
    renderDeliveryToggle();
    renderPaymentSelector();
    renderCommentSection();
    renderCartItems();
    cartDrawer.classList.remove("hidden");
    document.body.style.overflow = "hidden";
}

/**
 * Cierra el drawer guardando los valores actuales de los inputs (dirección, referencia, comentario).
 * Estos valores se persisten en localStorage para la próxima apertura.
 */
function closeCartAndSave() {
    deliveryAddress = document.getElementById("delivery-address")?.value || "";
    deliveryReference = document.getElementById("delivery-reference")?.value || "";
    orderComment = document.getElementById("order-comment")?.value || "";
    saveCartState();
    closeCart();
}

/** Cierra el drawer del carrito y restaura el scroll del body. */
function closeCart() {
    cartDrawer.classList.add("hidden");
    document.body.style.overflow = "";
}

/** Inicializa el método de pago por defecto según lo que acepte el local. */
function initPayment() {
    if (storeData.payment_transfer) selectedPayment = "transfer";
    else if (storeData.payment_cash) selectedPayment = "cash";
}

/** Renderiza los botones de selección "A domicilio" / "Retiro en local". */
function renderDeliveryButtons(el, cost) {
    const btnGroup = document.createElement("div");
    btnGroup.className = "flex gap-2";
    const deliveryBtn = document.createElement("button");
    deliveryBtn.id = "delivery-btn";
    deliveryBtn.className = "flex-1 py-2.5 rounded-xl text-sm font-medium transition border " + (selectedDelivery ? "bg-emerald-500 text-white border-emerald-500" : "bg-white/5 text-gray-400 border-white/10 hover:border-white/20");
    deliveryBtn.textContent = "A domicilio" + cost;
    btnGroup.appendChild(deliveryBtn);
    const pickupBtn = document.createElement("button");
    pickupBtn.id = "pickup-btn";
    pickupBtn.className = "flex-1 py-2.5 rounded-xl text-sm font-medium transition border " + (!selectedDelivery ? "bg-emerald-500 text-white border-emerald-500" : "bg-white/5 text-gray-400 border-white/10 hover:border-white/20");
    pickupBtn.textContent = "Retiro en local";
    btnGroup.appendChild(pickupBtn);
    el.appendChild(btnGroup);
    deliveryBtn.onclick = () => {
        deliveryAddress = document.getElementById("delivery-address")?.value || "";
        deliveryReference = document.getElementById("delivery-reference")?.value || "";
        selectedDelivery = true;
        renderDeliveryToggle();
        renderCartItems();
    };
    pickupBtn.onclick = () => {
        deliveryAddress = document.getElementById("delivery-address")?.value || "";
        deliveryReference = document.getElementById("delivery-reference")?.value || "";
        selectedDelivery = false;
        renderDeliveryToggle();
        renderCartItems();
    };
}

/** Renderiza los campos de dirección y referencia para la entrega a domicilio. */
function renderDeliveryFields(el) {
    const fieldsDiv = document.createElement("div");
    fieldsDiv.id = "delivery-fields";
    fieldsDiv.className = (selectedDelivery ? "" : "hidden") + " space-y-2 mt-3";
    const addrInput = document.createElement("input");
    addrInput.type = "text";
    addrInput.id = "delivery-address";
    addrInput.placeholder = "Dirección";
    addrInput.value = deliveryAddress;
    addrInput.className = "w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:outline-none focus:border-emerald-500 transition text-sm";
    fieldsDiv.appendChild(addrInput);
    const refInput = document.createElement("input");
    refInput.type = "text";
    refInput.id = "delivery-reference";
    refInput.placeholder = "Referencia (opcional)";
    refInput.value = deliveryReference;
    refInput.className = "w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:outline-none focus:border-emerald-500 transition text-sm";
    fieldsDiv.appendChild(refInput);
    el.appendChild(fieldsDiv);
}

/**
 * Renderiza el selector de entrega (a domicilio / retiro en local).
 * Si el local no ofrece delivery, muestra un mensaje informativo.
 */
function renderDeliveryToggle() {
    const el = deliverySection;
    el.innerHTML = "";
    if (!storeData.delivery_available) {
        const div = document.createElement("div");
        div.className = "flex items-center gap-2 text-sm text-gray-400";
        const span = document.createElement("span");
        span.textContent = "📍 Solo retiro en local";
        div.appendChild(span);
        el.appendChild(div);
        el.classList.remove("hidden");
        selectedDelivery = false;
        return;
    }
    const cost = storeData.delivery_price > 0 ? " (+$" + storeData.delivery_price.toLocaleString("es-AR") + ")" : " (Gratis)";
    const label = document.createElement("p");
    label.className = "text-xs text-gray-500 mb-2 font-medium";
    label.textContent = "📍 ENTREGA";
    el.appendChild(label);
    renderDeliveryButtons(el, cost);
    renderDeliveryFields(el);
    el.classList.remove("hidden");
}

/**
 * Renderiza los métodos de pago disponibles (transferencia / efectivo).
 * Si solo hay un método, lo muestra como texto informativo sin botones.
 */
function renderPaymentSelector() {
    const el = paymentSection;
    el.innerHTML = "";
    el.classList.remove("hidden");

    const methods = [];
    if (storeData.payment_transfer) methods.push({ value: "transfer", label: "Transferencia" });
    if (storeData.payment_cash) methods.push({ value: "cash", label: "Efectivo" });

    if (methods.length <= 1) {
        const label = methods.length ? methods[0].label : "\u2014";
        el.innerHTML = `<div class="flex items-center gap-2 text-sm text-gray-400"><span>💳 Pago: ${label}</span></div>`;
        return;
    }

    let html = '<p class="text-xs text-gray-500 mb-2 font-medium">💳 MÉTODO DE PAGO</p><div class="flex gap-2">';
    methods.forEach((m) => {
        html += `
            <button id="pay-${m.value}" class="flex-1 py-2.5 rounded-xl text-sm font-medium transition border ${selectedPayment === m.value ? 'bg-emerald-500 text-white border-emerald-500' : 'bg-white/5 text-gray-400 border-white/10 hover:border-white/20'} border">
                ${m.label}
            </button>
        `;
    });
    html += "</div>";
    el.innerHTML = html;

    methods.forEach((m) => {
        document.getElementById("pay-" + m.value).onclick = () => {
            selectedPayment = m.value;
            renderPaymentSelector();
        };
    });
}

/**
 * Renderiza el textarea de comentario del pedido.
 * Permite al cliente agregar instrucciones especiales (ej: "sin aceitunas").
 */
function renderCommentSection() {
    const el = commentSection;
    el.innerHTML = "";

    const label = document.createElement("p");
    label.className = "text-xs text-gray-500 mb-2 font-medium";
    label.textContent = "📝 COMENTARIO DEL PEDIDO";
    el.appendChild(label);

    const textarea = document.createElement("textarea");
    textarea.id = "order-comment";
    textarea.rows = 2;
    textarea.placeholder = "Ej: Sin aceitunas, mucho queso...";
    textarea.className = "w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:outline-none focus:border-emerald-500 transition text-sm resize-none";
    textarea.value = orderComment;
    el.appendChild(textarea);

    el.classList.remove("hidden");
}

/** Renderiza una fila individual del carrito con nombre, cantidad y botones +/−. */
function renderCartItemRow(id, item) {
    const el = document.createElement("div");
    el.className = "flex items-center justify-between";
    const left = document.createElement("div");
    left.className = "flex-1";
    const name = document.createElement("p");
    name.className = "text-white font-medium";
    name.textContent = item.variant ? item.name + " (" + item.variant.name + ")" : item.name;
    left.appendChild(name);
    const subtotal = document.createElement("p");
    subtotal.className = "text-sm text-gray-400";
    subtotal.textContent = item.qty + " x $" + item.price.toLocaleString("es-AR");
    left.appendChild(subtotal);
    el.appendChild(left);
    const right = document.createElement("div");
    right.className = "flex items-center gap-3";
    const minus = document.createElement("button");
    minus.className = "w-7 h-7 rounded-full bg-white/10 text-white font-bold hover:bg-white/20 transition flex items-center justify-center";
    minus.textContent = "\u2212";
    minus.onclick = () => { removeFromCart(id); renderCartItems(); updateCartUI(); };
    right.appendChild(minus);
    const qtySpan = document.createElement("span");
    qtySpan.className = "text-white font-bold w-5 text-center";
    qtySpan.textContent = item.qty;
    right.appendChild(qtySpan);
    const plus = document.createElement("button");
    const { id: prodId, variantIndex } = parseCartKey(id);
    const limit = getStockLimit(prodId, variantIndex);
    const atLimit = limit <= 0;
    plus.className = "w-7 h-7 rounded-full font-bold transition flex items-center justify-center " + (atLimit ? "bg-white/5 text-gray-600 cursor-not-allowed" : "bg-emerald-500 text-white hover:bg-emerald-600");
    plus.textContent = "+";
    plus.disabled = atLimit;
    plus.onclick = () => {
        if (atLimit) return;
        addToCart(prodId, item.name, item.price, item.variant, variantIndex);
        renderCartItems();
        updateCartUI();
    };
    right.appendChild(plus);
    el.appendChild(right);
    return el;
}

/** Actualiza el estado y texto del botón de WhatsApp según el carrito y si el local está abierto. */
function updateWhatsAppButton() {
    if (!Object.entries(cart).length) {
        whatsappBtn.disabled = true;
        whatsappBtn.classList.add("opacity-50");
        return;
    }
    whatsappBtn.disabled = false;
    whatsappBtn.classList.remove("opacity-50");
    if (!isStoreOpen()) {
        whatsappBtn.disabled = true;
        whatsappBtn.classList.add("opacity-50");
        whatsappBtn.innerHTML = "";
        whatsappBtn.textContent = "📖 Modo lectura — volvemos a las " + storeData.opening_time;
    } else {
        whatsappBtn.disabled = false;
        whatsappBtn.classList.remove("opacity-50");
        whatsappBtn.innerHTML = '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>';
        whatsappBtn.appendChild(document.createTextNode(" Enviar pedido por WhatsApp"));
    }
}

/**
 * Renderiza los items del carrito con cantidades, subtotales y totales.
 * Muestra un mensaje vacío si no hay productos en el carrito.
 */
function renderCartItems() {
    cartItems.innerHTML = "";
    const entries = Object.entries(cart);
    if (!entries.length) {
        cartItems.innerHTML = '<p class="text-gray-500 text-center py-8">Tu carrito está vacío</p>';
        cartTotal.textContent = "$0";
        whatsappBtn.disabled = true;
        whatsappBtn.classList.add("opacity-50");
        return;
    }
    updateWhatsAppButton();
    entries.forEach(([id, item]) => cartItems.appendChild(renderCartItemRow(id, item)));
    renderCartTotals(cartItems);
}

/**
 * Renderiza subtotal, envío y total al pie del carrito.
 * Muestra "Gratis" si el envío está seleccionado y no tiene costo.
 */
function renderCartTotals(container) {
    const subtotal = getSubtotal();
    const delivery = getDeliveryCost();
    const total = getTotal();

    let totalHtml = "";
    totalHtml += '<div class="flex justify-between text-sm text-gray-400"><span>Subtotal</span><span>$' + subtotal.toLocaleString("es-AR") + '</span></div>';
    if (delivery > 0) {
        totalHtml += '<div class="flex justify-between text-sm text-gray-400"><span>Envío</span><span>$' + delivery.toLocaleString("es-AR") + '</span></div>';
    } else if (selectedDelivery && storeData.delivery_available) {
        totalHtml += '<div class="flex justify-between text-sm text-emerald-400"><span>Envío</span><span>Gratis</span></div>';
    }

    const totalRow = document.createElement("div");
    totalRow.className = "border-t border-white/5 pt-3 mt-3 space-y-1";
    totalRow.innerHTML = totalHtml;
    container.appendChild(totalRow);

    cartTotal.textContent = "$" + total.toLocaleString("es-AR");
}

/**
 * Construye el texto del mensaje de WhatsApp con el detalle completo del pedido.
 * @param {Array} items - Lista de items del carrito.
 * @param {boolean} isDelivery - True si es a domicilio.
 * @param {string} address - Dirección de entrega.
 * @param {string} reference - Referencia de la dirección.
 * @param {string} comment - Comentario del pedido.
 * @param {string} payLabel - Etiqueta del método de pago.
 * @param {number} deliveryCost - Costo de envío.
 * @param {number} subtotal - Subtotal del pedido.
 * @param {number} total - Total del pedido.
 * @returns {string} Mensaje formateado para WhatsApp.
 */
function buildWhatsAppMessage(items, isDelivery, address, reference, comment, payLabel, deliveryCost, subtotal, total) {
    let msg = "Hola, quisiera pedir:\n";
    items.forEach(it => {
        const label = it.variant ? it.name + " (" + it.variant.name + ")" : it.name;
        msg += "- " + it.qty + "x " + label + " ($" + (it.price * it.qty).toLocaleString("es-AR") + ")\n";
    });
    msg += "\n📍 " + (isDelivery ? "A domicilio" : "Retiro en local");
    if (isDelivery && address) { msg += "\n   Dirección: " + address; if (reference) msg += "\n   Referencia: " + reference; }
    if (comment) msg += "\n📝 " + comment;
    msg += "\n💳 Pago: " + payLabel;
    msg += "\n─ ─ ─ ─ ─ ─ ─\n";
    msg += "Subtotal: $" + subtotal.toLocaleString("es-AR") + "\n";
    if (deliveryCost > 0) msg += "Envío: $" + deliveryCost.toLocaleString("es-AR") + "\n";
    msg += "Total: $" + total.toLocaleString("es-AR");
    return msg;
}

/**
 * Envía tracking de clic en WhatsApp (fire-and-forget usando sendBeacon).
 * No bloquea la navegación del usuario.
 */
function sendWhatsAppTracking(total, payMethod) {
    try {
        navigator.sendBeacon(`${API_BASE}/api/track/whatsapp-click/${currentSlug}`,
            JSON.stringify({ cart_value: total, item_count: getCartCount(), payment_method: payMethod }));
    } catch (e) {
        console.warn("Pedime: error en tracking WhatsApp", e);
    }
}

/**
 * Limpia el carrito eliminando los datos de localStorage y cierra el drawer.
 * Se usa después de enviar el pedido por WhatsApp.
 */
function clearCartAndClose() {
    cart = {};
    localStorage.removeItem(storageKey());
    updateCartUI();
    closeCart();
}

/**
 * Handler principal del botón de WhatsApp.
 * Recolecta todos los datos del pedido, construye el mensaje, envía tracking y redirige a wa.me.
 */
whatsappBtn.onclick = () => {
    const entries = Object.entries(cart);
    if (!entries.length) return;
    if (!isStoreOpen()) return;

    const address = document.getElementById("delivery-address")?.value?.trim() || deliveryAddress;
    const reference = document.getElementById("delivery-reference")?.value?.trim() || deliveryReference;
    const comment = document.getElementById("order-comment")?.value?.trim() || orderComment;
    const isDelivery = selectedDelivery && storeData.delivery_available;
    const payMethod = selectedPayment === "transfer" ? "transfer" : "cash";
    const payLabel = payMethod === "transfer" ? "Transferencia" : "Efectivo";
    const phone = storeData.whatsapp.replace(/\D/g, "");
    const deliveryCost = isDelivery ? storeData.delivery_price : 0;
    const items = entries.map(([, item]) => ({ qty: item.qty, name: item.name, price: item.price, variant: item.variant }));
    const subtotal = items.reduce((sum, item) => sum + item.price * item.qty, 0);
    const total = subtotal + deliveryCost;

    const msg = buildWhatsAppMessage(items, isDelivery, address, reference, comment, payLabel, deliveryCost, subtotal, total);
    sendWhatsAppTracking(total, payMethod);
    window.open("https://wa.me/" + phone + "?text=" + encodeURIComponent(msg), "_blank");
    clearCartAndClose();
};

init();
