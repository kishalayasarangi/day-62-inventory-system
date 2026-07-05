let selectedProductId = null;
let transType = 'in';

async function loadStats() {
  const res = await fetch('/api/stats');
  const s = await res.json();
  document.getElementById('totalProducts').textContent = s.total;
  document.getElementById('lowStock').textContent = s.low_stock;
  document.getElementById('outStock').textContent = s.out_of_stock;
  document.getElementById('totalValue').textContent = '₹' + s.total_value.toLocaleString('en-IN');

  const sel = document.getElementById('categoryFilter');
  const current = sel.value;
  sel.innerHTML = '<option value="">All Categories</option>' +
    s.categories.map(c => `<option value="${c}" ${c === current ? 'selected' : ''}>${c}</option>`).join('');
}

async function loadProducts() {
  const search = document.getElementById('searchInput').value;
  const category = document.getElementById('categoryFilter').value;
  const res = await fetch(`/api/products?search=${encodeURIComponent(search)}&category=${encodeURIComponent(category)}`);
  const products = await res.json();

  document.getElementById('productCount').textContent = `${products.length} products`;

  const tbody = document.getElementById('productsBody');
  if (products.length === 0) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="9">No products found!</td></tr>';
    return;
  }

  tbody.innerHTML = products.map(p => {
    const value = (p.quantity * p.price).toLocaleString('en-IN', { maximumFractionDigits: 0 });
    let statusCls, statusLabel;
    if (p.quantity === 0) { statusCls = 'stock-out'; statusLabel = 'Out of Stock'; }
    else if (p.quantity <= p.min_stock) { statusCls = 'stock-low'; statusLabel = 'Low Stock'; }
    else { statusCls = 'stock-ok'; statusLabel = 'In Stock'; }

    return `
      <tr>
        <td><strong>${p.name}</strong></td>
        <td style="font-family:monospace;color:#c084fc;">${p.sku}</td>
        <td>${p.category}</td>
        <td><strong>${p.quantity}</strong> ${p.unit}</td>
        <td>${p.min_stock} ${p.unit}</td>
        <td>₹${p.price.toLocaleString('en-IN')}</td>
        <td>₹${value}</td>
        <td><span class="stock-badge ${statusCls}">${statusLabel}</span></td>
        <td>
          <div class="action-btns">
            <button class="btn-in" onclick="openTrans(${p.id}, '${p.name}', 'in')">📥 In</button>
            <button class="btn-out" onclick="openTrans(${p.id}, '${p.name}', 'out')">📤 Out</button>
            <button class="btn-del" onclick="deleteProduct(${p.id})">✕</button>
          </div>
        </td>
      </tr>`;
  }).join('');
}

async function addProduct() {
  const name = document.getElementById('pName').value.trim();
  if (!name) { alert('Enter product name!'); return; }

  const res = await fetch('/api/products', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      category: document.getElementById('pCategory').value.trim() || 'General',
      sku: document.getElementById('pSku').value.trim(),
      quantity: document.getElementById('pQty').value,
      min_stock: document.getElementById('pMinStock').value,
      unit: document.getElementById('pUnit').value.trim() || 'units',
      price: document.getElementById('pPrice').value
    })
  });

  const data = await res.json();
  if (data.error) { alert(data.error); return; }

  hideAddForm();
  loadProducts();
  loadStats();
  loadTransactions();
}

async function deleteProduct(id) {
  if (!confirm('Delete this product and all its transactions?')) return;
  await fetch(`/api/products/${id}`, { method: 'DELETE' });
  loadProducts();
  loadStats();
  loadTransactions();
}

function openTrans(id, name, type) {
  selectedProductId = id;
  transType = type;
  document.getElementById('transModalTitle').textContent =
    `${type === 'in' ? '📥 Stock In' : '📤 Stock Out'} — ${name}`;
  document.getElementById('transQty').value = 1;
  document.getElementById('transNote').value = '';
  setTransType(type, document.getElementById(type === 'in' ? 'btnIn' : 'btnOut'));
  document.getElementById('transModal').classList.remove('hidden');
}

function setTransType(type, btn) {
  transType = type;
  document.querySelectorAll('.trans-type').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

async function submitTransaction() {
  const qty = parseInt(document.getElementById('transQty').value);
  const note = document.getElementById('transNote').value.trim();
  if (qty <= 0) { alert('Enter valid quantity!'); return; }

  const res = await fetch('/api/transaction', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: selectedProductId, type: transType, quantity: qty, note })
  });

  const data = await res.json();
  if (data.error) { alert(data.error); return; }

  hideTransModal();
  loadProducts();
  loadStats();
  loadTransactions();
}

function hideTransModal() {
  document.getElementById('transModal').classList.add('hidden');
  selectedProductId = null;
}

async function loadTransactions() {
  const res = await fetch('/api/transactions');
  const trans = await res.json();
  const tbody = document.getElementById('transBody');

  if (trans.length === 0) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No transactions yet</td></tr>';
    return;
  }

  tbody.innerHTML = trans.map(t => `
    <tr>
      <td>${t.product_name}</td>
      <td class="trans-${t.type}">${t.type === 'in' ? '📥 Stock In' : '📤 Stock Out'}</td>
      <td>${t.quantity} ${t.unit}</td>
      <td>${t.note || '—'}</td>
      <td style="color:#404050;font-size:0.78rem;">${t.created_at?.slice(0,16) || ''}</td>
    </tr>`).join('');
}

function showAddForm() {
  document.getElementById('addForm').classList.remove('hidden');
  document.getElementById('pName').focus();
}

function hideAddForm() {
  document.getElementById('addForm').classList.add('hidden');
  ['pName','pCategory','pSku','pUnit'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('pQty').value = '0';
  document.getElementById('pMinStock').value = '5';
  document.getElementById('pPrice').value = '0';
}

document.getElementById('transModal').addEventListener('click', e => {
  if (e.target === document.getElementById('transModal')) hideTransModal();
});

window.onload = () => {
  loadStats();
  loadProducts();
  loadTransactions();
};