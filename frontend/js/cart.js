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
const STORAGE_KEY = "pedime_cart";

let storeData = null;
let cart = {};
let currentSlug = "";
let selectedDelivery = false;
let selectedPayment = null;
let deliveryAddress = "";
let deliveryReference = "";
let orderComment = "";

function saveCartState() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
            cart,
            selectedDelivery,
            selectedPayment,
            deliveryAddress,
            deliveryReference,
            orderComment,
        }));
    } catch {
        console.warn("Pedime: no se pudo guardar el estado del carrito en localStorage");
    }
}

function loadCartState() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (!saved) return;
        const data = JSON.parse(saved);
        if (data.cart) cart = data.cart;
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
 */
function isStoreOpen() {
    if (!storeData.opening_time || !storeData.closing_time) return true;
    const now = new Date();
    const mins = now.getHours() * 60 + now.getMinutes();
    const [openH, openM] = storeData.opening_time.split(":").map(Number);
    const [closeH, closeM] = storeData.closing_time.split(":").map(Number);
    const openMins = openH * 60 + openM;
    const closeMins = closeH * 60 + closeM;
    if (closeMins <= openMins) {
        // Cruza medianoche (ej: 20:00 - 02:00)
        return mins >= openMins || mins <= closeMins;
    }
    return mins >= openMins && mins <= closeMins;
}

/** Inicializa la app extrayendo el slug de la URL y cargando el menú. */
function init() {
    currentSlug = window.location.pathname.split("/menu/")[1];
    if (!currentSlug) { showError(); return; }
    loadCartState();
    fetchMenu();
}

/** Fetch a la API /api/menu/{slug} y renderiza los datos. */
async function fetchMenu() {
    try {
        const res = await fetch(`${API_BASE}/api/menu/${currentSlug}`);
        if (!res.ok) throw new Error("Not found");
        storeData = await res.json();
        // Convierte precios de string a número para operaciones matemáticas
        storeData.delivery_price = Number(storeData.delivery_price);
        for (const cat of storeData.categories) {
            for (const p of cat.products) {
                p.price = Number(p.price);
            }
        }
        renderMenu();
    } catch { showError(); }
}

