/* =====================================================================
   StyleHub -- JavaScript version (one-page app)

   How it works:
     * The menu changes the address hash (#shop, #cart, ...). Each hash has a
       "view" function below that fetches JSON from the Python API
       (Files/API/api.py) and returns the HTML for that section.
     * Every form has data-action="..." -- submitting it runs the matching
       function in ACTIONS, which sends the change to the API with fetch().

   Path of one request (Place order):
     click -> ACTIONS.placeOrder -> fetch POST /api/orders -> api.py place_order()
     -> db.place_order() runs the SQL in one transaction -> JSON reply
     -> toast message + the Orders section is redrawn.
   ===================================================================== */

// ---------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------

// [tab id, menu label, subtitle, icon, who can see it]
const TABS = [
  ["shop",        "Shop",        "Clothing, shoes and accessories",        "shop",     "everyone"],
  ["cart",        "Cart",        "Review your items and check out",        "cart",     "customer"],
  ["orders",      "Orders",      "Your purchase history",                  "receipt",  "customer"],
  ["alterations", "Alterations", "Tailoring for any piece of clothing",    "scissors", "everyone"],
  ["board",       "Work board",  "Assign tailors and move jobs along",     "board",    "employee"],
  ["products",    "Products",    "Add, edit and remove products",          "tag",      "manager"],
  ["inventory",   "Inventory",   "Stock levels, suppliers and deliveries", "box",      "manager"],
  ["employees",   "Employees",   "Staff accounts and roles",               "users",    "manager"],
  ["reports",     "Reports",     "Business reports for decision making",   "chart",    "manager"],
  ["account",     "Account",     "Sign in, register or edit your profile", "user",     "everyone"],
];

const NAV_GROUPS = [
  ["Store",   ["shop", "cart", "orders", "alterations", "account"]],
  ["Staff",   ["board"]],
  ["Manager", ["products", "inventory", "employees", "reports"]],
];

const STATUSES = ["Received", "In Progress", "Ready for Pickup", "Completed"];
// Payment choices at checkout (same list as db.PAYMENT_METHODS)
const PAYMENT_METHODS = ["Credit Card", "Debit Card", "Cash", "Gift Card"];

const ICONS = {
  shop:     '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>',
  cart:     '<circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2 2h2l2.7 12.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L22 7H5.1"/>',
  receipt:  '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  scissors: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/>',
  board:    '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18"/>',
  tag:      '<path d="M12.6 2.6A2 2 0 0 0 11.2 2H4a2 2 0 0 0-2 2v7.2a2 2 0 0 0 .6 1.4l8.7 8.7a2.4 2.4 0 0 0 3.4 0l6.6-6.6a2.4 2.4 0 0 0 0-3.4Z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
  box:      '<path d="M21 8 12 3 3 8v8l9 5 9-5Z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  users:    '<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2M16 3.1a4 4 0 0 1 0 7.8M22 21v-2a4 4 0 0 0-3-3.9"/>',
  chart:    '<path d="M3 3v18h18"/><path d="M7 16v-4M12 16V8M17 16v-7"/>',
  user:     '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  logout:   '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
  search:   '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  check:    '<path d="M20 6 9 17l-5-5"/>',
  plus:     '<path d="M12 5v14M5 12h14"/>',
  trash:    '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
  edit:     '<path d="M17 3a2.8 2.8 0 0 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>',
  truck:    '<path d="M10 17h4V5H2v12h3M14 9h4l4 4v4h-2"/><circle cx="7.5" cy="17.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
  alert:    '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>',
  dollar:   '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  info:     '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  sparkle:  '<path d="m12 3 1.9 5.8L20 10l-6.1 1.2L12 17l-1.9-5.8L4 10l6.1-1.2Z"/>',
};

const COLOR_HEX = {
  white: "#f8fafc", black: "#1f2937", blue: "#3b82f6", navy: "#1e3a8a", red: "#dc2626",
  khaki: "#c3b091", charcoal: "#374151", gray: "#9ca3af", grey: "#9ca3af", green: "#16a34a",
  brown: "#8b5a2b", pink: "#f472b6", beige: "#e8dcc4", yellow: "#facc15", purple: "#7c3aed", teal: "#14b8a6",
};

// ---------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------

/** Escape text from the database before putting it into HTML. */
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;
const money = n => (n == null ? "" : "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const day = iso => (iso ? new Date(iso).toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" }) : "—");
const swatch = color => COLOR_HEX[(color || "").toLowerCase()] || "#14b8a6";
const slug = text => (text || "").toLowerCase().replaceAll(" ", "-");
const initials = name => (name || "?").charAt(0).toUpperCase();
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const columnLabel = name => name.replace(/([a-z])([A-Z])/g, "$1 $2");     // UnitsSold -> Units Sold
const options = (items, selected) =>
  items.map(v => `<option ${v === selected ? "selected" : ""}>${esc(v)}</option>`).join("");

const MONEY_COLUMN = /Revenue|Cost|Price|Profit|Spent|Value|Fee|Discount/;

