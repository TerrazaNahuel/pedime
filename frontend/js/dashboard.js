(function() {
    "use strict";

    // Almacena las variantes del producto que se está editando
    var currentVariants = window._currentVariants || [];
    window._currentVariants = currentVariants;

    /** Carga el Set de IDs de categorías expandidas desde sessionStorage. */
    function loadExpanded() {
        try { return new Set(JSON.parse(sessionStorage.getItem('pedime_exp') || '[]')); } catch (e) { console.warn("Pedime: error cargando categorías expandidas", e); return new Set(); }
    }
    /** Guarda el Set de IDs de categorías expandidas en sessionStorage. */
    function saveExpanded(set) {
        sessionStorage.setItem('pedime_exp', JSON.stringify([...set]));
    }

    /** Restaura el estado visual expandido/colapsado de cada categoría al cargar la página. */
    function restoreExpanded() {
        try {
            var e = loadExpanded();
            document.querySelectorAll('[id^="cat-group-"]').forEach(function(g) {
                var id = parseInt(g.id.replace('cat-group-','')), a = document.getElementById('cat-arrow-'+id);
                e.has(id) ? (g.style.display = '', a && (a.style.transform = 'rotate(0deg)')) : (g.style.display = 'none', a && (a.style.transform = 'rotate(-90deg)'));
            });
        } catch (ex) { console.warn("Pedime: error restaurando categorías expandidas", ex); }
    }

    /** Cambia entre las pestañas del dashboard: productos, categorías o configuración. */
    window.switchTab = function(tab) {
        document.getElementById('panel-productos').classList.toggle('hidden', tab !== 'productos');
        document.getElementById('panel-categorias').classList.toggle('hidden', tab !== 'categorias');
        document.getElementById('panel-config').classList.toggle('hidden', tab !== 'config');
        ['productos', 'categorias', 'config'].forEach(function(t) {
            var el = document.getElementById('tab-' + t);
            el.className = t === tab
                ? 'flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition bg-emerald-500 text-white'
                : 'flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition text-gray-400 hover:text-white';
        });
    };

    /** Abre un modal por ID, ocultando el scroll del body. */
    window.openModal = function(id) {
        document.getElementById(id).classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    /** Cierra un modal por ID y restaura el scroll del body. */
    window.closeModal = function(id) {
        document.getElementById(id).classList.add('hidden');
        document.body.style.overflow = '';
    };

    /**
     * Abre el modal de edición de producto con los datos existentes.
     * Expande automáticamente la categoría a la que pertenece el producto.
     */
    window.editProduct = function(id, name, description, price, categoryId, available, imageUrl, stock, variants, featured) {
        var exp = loadExpanded();
        exp.add(categoryId);
        saveExpanded(exp);
        document.getElementById('modal-title').textContent = 'Editar producto';
        document.getElementById('product-id').value = id;
        document.getElementById('product-name').value = name;
        document.getElementById('product-description').value = description;
        document.getElementById('product-price').value = price;
        document.getElementById('product-category').value = categoryId;
        document.getElementById('product-available').checked = available;
        document.getElementById('product-image').value = imageUrl || '';
        document.getElementById('product-stock').value = stock || 0;
        var cb = document.getElementById('product-featured');
        if (cb) cb.checked = !!featured;
        try {
            var v = JSON.parse(variants || "[]");
            currentVariants = Array.isArray(v) ? v : [];
        } catch (e) {
            console.warn("Pedime: error parseando variants en edit", e);
            currentVariants = [];
        }
        renderVariants();
        window.openModal('producto-modal');
    };

    /** Limpia el formulario de producto para crear uno nuevo (modal en blanco). */
    window.resetProductForm = function() {
        document.getElementById('modal-title').textContent = 'Nuevo producto';
        document.getElementById('product-id').value = '';
        document.getElementById('product-name').value = '';
        document.getElementById('product-description').value = '';
        document.getElementById('product-price').value = '';
        document.getElementById('product-image').value = '';
        document.getElementById('product-available').checked = true;
        currentVariants = [];
        renderVariants();
    };

    /** Agrega una variante vacía (nombre y precio) a la lista de variantes del producto actual. */
    window.addVariant = function() {
        currentVariants.push({ name: "", price: 0 });
        renderVariants();
    };

    /** Elimina una variante de la lista por su índice y re-renderiza. */
    window.removeVariant = function(index) {
        currentVariants.splice(index, 1);
        renderVariants();
    };

    /** Renderiza los inputs de nombre y precio para cada variante del producto. */
    function renderVariants() {
        var container = document.getElementById("variants-list");
        if (!container) return;
        container.innerHTML = "";
        currentVariants.forEach(function(v, i) {
            var row = document.createElement("div");
            row.className = "flex gap-2 items-center";
            var nameInput = document.createElement("input");
            nameInput.type = "text";
            nameInput.value = v.name;
            nameInput.placeholder = "Nombre";
            nameInput.className = "flex-1 bg-[#0a0a0a] border border-white/10 rounded-lg px-3 py-1.5 text-white text-sm";
            nameInput.onchange = function() { currentVariants[i].name = nameInput.value; syncVariants(); };
            var priceInput = document.createElement("input");
            priceInput.type = "number";
            priceInput.value = v.price;
            priceInput.placeholder = "Precio";
            priceInput.min = "0";
            priceInput.step = "0.01";
            priceInput.className = "w-24 bg-[#0a0a0a] border border-white/10 rounded-lg px-3 py-1.5 text-white text-sm";
            priceInput.onchange = function() { currentVariants[i].price = Number(priceInput.value); syncVariants(); };
            var removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "text-red-400 hover:text-red-300 text-sm px-2";
            removeBtn.textContent = "\u2715";
            removeBtn.onclick = function() { window.removeVariant(i); };
            row.appendChild(nameInput);
            row.appendChild(priceInput);
            row.appendChild(removeBtn);
            container.appendChild(row);
        });
        syncVariants();
    }

    /** Sincroniza el array de variantes con el input oculto del formulario como JSON. */
    function syncVariants() {
        var el = document.getElementById("product-variants");
        if (el) {
            el.value = currentVariants.length ? JSON.stringify(currentVariants) : "";
        }
    }

    /** Activa el modo edición inline de una categoría mostrando inputs. */
    window.editCategory = function(id) {
        document.getElementById('cat-name-' + id).classList.add('hidden');
        document.getElementById('cat-edit-group-' + id).classList.remove('hidden');
        document.getElementById('cat-input-' + id).focus();
        document.getElementById('cat-save-' + id).classList.remove('hidden');
        document.getElementById('cat-cancel-' + id).classList.remove('hidden');
    };

    /** Envía el formulario de edición de categoría para guardar los cambios. */
    window.saveCategory = function(id) {
        document.getElementById('cat-form-' + id).submit();
    };

    /** Cancela la edición inline de una categoría, restaurando el nombre original. */
    window.cancelCategory = function(id) {
        document.getElementById('cat-name-' + id).classList.remove('hidden');
        document.getElementById('cat-edit-group-' + id).classList.add('hidden');
        document.getElementById('cat-input-' + id).value = document.getElementById('cat-name-' + id).textContent.trim();
        document.getElementById('cat-save-' + id).classList.add('hidden');
        document.getElementById('cat-cancel-' + id).classList.add('hidden');
    };

    /** Expande o colapsa una categoría en el dashboard y persiste el estado. */
    window.toggleCategory = function(id) {
        var exp = loadExpanded();
        var group = document.getElementById('cat-group-' + id);
        var arrow = document.getElementById('cat-arrow-' + id);
        if (!group) return;
        var isHidden = group.style.display === 'none';
        group.style.display = isHidden ? '' : 'none';
        arrow.style.transform = isHidden ? 'rotate(0deg)' : 'rotate(-90deg)';
        if (isHidden) exp.add(id);
        else exp.delete(id);
        saveExpanded(exp);
    };

    if (!window._dashboardInit) {
        window._dashboardInit = true;

        // Restaurar categorías expandidas al cargar la página
        restoreExpanded();

        // Delegación de eventos: captura clics en elementos con data-action
        // Esto evita tener que asignar listeners individuales en HTML generado dinámicamente
        document.addEventListener('click', function(e) {
            var btn = e.target.closest('[data-action]');
            if (!btn) return;
            var action = btn.getAttribute('data-action');
            switch (action) {
                case 'switch-tab':
                    window.switchTab(btn.getAttribute('data-tab'));
                    break;
                case 'open-modal':
                    window.openModal(btn.getAttribute('data-target'));
                    break;
                case 'close-modal':
                    window.closeModal(btn.getAttribute('data-target'));
                    break;
                case 'toggle-category':
                    window.toggleCategory(parseInt(btn.getAttribute('data-id')));
                    break;
                case 'edit-category':
                    window.editCategory(parseInt(btn.getAttribute('data-id')));
                    break;
                case 'save-category':
                    window.saveCategory(parseInt(btn.getAttribute('data-id')));
                    break;
                case 'cancel-category':
                    window.cancelCategory(parseInt(btn.getAttribute('data-id')));
                    break;
                case 'add-variant':
                    window.addVariant();
                    break;
                case 'start-payment':
                    window.startPayment(btn.getAttribute('data-plan'));
                    break;
                case 'show-qr':
                    window.showQR();
                    break;
                case 'close-qr':
                    document.getElementById('qr-modal').classList.add('hidden');
                    document.body.style.overflow = '';
                    break;
            }
        });

        // Maneja clics en botones de edición de producto usando data attributes
        document.addEventListener('click', function(e) {
            var btn = e.target.closest('.edit-btn');
            if (!btn) return;
            var id = parseInt(btn.dataset.editId);
            var name = btn.dataset.editName || '';
            var description = btn.dataset.editDescription || '';
            var price = parseFloat(btn.dataset.editPrice) || 0;
            var categoryId = parseInt(btn.dataset.editCategory) || 0;
            var available = btn.dataset.editAvailable === 'true';
            var imageUrl = btn.dataset.editImage || '';
            var stock = parseInt(btn.dataset.editStock) || 0;
            var variants = btn.dataset.editVariants || '';
            var featured = btn.dataset.editFeatured === 'true';
            window.editProduct(id, name, description, price, categoryId, available, imageUrl, stock, variants, featured);
        });

        // Confirmación nativa para formularios con data-confirm
        document.addEventListener('submit', function(e) {
            var form = e.target;
            if (form.hasAttribute('data-confirm')) {
                if (!confirm(form.getAttribute('data-confirm'))) {
                    e.preventDefault();
                }
            }
        });

        // Cierra el modal al hacer clic fuera del contenido (en el backdrop)
        document.getElementById('producto-modal').addEventListener('click', function(e) {
            if (e.target === this) window.closeModal('producto-modal');
        });

        // Al abrir el modal de nuevo producto, resetea el formulario después de que el modal sea visible
        var newProductBtn = document.querySelector('[data-action="open-modal"][data-target="producto-modal"]');
        if (newProductBtn) {
            newProductBtn.addEventListener('click', function() {
                setTimeout(window.resetProductForm, 10);
            });
        }

        // Atajos de teclado: Enter guarda categoría, Escape la cancela
        document.querySelectorAll('[id^="cat-input-"]').forEach(function(input) {
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') { e.preventDefault(); window.saveCategory(parseInt(this.id.replace('cat-input-', ''))); }
                if (e.key === 'Escape') { window.cancelCategory(parseInt(this.id.replace('cat-input-', ''))); }
            });
        });

        // Antes de una petición HTMX, guarda el scroll actual y expande la categoría del producto
        document.addEventListener('htmx:beforeRequest', function(e) {
            window._savedScroll = window.scrollY;
            var elt = e.detail.elt;
            var form = elt.tagName === 'FORM' ? elt : elt.closest('form');
            if (!form) return;
            var catId = null;
            if (form.id === 'producto-form') {
                var sel = form.querySelector('[name="category_id"]');
                if (sel) catId = parseInt(sel.value);
            }
            if (form.dataset.categoryId) {
                catId = parseInt(form.dataset.categoryId);
            }
            if (catId && !isNaN(catId)) {
                var exp = loadExpanded();
                exp.add(catId);
                saveExpanded(exp);
            }
        });

        // Después de un swap HTMX, restaura el scroll y cierra el modal
        document.addEventListener('htmx:afterSwap', function(e) {
            window.scrollTo(0, window._savedScroll || 0);
            window.closeModal('producto-modal');
        });

        // Inicializa SortableJS para drag & drop en la lista de productos (reordenamiento)
        try {
            var productList = document.getElementById('product-list');
            if (productList) {
                new Sortable(productList, {
                    animation: 200,
                    handle: '.product-sort',
                    onEnd: function() {
                        var ids = Array.from(productList.querySelectorAll('.product-sort')).map(function(el) { return el.dataset.id; });
                        document.getElementById('product-order-input').value = ids.join(',');
                        document.getElementById('save-order-btn').closest('form').classList.remove('hidden');
                    }
                });
            }
        } catch (e) {
            console.warn("SortableJS no disponible, drag & drop desactivado:", e);
        }
    }

    /** Muestra el modal con el código QR del menú público. */
    window.showQR = function() {
        var modal = document.getElementById('qr-modal');
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        var container = document.getElementById('qrcode');
        container.innerHTML = '';
        var menuUrl = document.querySelector('[href^="/menu/"]');
        if (!menuUrl) return;
        var url = window.location.origin + menuUrl.getAttribute('href');
        new QRCode(container, { text: url, width: 200, height: 200 });
        setTimeout(function() {
            var canvas = container.querySelector('canvas');
            if (canvas) {
                document.getElementById('qr-download-btn').href = canvas.toDataURL('image/png');
            }
        }, 300);
    };

    // Cierra QR modal al hacer clic fuera
    document.addEventListener('click', function(e) {
        var modal = document.getElementById('qr-modal');
        if (e.target === modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    });

    /** Inicia el flujo de pago con Mercado Pago: crea una preferencia y redirige al checkout. */
    window.startPayment = async function(plan) {
        var btn = event.target;
        btn.disabled = true;
        btn.textContent = "Procesando...";
        var csrfEl = document.querySelector('input[name="csrf_token"]');
        var csrf = csrfEl ? csrfEl.value : "";
        try {
            var res = await fetch("/api/payments/create-preference", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ plan: plan, csrf_token: csrf }),
            });
            var data = await res.json();
            if (data.ok && data.init_point) {
                window.location.href = data.init_point;
            } else {
                alert("Error: " + (data.error || "No se pudo iniciar el pago"));
                btn.disabled = false;
                btn.textContent = plan === "vip_premium" ? "Contratar VIP Premium" : "Contratar VIP Básico";
            }
        } catch (e) {
            alert("Error de conexión: " + e.message);
            btn.disabled = false;
            btn.textContent = plan === "vip_premium" ? "Contratar VIP Premium" : "Contratar VIP Básico";
        }
    };
})();