/** Renderiza el menú completo: productos, categorías, búsqueda y carrito. */
function renderMenu() {
    document.getElementById("loading").classList.add("hidden");
    document.getElementById("store-name").textContent = storeData.store_name;
    document.title = storeData.store_name + " - Pedime";

    // Aplica el color personalizado del comercio
    const color = storeData.primary_color || "#10b981";
    document.documentElement.style.setProperty("--accent", color);

    // Logo del comercio
    const logo = document.getElementById("store-logo");
    if (storeData.logo_url) {
        logo.src = storeData.logo_url;
        logo.classList.remove("hidden");
        logo.onerror = () => logo.classList.add("hidden");
    } else {
        logo.classList.add("hidden");
    }

    // Metadatos: delivery y métodos de pago
    const meta = document.getElementById("store-meta");
    meta.innerHTML = "";
    const parts = [];

    if (storeData.delivery_available) {
        const cost = storeData.delivery_price > 0
            ? "$" + storeData.delivery_price.toLocaleString("es-AR")
            : "Gratis";
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

    const container = document.getElementById("menu-content");
    container.innerHTML = "";

    // Banner de modo lectura si el local está cerrado
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

    // Píldoras de navegación por categorías
    const pillsContainer = document.getElementById("category-pills");
    pillsContainer.innerHTML = "";

    storeData.categories.forEach((cat, idx) => {
        if (!cat.products.length) return;
        const sectionId = "cat-" + cat.id;
        const section = document.createElement("div");
        section.className = "space-y-3";
        section.id = sectionId;

        const title = document.createElement("h2");
        title.className = "text-sm font-semibold text-gray-400 uppercase tracking-wider px-1";
        title.textContent = cat.name;
        section.appendChild(title);

        // Píldora para scrollear a esta categoría
        const pill = document.createElement("button");
        pill.className = "shrink-0 px-3 py-1.5 rounded-full text-sm font-medium bg-[#1a1a1a] text-gray-400 hover:text-white hover:bg-white/10 transition border border-white/5";
        pill.textContent = cat.name;
        pill.onclick = () => {
            document.getElementById(sectionId).scrollIntoView({ behavior: "smooth", block: "start" });
        };
        pillsContainer.appendChild(pill);

        // Cards de productos
        cat.products.forEach((prod) => {
            const card = document.createElement("div");
            card.className = "product-card flex items-center justify-between bg-[#1a1a1a] rounded-xl p-4 border border-white/5 gap-3";
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

            const price = document.createElement("p");
            price.className = "text-emerald-400 font-bold mt-1";
            price.textContent = "$" + prod.price.toLocaleString("es-AR");
            info.appendChild(price);

            card.appendChild(info);

            if (isStoreOpen()) {
                // Controles de cantidad (solo si el local está abierto)
                const qtyDiv = document.createElement("div");
                qtyDiv.className = "flex items-center gap-2";

                if (cart[prod.id]) {
                    const minus = document.createElement("button");
                    minus.className = "w-8 h-8 rounded-full bg-white/10 text-white font-bold hover:bg-white/20 transition text-lg flex items-center justify-center";
                    minus.textContent = "\u2212";
                    minus.onclick = () => removeFromCart(prod.id);
                    qtyDiv.appendChild(minus);

                    const count = document.createElement("span");
                    count.className = "text-white font-bold w-6 text-center";
                    count.textContent = cart[prod.id].qty;
                    qtyDiv.appendChild(count);
                }

                const addBtn = document.createElement("button");
                addBtn.className = "w-8 h-8 rounded-full bg-emerald-500 text-white font-bold hover:bg-emerald-600 transition text-lg flex items-center justify-center";
                addBtn.textContent = "+";
                addBtn.onclick = () => addToCart(prod.id, prod.name, prod.price);
                qtyDiv.appendChild(addBtn);

                card.appendChild(qtyDiv);
            } else {
                // Badge "No disponible ahora" en modo lectura
                const badge = document.createElement("span");
                badge.className = "text-xs text-gray-500 shrink-0";
                badge.textContent = "No disponible ahora";
                card.appendChild(badge);
            }
            section.appendChild(card);
        });
        container.appendChild(section);
    });

    container.classList.remove("hidden");
    document.getElementById("search-section").classList.remove("hidden");
    document.getElementById("category-nav").classList.remove("hidden");
    updateCartUI();
}

// Filtro de búsqueda en tiempo real
document.getElementById("search-input").addEventListener("input", function() {
    const q = this.value.toLowerCase().trim();
    document.querySelectorAll(".product-card").forEach(card => {
        const name = card.getAttribute("data-name") || "";
        card.style.display = (!q || name.includes(q)) ? "" : "none";
    });
    // Oculta secciones de categoría sin productos visibles durante la búsqueda
    document.querySelectorAll("#menu-content > div[id^='cat-']").forEach(section => {
        const visibleCards = section.querySelectorAll('.product-card[style*="display: none"]');
        const allCards = section.querySelectorAll(".product-card");
        section.style.display = (allCards.length === visibleCards.length && q) ? "none" : "";
    });
});

/** Agrega un producto al carrito. */
function addToCart(id, name, price) {
    if (!isStoreOpen()) return;
    if (!cart[id]) cart[id] = { qty: 0, name, price };
    cart[id].qty++;
    saveCartState();
    renderMenu();
    showToast(name);
}

/** Reduce la cantidad o elimina un producto del carrito. */
function removeFromCart(id) {
    if (cart[id]) {
        cart[id].qty--;
        if (cart[id].qty <= 0) delete cart[id];
    }
    saveCartState();
    renderMenu();
}

/** Muestra un toast animado indicando que se agregó un producto. */
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

function getCartCount() {
    return Object.values(cart).reduce((sum, item) => sum + item.qty, 0);
}

function getSubtotal() {
    return Object.values(cart).reduce((sum, item) => sum + item.price * item.qty, 0);
}

function getDeliveryCost() {
    if (!selectedDelivery || !storeData.delivery_available) return 0;
    return storeData.delivery_price;
}

function getTotal() {
    return getSubtotal() + getDeliveryCost();
}

/** Actualiza la visibilidad del FAB del carrito según cantidad de items. */
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

function showError() {
    document.getElementById("loading").classList.add("hidden");
    document.getElementById("error").classList.remove("hidden");
}

// Referencias a elementos del drawer del carrito
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

cartBtn.onclick = () => openCart();
cartOverlay.onclick = () => closeCartAndSave();
cartClose.onclick = () => closeCartAndSave();

/** Abre el drawer del carrito y renderiza sus secciones. */
function openCart() {
    if (!selectedPayment) initPayment();
    renderDeliveryToggle();
    renderPaymentSelector();
    renderCommentSection();
    renderCartItems();
    cartDrawer.classList.remove("hidden");
    document.body.style.overflow = "hidden";
}

/** Cierra el drawer guardando los valores de los inputs. */
function closeCartAndSave() {
    deliveryAddress = document.getElementById("delivery-address")?.value || "";
    deliveryReference = document.getElementById("delivery-reference")?.value || "";
    orderComment = document.getElementById("order-comment")?.value || "";
    saveCartState();
    closeCart();
}

function closeCart() {
    cartDrawer.classList.add("hidden");
    document.body.style.overflow = "";
}

function initPayment() {
    if (storeData.payment_transfer) selectedPayment = "transfer";
    else if (storeData.payment_cash) selectedPayment = "cash";
}

/** Renderiza el selector de entrega (a domicilio / retiro en local). */
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

    const cost = storeData.delivery_price > 0
        ? " (+$" + storeData.delivery_price.toLocaleString("es-AR") + ")"
        : " (Gratis)";

    const label = document.createElement("p");
    label.className = "text-xs text-gray-500 mb-2 font-medium";
    label.textContent = "📍 ENTREGA";
    el.appendChild(label);

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

    // Campos de dirección (solo visibles si es delivery)
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
    el.classList.remove("hidden");

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

/** Renderiza los métodos de pago disponibles (transferencia / efectivo). */
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

/** Renderiza el textarea de comentario del pedido. */
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

/** Renderiza los items del carrito con cantidades, subtotales y totales. */
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

    whatsappBtn.disabled = false;
    whatsappBtn.classList.remove("opacity-50");

    // Estado del botón WhatsApp según modo lectura
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

    entries.forEach(([id, item]) => {
        const el = document.createElement("div");
        el.className = "flex items-center justify-between";

        const left = document.createElement("div");
        left.className = "flex-1";

        const name = document.createElement("p");
        name.className = "text-white font-medium";
        name.textContent = item.name;
        left.appendChild(name);

        const subtotal = document.createElement("p");
        subtotal.className = "text-sm text-gray-400";
        subtotal.textContent = item.qty + " x $" + item.price.toLocaleString("es-AR");
        left.appendChild(subtotal);

        el.appendChild(left);

        // Controles +/− para cada item en el carrito
        const right = document.createElement("div");
        right.className = "flex items-center gap-3";

        const minus = document.createElement("button");
        minus.className = "w-7 h-7 rounded-full bg-white/10 text-white font-bold hover:bg-white/20 transition flex items-center justify-center";
        minus.textContent = "\u2212";
        minus.onclick = () => { removeFromCart(parseInt(id)); renderCartItems(); updateCartUI(); };
        right.appendChild(minus);

        const qtySpan = document.createElement("span");
        qtySpan.className = "text-white font-bold w-5 text-center";
        qtySpan.textContent = item.qty;
        right.appendChild(qtySpan);

        const plus = document.createElement("button");
        plus.className = "w-7 h-7 rounded-full bg-emerald-500 text-white font-bold hover:bg-emerald-600 transition flex items-center justify-center";
        plus.textContent = "+";
        plus.onclick = () => { addToCart(parseInt(id), item.name, item.price); renderCartItems(); updateCartUI(); };
        right.appendChild(plus);

        el.appendChild(right);
        cartItems.appendChild(el);
    });

    // Totales
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
    cartItems.appendChild(totalRow);

    cartTotal.textContent = "$" + total.toLocaleString("es-AR");
}

