import { useEffect, useState } from 'react';
import { Package, Plus, Search, Edit, Trash2, Tag, RefreshCw, AlertTriangle, X } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

interface Product {
  id: string;
  sku: string;
  name: string;
  description: string | null;
  price: number;
  currency: string;
  stock: number;
  category: string | null;
  is_active: boolean;
  metadata: any;
  created_at: string;
  updated_at: string;
}

export default function Products() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');

  // Modal State
  const [isOpen, setIsOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formData, setFormData] = useState({
    sku: '',
    name: '',
    description: '',
    price: '',
    currency: 'INR',
    stock: '',
    category: '',
    is_active: true,
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/products`);
      if (!response.ok) throw new Error('Failed to fetch product catalog.');
      const data = await response.json();
      setProducts(data);
    } catch (err: any) {
      setError(err.message || 'Error loading products catalog.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const handleOpenAdd = () => {
    setEditingProduct(null);
    setFormData({
      sku: '',
      name: '',
      description: '',
      price: '',
      currency: 'INR',
      stock: '',
      category: '',
      is_active: true,
    });
    setFormError(null);
    setIsOpen(true);
  };

  const handleOpenEdit = (p: Product) => {
    setEditingProduct(p);
    setFormData({
      sku: p.sku,
      name: p.name,
      description: p.description || '',
      price: p.price.toString(),
      currency: p.currency,
      stock: p.stock.toString(),
      category: p.category || '',
      is_active: p.is_active,
    });
    setFormError(null);
    setIsOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);

    const payload = {
      sku: formData.sku.trim(),
      name: formData.name.trim(),
      description: formData.description.trim() || null,
      price: parseFloat(formData.price),
      currency: formData.currency,
      stock: parseInt(formData.stock, 10),
      category: formData.category.trim() || null,
      is_active: formData.is_active,
    };

    try {
      const url = editingProduct
        ? `${API_BASE_URL}/products/${editingProduct.id}`
        : `${API_BASE_URL}/products`;
      const method = editingProduct ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to save product.');
      }

      setIsOpen(false);
      fetchProducts();
    } catch (err: any) {
      setFormError(err.message || 'An error occurred.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to archive this product?')) return;
    try {
      const res = await fetch(`${API_BASE_URL}/products/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete product.');
      fetchProducts();
    } catch (err: any) {
      alert(err.message || 'Delete operation failed.');
    }
  };

  const categories = Array.from(new Set(products.map((p) => p.category).filter(Boolean)));

  const filteredProducts = products.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.sku.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesCategory = categoryFilter === 'ALL' || p.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6 text-[#F3F4F4]">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold font-display text-[#F3F4F4] flex items-center gap-2">
            <Package className="h-7 w-7 text-[#853953]" /> Merchant Catalog
          </h2>
          <p className="text-xs text-zinc-300 mt-1">
            Manage agent-queryable inventory, pricing configurations, and SKU availability.
          </p>
        </div>

        <button
          onClick={handleOpenAdd}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-[#853953] hover:bg-[#9c4362] text-xs font-bold text-white rounded-xl shadow-lg shadow-[#853953]/30 border border-[#853953]/50 transition"
        >
          <Plus className="h-4 w-4" />
          <span>Add New Product</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:max-w-md">
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-zinc-400" />
          <input
            type="text"
            placeholder="Search by SKU, product title, description..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#2C2C2C] border border-[#3a3a3a] rounded-xl pl-10 pr-4 py-2.5 text-xs text-[#F3F4F4] placeholder-zinc-400 focus:outline-none focus:border-[#853953]"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
          <span className="text-xs text-zinc-300 font-medium">Category:</span>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-[#2C2C2C] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-[#853953]"
          >
            <option value="ALL">All Categories</option>
            {categories.map((cat, idx) => (
              <option key={idx} value={cat!}>{cat}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Grid Display */}
      {loading ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] flex flex-col items-center justify-center space-y-4 shadow-xl">
          <RefreshCw className="h-8 w-8 text-[#853953] animate-spin" />
          <p className="text-xs text-zinc-400 font-mono">Querying merchant catalog...</p>
        </div>
      ) : error ? (
        <div className="bg-[#2C2C2C] p-8 rounded-2xl border border-rose-500/30 text-center space-y-3 shadow-xl">
          <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto" />
          <p className="text-xs text-rose-300">{error}</p>
        </div>
      ) : filteredProducts.length === 0 ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] text-center space-y-4 shadow-xl">
          <Package className="h-10 w-10 text-[#853953] mx-auto opacity-60" />
          <h3 className="text-base font-bold text-[#F3F4F4]">No Catalog Products Found</h3>
          <p className="text-xs text-zinc-400 max-w-sm mx-auto">No products match your filter criteria.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProducts.map((product) => (
            <div key={product.id} className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] flex flex-col justify-between space-y-4 shadow-xl hover:border-[#853953]/50 transition">
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[10px] bg-[#1c1c1c] border border-[#3a3a3a] px-2 py-0.5 rounded font-mono text-[#a85890] font-bold">
                      SKU: {product.sku}
                    </span>
                    <h3 className="text-base font-bold text-[#F3F4F4] mt-1 font-display">{product.name}</h3>
                  </div>
                  <span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                    product.is_active 
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                      : 'bg-zinc-800 text-zinc-400 border-zinc-700/50'
                  }`}>
                    {product.is_active ? 'In Stock' : 'Inactive'}
                  </span>
                </div>

                <p className="text-xs text-zinc-300 line-clamp-2 leading-relaxed">
                  {product.description || 'No product description configured.'}
                </p>
              </div>

              <div className="space-y-3 pt-2 border-t border-[#3a3a3a]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1 text-xs text-zinc-400">
                    <Tag className="h-3.5 w-3.5 text-[#853953]" />
                    <span>{product.category || 'General'}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-zinc-400 block font-mono">Base Price</span>
                    <span className="text-base font-extrabold text-[#F3F4F4]">₹{product.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-1">
                  <button
                    onClick={() => handleOpenEdit(product)}
                    className="p-2 bg-[#612D53]/40 border border-[#612D53] hover:bg-[#853953] rounded-xl text-[#F3F4F4] transition"
                    title="Edit Product"
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(product.id)}
                    className="p-2 bg-[#612D53]/40 border border-[#612D53] hover:bg-rose-950/40 hover:border-rose-800 hover:text-rose-400 rounded-xl text-zinc-300 transition"
                    title="Archive Product"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Product Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-[#2C2C2C] border border-[#3a3a3a] rounded-2xl shadow-2xl p-6 relative space-y-4 text-[#F3F4F4]">
            <div className="flex items-center justify-between border-b border-[#3a3a3a] pb-3">
              <h3 className="text-base font-bold font-display text-[#F3F4F4]">
                {editingProduct ? 'Edit Catalog Item' : 'Add Catalog Product'}
              </h3>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 hover:bg-[#612D53]/40 rounded-xl text-zinc-400 hover:text-white transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-300 mb-1 font-semibold">SKU Code</label>
                  <input
                    type="text"
                    required
                    value={formData.sku}
                    onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                    className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953] font-mono"
                    placeholder="SKU-WATCH-01"
                  />
                </div>
                <div>
                  <label className="block text-zinc-300 mb-1 font-semibold">Product Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953]"
                    placeholder="Smart Watch Pro"
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-300 mb-1 font-semibold">Description</label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953] resize-none font-sans"
                  placeholder="High performance AI wearable..."
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-zinc-300 mb-1 font-semibold">Price (INR)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                    className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953]"
                    placeholder="24999"
                  />
                </div>
                <div>
                  <label className="block text-zinc-300 mb-1 font-semibold">Stock Quantity</label>
                  <input
                    type="number"
                    required
                    value={formData.stock}
                    onChange={(e) => setFormData({ ...formData, stock: e.target.value })}
                    className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953]"
                    placeholder="50"
                  />
                </div>
                <div>
                  <label className="block text-zinc-300 mb-1 font-semibold">Category</label>
                  <input
                    type="text"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953]"
                    placeholder="Electronics"
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-[#3a3a3a] flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="px-4 py-2 bg-[#612D53]/40 border border-[#612D53] hover:bg-[#612D53]/80 rounded-xl text-xs font-semibold text-[#F3F4F4] transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-4 py-2 bg-[#853953] hover:bg-[#9c4362] text-white text-xs font-bold rounded-xl transition shadow-lg shadow-[#853953]/30 border border-[#853953]/50"
                >
                  {formSubmitting ? 'Saving...' : editingProduct ? 'Save Changes' : 'Create Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