/** Format one report value. Money columns always show cents (15 -> 15.00). */
function cell(value, column = "") {
  if (value == null) return "—";
  if (typeof value === "number") {
    return Number.isInteger(value) && !MONEY_COLUMN.test(column) ? value.toLocaleString("en-US")
      : value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (/^\d{4}-\d{2}-\d{2}T/.test(value)) return value.slice(0, 10);
  return esc(value);
}

function emptyState(iconName, title, text, actionHtml = "") {
  return `<div class="empty"><div class="e-icon">${icon(iconName)}</div><h3>${title}</h3><p>${text}</p>${actionHtml}</div>`;
}

function toast(message, kind = "success") {
  const el = document.createElement("div");
  el.className = `flash flash-${kind}`;
  el.innerHTML = `${icon(kind === "success" ? "check" : "alert")} ${esc(message)}`;
  document.getElementById("toasts").appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

// ---------------------------------------------------------------------
// Talking to the API
// ---------------------------------------------------------------------

/** Call the Python API. Throws an Error with the server's message if it fails. */
async function api(method, url, data) {
  const response = await fetch(url, {
    method,
    headers: data ? { "Content-Type": "application/json" } : {},
    body: data ? JSON.stringify(data) : undefined,
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(json.error || `Request failed (${response.status})`);
  return json;
}

// ---------------------------------------------------------------------
// App state
// ---------------------------------------------------------------------
const state = {
  user: null,            // { type, id, name, role } or null
  cartCount: 0,
  filters: {},           // shop search/filter/sort values
  reportKey: "sales",
  editProductId: null,
};

const isCustomer = () => state.user?.type === "customer";
const isEmployee = () => state.user?.type === "employee";
const isManager = () => isEmployee() && state.user.role === "Manager";
const canSee = who => ({ everyone: true, customer: isCustomer(), employee: isEmployee(), manager: isManager() })[who];

async function refreshSession() {
  const session = await api("GET", "/api/session");
  state.user = session.user;
  state.cartCount = session.cartCount;
}

// ---------------------------------------------------------------------
// Drawing the page
// ---------------------------------------------------------------------
let renderNumber = 0;

async function render() {
  const tabs = TABS.filter(t => canSee(t[4]));
  let tabId = location.hash.slice(1) || "shop";
  if (!tabs.some(t => t[0] === tabId)) tabId = "shop";
  const tab = tabs.find(t => t[0] === tabId);

  drawSidebar(tabs, tabId);
  drawTopbar(tab);
  document.title = `StyleHub · ${tab[1]}`;

  const content = document.getElementById("content");
  const myTurn = ++renderNumber;
  try {
    const html = await VIEWS[tabId]();
    if (myTurn === renderNumber) content.innerHTML = html;     // ignore out-of-date results
  } catch (err) {
    if (myTurn === renderNumber) {
      content.innerHTML = `<div class="card">${emptyState("alert", "Something went wrong", esc(err.message))}</div>`;
    }
  }
}

function drawSidebar(tabs, activeId) {
  const groups = NAV_GROUPS.map(([label, ids]) => {
    const links = tabs.filter(t => ids.includes(t[0])).map(([id, name, , iconName]) => `
      <a class="nav-link ${id === activeId ? "active" : ""}" href="#${id}">
        ${icon(iconName)} ${id === "account" && !state.user ? "Sign in" : name}
        ${id === "cart" && state.cartCount ? `<span class="nav-count">${state.cartCount}</span>` : ""}
      </a>`).join("");
    return links ? `<div class="nav-label">${label}</div>${links}` : "";
  }).join("");

  const userCard = state.user ? `
    <div class="sidebar-user">
      <span class="avatar">${initials(state.user.name)}</span>
      <div class="who"><div class="name">${esc(state.user.name)}</div><div class="role">${esc(state.user.role)}</div></div>
      <form data-action="logout" class="inline"><button class="icon-btn" title="Sign out" aria-label="Sign out">${icon("logout")}</button></form>
    </div>` : "";

  document.getElementById("sidebar").innerHTML = `
    <a class="brand" href="#shop"><span class="brand-mark">S</span><span class="brand-name">Style<span>Hub</span></span></a>
    <nav class="nav">${groups}</nav>
    ${userCard}`;
}

function drawTopbar(tab) {
  let action = "";
  if (isCustomer()) action = `<a class="btn btn-blue" href="#cart">${icon("cart")} Cart · ${state.cartCount}</a>`;
  else if (!state.user) action = `<a class="btn btn-primary" href="#account">${icon("user")} Sign in</a>`;
  document.getElementById("topbar").innerHTML = `
    <div><h1>${tab[1]}</h1><div class="subtitle">${tab[2]}</div></div>
    <div class="topbar-actions">${action}</div>`;
}

// =====================================================================
// VIEWS -- one async function per tab; each returns that tab's HTML
// =====================================================================
const VIEWS = {};

// ----------------------------- SHOP ---------------------------------
let filterOptions = null;

VIEWS.shop = async () => {
  const query = new URLSearchParams(Object.entries(state.filters).filter(([, v]) => v)).toString();
  const [products, opts] = await Promise.all([
    api("GET", "/api/products" + (query ? "?" + query : "")),
    filterOptions || api("GET", "/api/filters"),
  ]);
  filterOptions = opts;
  const f = state.filters;

  const hero = state.user ? "" : `
    <section class="hero">
      <h2>Clothes that fit like they were made for you.</h2>
      <p>Shop men's, women's and children's clothing and accessories, then let our tailors hem, take in or adjust anything you own.</p>
      <div class="form-actions">
        <a class="btn" href="#account">Sign in to shop</a>
        <a class="btn btn-outline-light" href="#alterations">${icon("scissors")} Alteration services</a>
      </div>
    </section>`;

  const sortChoices = [["", "Name (A–Z)"], ["price_asc", "Price: low to high"], ["price_desc", "Price: high to low"], ["popular", "Most popular"]]
    .map(([v, label]) => `<option value="${v}" ${f.sort === v ? "selected" : ""}>${label}</option>`).join("");

  const filterBar = `
    <section class="card"><div class="card-body">
      <form data-action="search" class="filter-bar">
        <label class="field search"><span>Search</span>
          <div class="input-icon">${icon("search")}<input name="text" value="${esc(f.text)}" placeholder="Product name or brand"></div></label>
        <label class="field"><span>Category</span><select name="category"><option value="">All</option>${options(opts.categories, f.category)}</select></label>
        <label class="field"><span>Size</span><select name="size"><option value="">All</option>${options(opts.sizes, f.size)}</select></label>
        <label class="field"><span>Color</span><select name="color"><option value="">All</option>${options(opts.colors, f.color)}</select></label>
        <label class="field"><span>Min $</span><input name="min_price" type="number" step="0.01" min="0" value="${esc(f.min_price)}"></label>
        <label class="field"><span>Max $</span><input name="max_price" type="number" step="0.01" min="0" value="${esc(f.max_price)}"></label>
        <label class="field"><span>Sort by</span><select name="sort">${sortChoices}</select></label>
        <div class="form-actions">
          <button class="btn btn-primary">Apply</button>
          <button class="btn" type="button" data-click="resetFilters">Reset</button>
        </div>
      </form>
    </div></section>`;

  const resultLine = `
    <div class="result-line">
      <span><strong>${products.length}</strong> ${products.length === 1 ? "product" : "products"}</span>
      ${isEmployee() ? '<span class="small">Browsing as staff — sign in as a customer to buy.</span>' : ""}
    </div>`;

  const cards = products.map(p => {
    let stock = "";
    if (p.QuantityInStock === 0) stock = '<span class="badge badge-red stock">Sold out</span>';
    else if (p.QuantityInStock <= p.ReorderPoint) stock = `<span class="badge badge-amber stock">Only ${p.QuantityInStock} left</span>`;
    const addForm = isCustomer() && p.QuantityInStock > 0 ? `
      <form data-action="addToCart" class="add-form">
        <input type="hidden" name="productId" value="${p.ProductID}">
        <input class="input input-sm" type="number" name="quantity" value="1" min="1" max="${p.QuantityInStock}" aria-label="Quantity">
        <button class="btn btn-primary btn-sm">${icon("cart")} Add to cart</button>
      </form>` : "";
    return `
      <article class="product">
        <div class="product-art">
          <span class="chip cat">${esc(p.CategoryName)}</span>${stock}
          <span class="swatch" style="background:${swatch(p.Color)}"></span>
        </div>
        <div class="product-body">
          <div class="product-brand">${esc(p.Brand)}</div>
          <div class="product-name">${esc(p.ProductName)}</div>
          <div class="product-meta">
            <span class="chip">Size ${esc(p.Size)}</span>
            <span class="chip"><span class="chip-dot" style="background:${swatch(p.Color)}"></span>${esc(p.Color)}</span>
          </div>
          <div class="product-foot"><span class="price">${money(p.PricePerUnit)}</span><span class="sold">${p.UnitsSold} sold</span></div>
          ${addForm}
        </div>
      </article>`;
  }).join("");

  const grid = products.length ? `<div class="product-grid">${cards}</div>`
    : `<div class="card">${emptyState("search", "No products match those filters", "Try a different search or reset the filters.")}</div>`;

  return hero + filterBar + resultLine + grid;
};

// ----------------------------- CART ---------------------------------
VIEWS.cart = async () => {
  const cart = await api("GET", "/api/cart");
  if (!cart.length) {
    return `<div class="card">${emptyState("cart", "Your cart is empty", "Find something you like in the shop.",
      `<a class="btn btn-primary" href="#shop">${icon("shop")} Go to shop</a>`)}</div>`;
  }
  const total = cart.reduce((sum, item) => sum + item.LineTotal, 0);
  const lines = cart.map(item => `
    <div class="line-item">
      <span class="swatch-sm" style="background:${swatch(item.Color)}"></span>
      <div class="info">
        <div class="title">${esc(item.ProductName)}</div>
        <div class="muted small">${esc(item.Brand)} · Size ${esc(item.Size)} · ${esc(item.Color)} · ${money(item.PricePerUnit)} each</div>
      </div>
      <form data-action="updateCart" class="qty-form">
        <input type="hidden" name="productId" value="${item.ProductID}">
        <input class="input input-sm" type="number" name="quantity" value="${item.Quantity}" min="0" max="${item.QuantityInStock}" aria-label="Quantity">
        <button class="btn btn-sm">Update</button>
      </form>
      <div class="line-total">${money(item.LineTotal)}</div>
      <form data-action="removeFromCart" class="inline">
        <input type="hidden" name="productId" value="${item.ProductID}">
        <button class="icon-btn btn-danger" title="Remove" aria-label="Remove ${esc(item.ProductName)}">${icon("trash")}</button>
      </form>
    </div>`).join("");
  const summary = cart.map(item =>
    `<div class="summary-row"><span>${item.Quantity} × ${esc(item.ProductName)}</span><span>${money(item.LineTotal)}</span></div>`).join("");

  return `
    <div class="grid-2">
      <section class="card">
        <div class="card-head"><h2>Items in your cart</h2><span class="spacer"></span><span class="muted">${plural(state.cartCount, "item")}</span></div>
        ${lines}
      </section>
      <aside class="card"><div class="card-body">
        <h2 class="section-title">Order summary</h2>
        ${summary}
        <div class="summary-total"><span class="muted">Total</span><strong>${money(total)}</strong></div>
        <form data-action="placeOrder" class="form-stack" style="margin-top:18px;">
          <h3 class="section-title">Payment</h3>
          <div class="form-grid">
            <label class="field"><span>Pay with</span>
              <select name="paymentMethod" required>${PAYMENT_METHODS.map(m => `<option>${m}</option>`).join("")}</select>
            </label>
            <label class="field"><span>Card last 4 digits</span>
              <input name="cardLastFour" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" placeholder="Cards only">
            </label>
          </div>
          <button class="btn btn-primary btn-lg btn-block">${icon("check")} Pay ${money(total)} &amp; place order</button>
        </form>
        <p class="muted small" style="margin:12px 0 0;">Placing the order saves it, records each item at today's price, lowers inventory, records your payment and empties your cart — all in one database transaction.</p>
      </div></aside>
    </div>`;
};

// ----------------------------- ORDERS -------------------------------
VIEWS.orders = async () => {
  const orders = await api("GET", "/api/orders");
  if (!orders.length) {
    return `<div class="card">${emptyState("receipt", "No orders yet", "Your purchases will appear here.",
      '<a class="btn btn-primary" href="#shop">Start shopping</a>')}</div>`;
  }
  return `<div class="stack">${orders.map((o, i) => `
    <details class="order-card" ${i === 0 ? "open" : ""}>
      <summary>
        <span class="order-num">#${o.OrderID}</span>
        <div>
          <div class="strong">Order #${o.OrderID}</div>
          <div class="muted small">Placed ${day(o.OrderDate)} · ${plural(o.Items.length, "item line")}</div>
          <div class="muted small">${o.PaymentMethod ? `Paid by ${esc(o.PaymentMethod)}${o.CardLastFour ? ` ending ${esc(o.CardLastFour)}` : ""}` : "Not paid yet"}</div>
        </div>
        ${o.CompletionDate ? '<span class="status status-completed">Confirmed</span>' : '<span class="status status-in-progress">Processing</span>'}
        <span class="amount">${money(o.OrderAmount)}</span>
      </summary>
      <ul class="order-items">
        ${o.Items.map(it => `<li><span>${it.Quantity} × ${esc(it.ProductName)} <span class="muted">@ ${money(it.UnitPrice)}</span></span><strong>${money(it.LineTotal)}</strong></li>`).join("")}
      </ul>
    </details>`).join("")}</div>`;
};

// ----------------------------- ALTERATIONS --------------------------
function stepper(status) {
  const current = STATUSES.indexOf(status);
  return `<div class="stepper">${STATUSES.map((s, i) => {
    const done = i < current || status === "Completed";
    const cls = done ? "done" : i === current ? "current" : "";
    return `<div class="step ${cls}"><div class="dot">${done ? icon("check") : ""}</div>${s}</div>`;
  }).join("")}</div>`;
}

VIEWS.alterations = async () => {
  const [services, mine] = await Promise.all([
    api("GET", "/api/services"),
    isCustomer() ? api("GET", "/api/my-alterations") : [],
  ]);

  const serviceCards = `
    <section class="card">
      <div class="card-head"><h2>Our services</h2><span class="spacer"></span><span class="muted">Bring in any piece of clothing — bought here or anywhere else.</span></div>
      <div class="card-body"><div class="service-grid">
        ${services.map(s => `
          <div class="service">
            <div class="s-icon">${icon("scissors")}</div>
            <h3>${esc(s.AlterationName)}</h3>
            <p>${esc(s.Description)}</p>
            <span class="s-price">${money(s.AlterationPrice)}</span>
          </div>`).join("")}
      </div></div>
    </section>`;

  if (!state.user) {
    return serviceCards + `<div class="callout">${icon("info")}<span><a href="#account">Sign in as a customer</a> to request an alteration and track its status.</span></div>`;
  }
  if (isEmployee()) {
    return serviceCards + `<div class="callout">${icon("info")}<span>Staff manage alteration orders on the <a href="#board">Work board</a>.</span></div>`;
  }

  const orders = mine.length ? mine.map(a => `
    <div class="alt-card">
      <div class="alt-top">
        <div class="info">
          <div class="title">${esc(a.GarmentDescription)}</div>
          <div class="muted small">#${a.AlterationOrderID} · ${esc(a.AlterationName)} · requested ${day(a.RequestDate)}
            · ${a.Tailor ? "Tailor: " + esc(a.Tailor) : "Waiting for a tailor"}${a.PickupDate ? " · picked up " + day(a.PickupDate) : ""}</div>
        </div>
        <span class="fee">${money(a.ServiceFee)}</span>
        ${a.Status === "Received" ? `
          <form data-action="cancelAlteration" class="inline">
            <input type="hidden" name="id" value="${a.AlterationOrderID}">
            <button class="btn btn-sm btn-danger">Cancel</button>
          </form>` : ""}
      </div>
      ${stepper(a.Status)}
    </div>`).join("")
    : emptyState("scissors", "No alteration orders yet", "Request one with the form.");

  return serviceCards + `
    <div class="grid-2">
      <section class="card"><div class="card-head"><h2>My alteration orders</h2></div>${orders}</section>
      <aside class="card">
        <div class="card-head"><h2>Request an alteration</h2></div>
        <div class="card-body">
          <form data-action="requestAlteration" class="form-stack">
            <label class="field"><span>Garment to alter</span><input name="garment" required maxlength="255" placeholder="e.g. Navy suit pants, 34x32"></label>
            <label class="field"><span>Service</span>
              <select name="alterationId" required>
                ${services.map(s => `<option value="${s.AlterationID}">${esc(s.AlterationName)} — ${money(s.AlterationPrice)}</option>`).join("")}
              </select></label>
            <button class="btn btn-primary">${icon("plus")} Submit request</button>
            <p class="muted small" style="margin:0;">Drop the garment off at the store. We'll assign a tailor and you can follow each step here.</p>
          </form>
        </div>
      </aside>
    </div>`;
};

// ----------------------------- WORK BOARD ---------------------------
VIEWS.board = async () => {
  const { jobs, tailors } = await api("GET", "/api/board");
  const columns = STATUSES.map(status => {
    const cards = jobs.filter(j => j.Status === status).map(a => `
      <div class="job s-${slug(status)}">
        <div class="garment">${esc(a.GarmentDescription)}</div>
        <div class="meta">#${a.AlterationOrderID} · ${esc(a.AlterationName)}<br>${esc(a.CustomerName)}${a.Phone ? " · " + esc(a.Phone) : ""}<br>
          Requested ${day(a.RequestDate)}${a.PickupDate ? " · picked up " + day(a.PickupDate) : ""}</div>
        ${a.EmpID ? "" : '<div class="unassigned" style="margin-bottom:8px;">No tailor assigned</div>'}
        <form data-action="updateJob" class="job-form">
          <input type="hidden" name="id" value="${a.AlterationOrderID}">
          <select name="empId" class="select full" aria-label="Tailor">
            <option value="">— Unassigned —</option>
            ${tailors.map(t => `<option value="${t.EmpID}" ${a.EmpID === t.EmpID ? "selected" : ""}>${esc(t.FirstName)} ${esc(t.LastName)}</option>`).join("")}
          </select>
          <select name="status" class="select full" aria-label="Status">${options(STATUSES, a.Status)}</select>
          <label class="fee-field">$<input name="fee" type="number" step="0.01" min="0" value="${a.ServiceFee}" class="input" aria-label="Service fee"></label>
          <button class="btn btn-soft btn-sm">Save</button>
        </form>
      </div>`).join("");
    const count = jobs.filter(j => j.Status === status).length;
    return `
      <div class="column">
        <div class="column-head"><span class="status status-${slug(status)}">${status}</span><span class="count">${count}</span></div>
        <div class="column-cards">${cards || '<div class="column-empty">Nothing here</div>'}</div>
      </div>`;
  }).join("");

  return `
    <div class="callout">${icon("info")}<span>Pick a tailor and a new status, then save. A job can't move past <strong>Received</strong> until a tailor is assigned — the database's CHECK constraint enforces this. The pickup date is recorded automatically when a job is marked <strong>Completed</strong>.</span></div>
    <div class="kanban">${columns}</div>`;
};

// ----------------------------- PRODUCTS -----------------------------
VIEWS.products = async () => {
  const [products, categories] = await Promise.all([api("GET", "/api/products"), api("GET", "/api/categories")]);
  const ep = products.find(p => p.ProductID === state.editProductId) || null;

  const rows = products.map(p => `
    <tr>
      <td><div class="strong">${esc(p.ProductName)}</div><div class="muted small">${esc(p.Brand)} · #${p.ProductID}</div></td>
      <td><span class="chip"><span class="chip-dot" style="background:${swatch(p.Color)}"></span>${esc(p.CategoryName)} · ${esc(p.Size)}</span></td>
      <td class="num">${money(p.PricePerUnit)}</td>
      <td class="num">${p.QuantityInStock <= p.ReorderPoint ? `<span class="badge badge-amber">${p.QuantityInStock}</span>` : p.QuantityInStock}</td>
      <td class="num">${p.ReorderPoint}</td>
      <td><div class="actions">
        <button class="btn btn-sm" data-click="editProduct" data-id="${p.ProductID}">${icon("edit")} Edit</button>
        <form data-action="deleteProduct" class="inline">
          <input type="hidden" name="id" value="${p.ProductID}">
          <button class="btn btn-sm btn-danger" title="Delete">${icon("trash")}</button>
        </form>
      </div></td>
    </tr>`).join("");

  const categoryOptions = categories.map(c =>
    `<option value="${c.CategoryID}" ${ep && ep.CategoryID === c.CategoryID ? "selected" : ""}>${esc(c.CategoryName)} · ${esc(c.Size)} · ${esc(c.Color)}</option>`).join("");

  return `
    <div class="grid-2 wide">
      <section class="card">
        <div class="card-head"><h2>All products</h2><span class="spacer"></span><span class="muted">${products.length} total</span></div>
        <div class="table-wrap"><table class="table">
          <thead><tr><th>Product</th><th>Category</th><th class="num">Price</th><th class="num">Stock</th><th class="num">Reorder at</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table></div>
      </section>
      <div class="stack">
        <section class="card">
          <div class="card-head"><h2>${ep ? "Edit product #" + ep.ProductID : "Add a product"}</h2></div>
          <div class="card-body">
            <form data-action="saveProduct" class="form-stack">
              <input type="hidden" name="id" value="${ep ? ep.ProductID : ""}">
              <label class="field"><span>Product name</span><input name="productName" required maxlength="100" value="${esc(ep?.ProductName)}"></label>
              <label class="field"><span>Brand</span><input name="brand" required maxlength="50" value="${esc(ep?.Brand)}"></label>
              <label class="field"><span>Category · size · color</span><select name="categoryId" required>${categoryOptions}</select></label>
              <div class="form-grid">
                <label class="field"><span>Price</span><input name="price" type="number" step="0.01" min="0" required value="${ep ? ep.PricePerUnit : ""}"></label>
                <label class="field"><span>In stock</span><input name="quantity" type="number" min="0" required value="${ep ? ep.QuantityInStock : 0}"></label>
                <label class="field"><span>Reorder at</span><input name="reorderPoint" type="number" min="0" required value="${ep ? ep.ReorderPoint : 5}"></label>
              </div>
              <div class="form-actions">
                <button class="btn btn-primary">${icon("check")} ${ep ? "Save changes" : "Add product"}</button>
                ${ep ? '<button type="button" class="btn" data-click="cancelEdit">Cancel</button>' : ""}
              </div>
            </form>
          </div>
        </section>
        <section class="card">
          <div class="card-head"><h2>Add a category</h2></div>
          <div class="card-body">
            <form data-action="addCategory" class="form-stack">
              <label class="field"><span>Category name</span><input name="categoryName" required maxlength="50" placeholder="e.g. Shoes"></label>
              <div class="form-grid">
                <label class="field"><span>Size</span><input name="size" required maxlength="10" placeholder="e.g. 10"></label>
                <label class="field"><span>Color</span><input name="color" required maxlength="30" placeholder="e.g. Brown"></label>
              </div>
              <div class="form-actions"><button class="btn btn-soft">${icon("plus")} Add category</button></div>
            </form>
          </div>
        </section>
      </div>
    </div>`;
};

// ----------------------------- INVENTORY ----------------------------
VIEWS.inventory = async () => {
  const { lowStock, suppliers, purchases, products } = await api("GET", "/api/inventory");

  const lowList = lowStock.length ? `<div class="alert-list">${lowStock.map(r => {
    const pct = r.ReorderPoint ? Math.min(100, (r.QuantityInStock / r.ReorderPoint) * 100) : 100;
    return `
      <div class="alert-item">
        <div style="flex:1;min-width:0;">
          <div class="strong">${esc(r.ProductName)}</div>
          <div class="muted small">${esc(r.Size)} · ${esc(r.Color)} · last supplier ${esc(r.LastSupplier || "—")}${r.QtyOnOrder ? ` · <strong>${r.QtyOnOrder} on order</strong>` : ""}</div>
        </div>
        <div style="text-align:right;">
          <div class="small"><strong>${r.QuantityInStock}</strong> / ${r.ReorderPoint}</div>
          <div class="meter" title="Stock vs. reorder point"><span style="width:${pct}%"></span></div>
        </div>
        <div style="text-align:right;min-width:110px;">
          ${r.SuggestedOrderQty ? `<div class="small">Order <strong>${r.SuggestedOrderQty}</strong></div><div class="muted small">≈ ${money(r.EstimatedCost)}</div>`
                                : '<span class="badge badge-blue">Covered</span>'}
        </div>
      </div>`;
  }).join("")}</div>` : emptyState("check", "All stocked up", "Every product is above its reorder point.");

  const purchaseRows = purchases.map(p => `
    <tr>
      <td class="muted">${p.PurchaseID}</td>
      <td class="strong">${esc(p.SupplierName)}</td>
      <td>${esc(p.ProductName)}</td>
      <td class="num">${p.Quantity}</td>
      <td class="num">${money(p.PricePerUnit)}</td>
      <td class="num strong">${money(p.TotalCost)}</td>
      <td>${day(p.PurchaseDate)}</td>
      <td>${p.ReceivedDate ? `<span class="status status-completed">${day(p.ReceivedDate)}</span>` : `
        <form data-action="receivePurchase" class="inline">
          <input type="hidden" name="id" value="${p.PurchaseID}">
          <button class="btn btn-sm btn-soft">${icon("check")} Mark received</button>
        </form>`}</td>
    </tr>`).join("");

  const supplierRows = suppliers.map(s => {
    const formId = `sup-${s.SupplierID}`;
    return `
      <tr>
        <td><input class="input input-sm" name="supplierName" value="${esc(s.SupplierName)}" form="${formId}" required></td>
        <td><input class="input input-sm" name="contactFirst" value="${esc(s.ContactFirstName)}" form="${formId}"></td>
        <td><input class="input input-sm" name="contactLast" value="${esc(s.ContactLastName)}" form="${formId}"></td>
        <td><input class="input input-sm" name="contactEmail" type="email" value="${esc(s.ContactEmail)}" form="${formId}"></td>
        <td><form data-action="updateSupplier" id="${formId}" class="inline">
          <input type="hidden" name="id" value="${s.SupplierID}"><button class="btn btn-sm">Save</button>
        </form></td>
      </tr>`;
  }).join("");

  return `
    <div class="grid-2">
      <section class="card">
        <div class="card-head">${icon("alert")}<h2>Below reorder point</h2><span class="spacer"></span><span class="badge badge-amber">${plural(lowStock.length, "product")}</span></div>
        ${lowList}
      </section>
      <section class="card">
        <div class="card-head">${icon("truck")}<h2>Record a supplier purchase</h2></div>
        <div class="card-body">
          <form data-action="addPurchase" class="form-stack">
            <label class="field"><span>Supplier</span><select name="supplierId" required>${suppliers.map(s => `<option value="${s.SupplierID}">${esc(s.SupplierName)}</option>`).join("")}</select></label>
            <label class="field"><span>Product</span><select name="productId" required>${products.map(p => `<option value="${p.ProductID}">${esc(p.ProductName)} (${esc(p.Size)}, ${esc(p.Color)})</option>`).join("")}</select></label>
            <div class="form-grid">
              <label class="field"><span>Unit cost</span><input name="unitCost" type="number" step="0.01" min="0" required></label>
              <label class="field"><span>Quantity</span><input name="quantity" type="number" min="1" required></label>
            </div>
            <button class="btn btn-primary">${icon("plus")} Record purchase</button>
          </form>
        </div>
      </section>
    </div>

    <section class="card">
      <div class="card-head"><h2>Supplier purchases</h2><span class="spacer"></span><span class="muted">Mark a delivery received to add it to inventory</span></div>
      <div class="table-wrap"><table class="table">
        <thead><tr><th>#</th><th>Supplier</th><th>Product</th><th class="num">Qty</th><th class="num">Unit cost</th><th class="num">Total</th><th>Ordered</th><th>Received</th></tr></thead>
        <tbody>${purchaseRows}</tbody>
      </table></div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Suppliers</h2></div>
      <div class="table-wrap"><table class="table">
        <thead><tr><th>Supplier</th><th>Contact first</th><th>Contact last</th><th>Email</th><th></th></tr></thead>
        <tbody>${supplierRows}</tbody>
      </table></div>
      <div class="card-body" style="border-top:1px solid var(--line-2);">
        <form data-action="addSupplier" class="form-grid">
          <label class="field"><span>New supplier name</span><input name="supplierName" required maxlength="100"></label>
          <label class="field"><span>Contact first name</span><input name="contactFirst" maxlength="50"></label>
          <label class="field"><span>Contact last name</span><input name="contactLast" maxlength="50"></label>
          <label class="field"><span>Contact email</span><input name="contactEmail" type="email" maxlength="100"></label>
          <div class="form-actions"><button class="btn btn-soft">${icon("plus")} Add supplier</button></div>
        </form>
      </div>
    </section>`;
};

// ----------------------------- EMPLOYEES ----------------------------
VIEWS.employees = async () => {
  const { employees, roles } = await api("GET", "/api/employees");
  const badge = role => role === "Manager" ? "badge-blue" : role === "Tailor" ? "badge-teal" : "badge-amber";
  return `
    <div class="grid-2">
      <section class="card">
        <div class="card-head"><h2>Staff</h2><span class="spacer"></span><span class="muted">${employees.length} employees</span></div>
        <div class="table-wrap"><table class="table">
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Since</th></tr></thead>
          <tbody>${employees.map(e => `
            <tr>
              <td><div style="display:flex;align-items:center;gap:10px;"><span class="avatar" style="width:32px;height:32px;font-size:.85rem;">${initials(e.FirstName)}</span><span class="strong">${esc(e.FirstName)} ${esc(e.LastName)}</span></div></td>
              <td class="muted">${esc(e.Email)}</td>
              <td><span class="badge ${badge(e.Role)}">${esc(e.Role)}</span></td>
              <td>${day(e.CreatedAt)}</td>
            </tr>`).join("")}</tbody>
        </table></div>
      </section>
      <section class="card">
        <div class="card-head"><h2>Create an employee account</h2></div>
        <div class="card-body">
          <form data-action="addEmployee" class="form-stack">
            <div class="form-grid">
              <label class="field"><span>First name</span><input name="firstName" required maxlength="50"></label>
              <label class="field"><span>Last name</span><input name="lastName" required maxlength="50"></label>
            </div>
            <label class="field"><span>Email</span><input name="email" type="email" required maxlength="100"></label>
            <label class="field"><span>Role</span><select name="role">${options(roles)}</select></label>
            <label class="field"><span>Starting password</span><input name="password" type="password" required></label>
            <button class="btn btn-primary">${icon("plus")} Create account</button>
          </form>
        </div>
      </section>
    </div>`;
};

// ----------------------------- REPORTS ------------------------------
VIEWS.reports = async () => {
  const [stats, list, report] = await Promise.all([
    api("GET", "/api/stats"),
    api("GET", "/api/reports"),
    api("GET", `/api/reports/${state.reportKey}`),
  ]);
  const kpi = (iconName, tone, label, value) =>
    `<div class="kpi"><span class="k-icon ${tone}">${icon(iconName)}</span><div><div class="k-label">${label}</div><div class="k-value">${value}</div></div></div>`;
  const columns = report.rows.length ? Object.keys(report.rows[0]) : [];
  const isNum = col => typeof report.rows[0][col] === "number";

  const table = report.rows.length ? `
    <div class="table-wrap"><table class="table">
      <thead><tr>${columns.map(c => `<th class="${isNum(c) ? "num" : ""}">${columnLabel(c)}</th>`).join("")}</tr></thead>
      <tbody>${report.rows.map(row => `<tr>${columns.map(c =>
        `<td class="${typeof row[c] === "number" ? "num" : ""}">${cell(row[c], c)}</td>`).join("")}</tr>`).join("")}</tbody>
    </table></div>` : '<div class="empty"><h3>No rows right now</h3></div>';

  return `
    <div class="kpis">
      ${kpi("dollar", "blue", "Product sales", money(stats.SalesRevenue))}
      ${kpi("scissors", "teal", "Alteration revenue", money(stats.AlterationRevenue))}
      ${kpi("board", "blue", "Open alteration jobs", stats.OpenAlterations)}
      ${kpi("alert", "teal", "Products to reorder", stats.LowStockCount)}
    </div>
    <nav class="tabs" aria-label="Reports">
      ${list.map(r => `<button class="tab ${r.key === state.reportKey ? "active" : ""}" data-click="showReport" data-id="${r.key}">${esc(r.title)}</button>`).join("")}
    </nav>
    <section class="card">
      <div class="card-head"><h2>${esc(report.title)}</h2><span class="spacer"></span><span class="muted">${plural(report.rows.length, "row")}</span></div>
      <div class="card-body" style="padding-bottom:6px;">
        <div class="callout">${icon("sparkle")}<span><strong>What this tells the manager:</strong> ${esc(report.takeaway)}</span></div>
      </div>
      ${table}
    </section>`;
};

// ----------------------------- ACCOUNT ------------------------------
VIEWS.account = async () => {
  if (isCustomer()) {
    const p = await api("GET", "/api/profile");
    return `
      <div class="grid-2-even">
        <section class="card"><div class="card-body">
          <div class="profile-head" style="margin-bottom:20px;">
            <span class="avatar">${initials(p.FirstName)}</span>
            <div><h2 style="font-size:1.2rem;">${esc(p.FirstName)} ${esc(p.LastName)}</h2>
              <div class="muted">${esc(p.Email)} · member since ${day(p.CreatedAt)}</div></div>
          </div>
          <form data-action="updateProfile" class="form-stack">
            <div class="form-grid">
              <label class="field"><span>First name</span><input name="firstName" required maxlength="50" value="${esc(p.FirstName)}"></label>
              <label class="field"><span>Last name</span><input name="lastName" required maxlength="50" value="${esc(p.LastName)}"></label>
            </div>
            <label class="field"><span>Phone</span><input name="phone" maxlength="20" value="${esc(p.Phone)}"></label>
            <div class="form-actions"><button class="btn btn-primary">${icon("check")} Save profile</button></div>
          </form>
        </div></section>
        <section class="card"><div class="card-body stack" style="gap:12px;">
          <h2 class="section-title" style="margin:0;">Quick links</h2>
          <a class="btn" href="#orders">${icon("receipt")} Order history</a>
          <a class="btn" href="#alterations">${icon("scissors")} My alteration orders</a>
          <form data-action="logout"><button class="btn btn-block btn-danger">${icon("logout")} Sign out</button></form>
        </div></section>
      </div>`;
  }

  if (state.user) {
    return `
      <section class="card"><div class="card-body profile-head">
        <span class="avatar">${initials(state.user.name)}</span>
        <div><h2 style="font-size:1.2rem;">${esc(state.user.name)}</h2><div class="muted">Signed in as ${esc(state.user.role)}</div></div>
        <form data-action="logout" style="margin-left:auto;"><button class="btn btn-danger">${icon("logout")} Sign out</button></form>
      </div></section>`;
  }

  const demo = await api("GET", "/api/demo-accounts");
  return `
    <section class="card auth">
      <div class="auth-side">
        <h2>Welcome to StyleHub</h2>
        <p>One account for shopping, order history and alteration tracking.</p>
        <ul>
          <li>${icon("check")} Save items in your cart</li>
          <li>${icon("check")} See every past order</li>
          <li>${icon("check")} Follow your alteration from drop-off to pickup</li>
        </ul>
        <div class="demo-box">
          <strong>Demo sign-in</strong>
          <div class="small" style="color:#dbeafe;">Sample-data accounts use placeholder passwords — pick one for the presentation.</div>
          <form data-action="demoLogin">
            <select name="account" class="select" aria-label="Demo account">
              <optgroup label="Customers">${demo.customers.map(c => `<option value="customer:${c.CustID}">${esc(c.FirstName)} ${esc(c.LastName)}</option>`).join("")}</optgroup>
              <optgroup label="Employees">${demo.employees.map(e => `<option value="employee:${e.EmpID}">${esc(e.FirstName)} ${esc(e.LastName)} — ${esc(e.Role)}</option>`).join("")}</optgroup>
            </select>
            <button class="btn btn-block">Continue as this user</button>
          </form>
        </div>
      </div>
      <div class="auth-forms">
        <form data-action="login" class="form-stack">
          <h2 class="section-title" style="margin:0;">Sign in</h2>
          <label class="field"><span>Email</span><input name="email" type="email" required autocomplete="email"></label>
          <label class="field"><span>Password</span><input name="password" type="password" required autocomplete="current-password"></label>
          <button class="btn btn-primary">Sign in</button>
        </form>
        <div class="divider">NEW CUSTOMER?</div>
        <form data-action="register" class="form-stack">
          <div class="form-grid">
            <label class="field"><span>First name</span><input name="firstName" required maxlength="50"></label>
            <label class="field"><span>Last name</span><input name="lastName" required maxlength="50"></label>
          </div>
          <label class="field"><span>Email</span><input name="email" type="email" required maxlength="100"></label>
          <div class="form-grid">
            <label class="field"><span>Phone</span><input name="phone" maxlength="20"></label>
            <label class="field"><span>Password</span><input name="password" type="password" required autocomplete="new-password"></label>
          </div>
          <button class="btn btn-soft">Create account</button>
        </form>
      </div>
    </section>`;
};

// =====================================================================
// ACTIONS -- what each form does. `data` holds the form's fields.
// Each returns the message to show, or throws an Error to show instead.
// =====================================================================

/** After signing in, send each kind of user to the most useful tab. */
function goHome() {
  const target = isCustomer() ? "shop" : isManager() ? "reports" : isEmployee() ? "board" : "shop";
  if (location.hash === "#" + target) render(); else location.hash = target;
}

const ACTIONS = {
  // ---- account ----
  async login(data)       { const r = await api("POST", "/api/login", data); await refreshSession(); goHome(); return r.message; },
  async demoLogin(data)   { const r = await api("POST", "/api/demo-login", data); await refreshSession(); goHome(); return r.message; },
  async register(data, form) { const r = await api("POST", "/api/register", data); form.reset(); return r.message; },
  async logout()          { const r = await api("POST", "/api/logout"); await refreshSession(); filterOptions = null; location.hash = "shop"; render(); return r.message; },
  async updateProfile(data) { return (await api("PUT", "/api/profile", data)).message; },

  // ---- shop & cart ----
  async search(data)      { state.filters = data; await render(); },
  async addToCart(data)   { return (await api("POST", "/api/cart", data)).message; },
  async updateCart(data)  { return (await api("PUT", `/api/cart/${data.productId}`, data)).message; },
  async removeFromCart(data) { return (await api("DELETE", `/api/cart/${data.productId}`)).message; },
  async placeOrder(data)  { const r = await api("POST", "/api/orders", data); location.hash = "orders"; return r.message; },

  // ---- alterations ----
  async requestAlteration(data) { return (await api("POST", "/api/alterations", data)).message; },
  async cancelAlteration(data)  { return (await api("DELETE", `/api/alterations/${data.id}`)).message; },
  async updateJob(data)         { return (await api("PUT", `/api/board/${data.id}`, data)).message; },

  // ---- manager ----
  async saveProduct(data) {
    const r = data.id ? await api("PUT", `/api/products/${data.id}`, data) : await api("POST", "/api/products", data);
    state.editProductId = null; filterOptions = null;
    return r.message;
  },
  async deleteProduct(data) {
    if (!confirm("Delete this product?")) return;
    return (await api("DELETE", `/api/products/${data.id}`)).message;
  },
  async addCategory(data)     { filterOptions = null; return (await api("POST", "/api/categories", data)).message; },
  async addSupplier(data)     { return (await api("POST", "/api/suppliers", data)).message; },
  async updateSupplier(data)  { return (await api("PUT", `/api/suppliers/${data.id}`, data)).message; },
  async addPurchase(data)     { return (await api("POST", "/api/purchases", data)).message; },
  async receivePurchase(data) { return (await api("POST", `/api/purchases/${data.id}/receive`)).message; },
  async addEmployee(data)     { return (await api("POST", "/api/employees", data)).message; },
};

// Buttons that only change what is shown (no database change)
const CLICKS = {
  resetFilters()   { state.filters = {}; render(); },
  editProduct(id)  { state.editProductId = Number(id); render().then(() => window.scrollTo({ top: 0, behavior: "smooth" })); },
  cancelEdit()     { state.editProductId = null; render(); },
  showReport(key)  { state.reportKey = key; render(); },
};

// Actions that already redraw the page themselves
const SELF_RENDERING = ["login", "demoLogin", "logout", "search"];

// =====================================================================
// Event wiring
// =====================================================================
document.addEventListener("submit", async event => {
  const form = event.target.closest("form[data-action]");
  if (!form) return;
  event.preventDefault();

  const name = form.dataset.action;
  const data = Object.fromEntries(new FormData(form));     // includes inputs linked with form="..."
  const submitButton = form.querySelector("button");
  if (submitButton) submitButton.disabled = true;

  try {
    const message = await ACTIONS[name](data, form);
    if (message) toast(message);
    if (!SELF_RENDERING.includes(name)) {
      await refreshSession();          // cart count may have changed
      await render();
    }
  } catch (err) {
    toast(err.message, "error");
  } finally {
    if (submitButton) submitButton.disabled = false;
  }
});

document.addEventListener("click", event => {
  const el = event.target.closest("[data-click]");
  if (el) CLICKS[el.dataset.click](el.dataset.id);
});

window.addEventListener("hashchange", render);

// Start: find out who is signed in, then draw the page
refreshSession().catch(() => {}).finally(render);