/** Construye el mensaje de WhatsApp y abre wa.me con los datos del pedido. */
whatsappBtn.onclick = () => {
    const entries = Object.entries(cart);
    if (!entries.length) return;
    if (!isStoreOpen()) return;

    const address = document.getElementById("delivery-address")?.value?.trim() || deliveryAddress;
    const reference = document.getElementById("delivery-reference")?.value?.trim() || deliveryReference;
    const comment = document.getElementById("order-comment")?.value?.trim() || orderComment;
    const isDelivery = selectedDelivery && storeData.delivery_available;
    const payLabel = selectedPayment === "transfer" ? "Transferencia" : "Efectivo";
    const phone = storeData.whatsapp.replace(/\D/g, "");
    const deliveryCost = isDelivery ? Number(storeData.delivery_price) : 0;
    const items = entries.map(([, item]) => ({
        qty: item.qty, name: item.name, price: item.price,
    }));
    const subtotal = items.reduce((sum, item) => sum + item.price * item.qty, 0);
    const total = subtotal + deliveryCost;

    let msg = "Hola, quisiera pedir:\n";
    items.forEach(it => { msg += "- " + it.qty + "x " + it.name + " ($" + (it.price * it.qty).toLocaleString("es-AR") + ")\n"; });
    msg += "\n📍 " + (isDelivery ? "A domicilio" : "Retiro en local");
    if (isDelivery && address) { msg += "\n   Dirección: " + address; if (reference) msg += "\n   Referencia: " + reference; }
    if (comment) msg += "\n📝 " + comment;
    msg += "\n💳 Pago: " + payLabel;
    msg += "\n─ ─ ─ ─ ─ ─ ─\n";
    msg += "Subtotal: $" + subtotal.toLocaleString("es-AR") + "\n";
    if (deliveryCost > 0) msg += "Envío: $" + deliveryCost.toLocaleString("es-AR") + "\n";
    msg += "Total: $" + total.toLocaleString("es-AR");

    window.open("https://wa.me/" + phone + "?text=" + encodeURIComponent(msg), "_blank");
    cart = {};
    localStorage.removeItem(STORAGE_KEY);
    updateCartUI();
    closeCart();
};

init();
