'use client';

import { useState } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

interface PartyInfo {
  name: string;
  legal_name: string;
  address: string;
  country: string;
  tax_id: string;
  iban: string;
  bank_name: string;
  swift: string;
  email: string;
  phone: string;
  representative: string;
  representative_title: string;
}

interface WorkItem {
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
}

const emptyParty: PartyInfo = {
  name: '',
  legal_name: '',
  address: '',
  country: 'Ukraine',
  tax_id: '',
  iban: '',
  bank_name: '',
  swift: '',
  email: '',
  phone: '',
  representative: '',
  representative_title: '',
};

export default function DocumentsPage() {
  const [docType, setDocType] = useState<'act' | 'invoice'>('act');
  const [language, setLanguage] = useState('uk');
  const [format, setFormat] = useState('html');
  const [currency, setCurrency] = useState('USD');

  const [contractor, setContractor] = useState<PartyInfo>({
    ...emptyParty,
    name: 'Tech Solutions LLC',
    address: 'Kyiv, Ukraine',
  });
  const [client, setClient] = useState<PartyInfo>({
    ...emptyParty,
    name: 'Client Company',
    address: 'City, Country',
  });

  const [projectName, setProjectName] = useState('Repository Audit Services');
  const [contractNumber, setContractNumber] = useState('');
  const [docNumber, setDocNumber] = useState('');

  const [workDescription, setWorkDescription] = useState(
    'Comprehensive repository analysis and technical audit services'
  );
  const [deliverables, setDeliverables] = useState([
    'Technical audit report',
    'Repository health assessment',
    'Cost estimation',
    'Improvement recommendations',
  ]);

  const [items, setItems] = useState<WorkItem[]>([
    { description: 'Repository analysis services', quantity: 40, unit: 'hours', unit_price: 50 },
  ]);

  const [taxRate, setTaxRate] = useState(0);
  const [analysisId, setAnalysisId] = useState('');

  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultHtml, setResultHtml] = useState<string | null>(null);

  const calculateTotal = () => {
    const subtotal = items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0);
    const tax = subtotal * taxRate;
    return { subtotal, tax, total: subtotal + tax };
  };

  const handleAddItem = () => {
    setItems([...items, { description: '', quantity: 1, unit: 'hours', unit_price: 0 }]);
  };

  const handleRemoveItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleUpdateItem = (index: number, field: keyof WorkItem, value: string | number) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    setItems(newItems);
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    setResultHtml(null);

    const totals = calculateTotal();
    const today = new Date().toISOString().split('T')[0];

    try {
      let endpoint = '';
      let body: any = {};

      if (docType === 'act') {
        endpoint = '/api/financial/act';
        body = {
          act_number: docNumber || `ACT-${Date.now()}`,
          act_date: today,
          language,
          format,
          contractor,
          client,
          project_name: projectName,
          contract_number: contractNumber || undefined,
          work_period_start: today,
          work_period_end: today,
          work_description: workDescription,
          deliverables,
          items,
          currency,
          subtotal: totals.subtotal,
          tax_rate: taxRate,
          tax_amount: totals.tax,
          total: totals.total,
          analysis_id: analysisId || undefined,
        };
      } else {
        endpoint = '/api/financial/invoice';
        body = {
          invoice_number: docNumber || `INV-${Date.now()}`,
          invoice_date: today,
          due_date: today,
          language,
          format,
          contractor,
          client,
          project_name: projectName,
          contract_number: contractNumber || undefined,
          items,
          currency,
          subtotal: totals.subtotal,
          tax_rate: taxRate,
          tax_amount: totals.tax,
          total: totals.total,
          payment_terms: 'Net 30',
          analysis_id: analysisId || undefined,
        };
      }

      const res = await apiFetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const html = await res.text();
        setResultHtml(html);
      } else {
        const err = await res.json();
        setError(err.detail || 'Generation failed');
      }
    } catch (err) {
      setError('Failed to generate document');
    }

    setGenerating(false);
  };

  const handleDownload = () => {
    if (!resultHtml) return;
    const blob = new Blob([resultHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${docType}_${docNumber || Date.now()}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const totals = calculateTotal();

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Document Generator</h1>
        <p className="text-slate-600">
          Generate acts, invoices, and other financial documents.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="space-y-6">
          {/* Document Type */}
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <h3 className="font-semibold text-slate-900 mb-3">Document Type</h3>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: 'act', label: 'Act of Work', desc: 'Акт виконаних робіт' },
                { id: 'invoice', label: 'Invoice', desc: 'Рахунок-фактура' },
              ].map((type) => (
                <button
                  key={type.id}
                  onClick={() => setDocType(type.id as typeof docType)}
                  className={`p-3 rounded-lg border-2 text-left ${
                    docType === type.id
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="font-medium">{type.label}</div>
                  <div className="text-xs text-slate-500">{type.desc}</div>
                </button>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-2 mt-4">
              <div>
                <label className="text-xs text-slate-500">Language</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-2 py-1 border rounded"
                >
                  <option value="uk">Ukrainian</option>
                  <option value="en">English</option>
                  <option value="ru">Russian</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500">Currency</label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full px-2 py-1 border rounded"
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="UAH">UAH</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500">Doc Number</label>
                <input
                  type="text"
                  value={docNumber}
                  onChange={(e) => setDocNumber(e.target.value)}
                  placeholder="Auto"
                  className="w-full px-2 py-1 border rounded"
                />
              </div>
            </div>
          </div>

          {/* Parties */}
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <h3 className="font-semibold text-slate-900 mb-3">Parties</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-700">Contractor</label>
                <input
                  type="text"
                  value={contractor.name}
                  onChange={(e) => setContractor({ ...contractor, name: e.target.value })}
                  placeholder="Company name"
                  className="w-full px-3 py-2 border rounded mt-1"
                />
                <input
                  type="text"
                  value={contractor.address}
                  onChange={(e) => setContractor({ ...contractor, address: e.target.value })}
                  placeholder="Address"
                  className="w-full px-3 py-2 border rounded mt-1"
                />
                <div className="grid grid-cols-2 gap-2 mt-1">
                  <input
                    type="text"
                    value={contractor.iban}
                    onChange={(e) => setContractor({ ...contractor, iban: e.target.value })}
                    placeholder="IBAN"
                    className="px-3 py-2 border rounded"
                  />
                  <input
                    type="text"
                    value={contractor.bank_name}
                    onChange={(e) => setContractor({ ...contractor, bank_name: e.target.value })}
                    placeholder="Bank name"
                    className="px-3 py-2 border rounded"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Client</label>
                <input
                  type="text"
                  value={client.name}
                  onChange={(e) => setClient({ ...client, name: e.target.value })}
                  placeholder="Client name"
                  className="w-full px-3 py-2 border rounded mt-1"
                />
                <input
                  type="text"
                  value={client.address}
                  onChange={(e) => setClient({ ...client, address: e.target.value })}
                  placeholder="Client address"
                  className="w-full px-3 py-2 border rounded mt-1"
                />
              </div>
            </div>
          </div>

          {/* Project */}
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <h3 className="font-semibold text-slate-900 mb-3">Project Details</h3>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Project name"
              className="w-full px-3 py-2 border rounded mb-2"
            />
            <input
              type="text"
              value={contractNumber}
              onChange={(e) => setContractNumber(e.target.value)}
              placeholder="Contract number (optional)"
              className="w-full px-3 py-2 border rounded mb-2"
            />
            <textarea
              value={workDescription}
              onChange={(e) => setWorkDescription(e.target.value)}
              placeholder="Work description"
              rows={2}
              className="w-full px-3 py-2 border rounded"
            />
          </div>

          {/* Items */}
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-semibold text-slate-900">Line Items</h3>
              <button
                onClick={handleAddItem}
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                + Add Item
              </button>
            </div>
            <div className="space-y-2">
              {items.map((item, index) => (
                <div key={index} className="flex gap-2 items-center">
                  <input
                    type="text"
                    value={item.description}
                    onChange={(e) => handleUpdateItem(index, 'description', e.target.value)}
                    placeholder="Description"
                    className="flex-1 px-2 py-1 border rounded text-sm"
                  />
                  <input
                    type="number"
                    value={item.quantity}
                    onChange={(e) => handleUpdateItem(index, 'quantity', parseFloat(e.target.value) || 0)}
                    className="w-16 px-2 py-1 border rounded text-sm"
                  />
                  <select
                    value={item.unit}
                    onChange={(e) => handleUpdateItem(index, 'unit', e.target.value)}
                    className="w-20 px-2 py-1 border rounded text-sm"
                  >
                    <option value="hours">hours</option>
                    <option value="days">days</option>
                    <option value="units">units</option>
                  </select>
                  <input
                    type="number"
                    value={item.unit_price}
                    onChange={(e) => handleUpdateItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
                    placeholder="Rate"
                    className="w-20 px-2 py-1 border rounded text-sm"
                  />
                  <span className="w-24 text-right text-sm">
                    {(item.quantity * item.unit_price).toLocaleString()} {currency}
                  </span>
                  <button
                    onClick={() => handleRemoveItem(index)}
                    className="text-red-500 hover:text-red-700"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t space-y-1 text-right">
              <div className="text-slate-600">
                Subtotal: <span className="font-medium">{totals.subtotal.toLocaleString()} {currency}</span>
              </div>
              <div className="flex items-center justify-end gap-2">
                <span className="text-slate-600">Tax:</span>
                <input
                  type="number"
                  value={taxRate * 100}
                  onChange={(e) => setTaxRate(parseFloat(e.target.value) / 100 || 0)}
                  className="w-16 px-2 py-1 border rounded text-sm"
                />
                <span className="text-slate-600">%</span>
                <span className="font-medium">{totals.tax.toLocaleString()} {currency}</span>
              </div>
              <div className="text-lg font-semibold">
                Total: {totals.total.toLocaleString()} {currency}
              </div>
            </div>
          </div>

          {/* From Analysis */}
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <h3 className="font-semibold text-slate-900 mb-3">From Analysis (Optional)</h3>
            <input
              type="text"
              value={analysisId}
              onChange={(e) => setAnalysisId(e.target.value)}
              placeholder="Analysis ID to link document"
              className="w-full px-3 py-2 border rounded"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={generating || items.length === 0}
            className="w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 font-medium"
          >
            {generating ? 'Generating...' : `Generate ${docType === 'act' ? 'Act of Work' : 'Invoice'}`}
          </button>
        </div>

        {/* Preview */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold text-slate-900">Preview</h3>
            {resultHtml && (
              <button
                onClick={handleDownload}
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                Download HTML
              </button>
            )}
          </div>
          {resultHtml ? (
            <iframe
              srcDoc={resultHtml}
              className="w-full h-[600px] border rounded"
              title="Document Preview"
            />
          ) : (
            <div className="flex items-center justify-center h-96 text-slate-400">
              Generate a document to see preview
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
