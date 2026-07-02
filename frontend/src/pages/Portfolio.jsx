import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Plus, Trash2, Wallet, TrendingUp, Coins, Download, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { FeatureGate } from '../components/FeatureGate';
import { SignalBadge } from '../components/SignalBadge';
import api from '../lib/api';

function fmt(v, cur = 'USD') {
  if (v == null) return '\u2014';
  try { return new Intl.NumberFormat(undefined, { style: 'currency', currency: cur, maximumFractionDigits: 2 }).format(v); }
  catch { return Number(v).toFixed(2); }
}
function pctColor(v) { return v == null ? 'var(--dz-muted)' : v >= 0 ? 'var(--dz-buy)' : 'var(--dz-sell)'; }

function PortfolioInner() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ ticker: '', quantity: '', avg_cost: '' });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { const res = await api.get('/portfolio'); setData(res.data); }
    catch (e) { setData({ positions: [], totals: {} }); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const add = async (e) => {
    e.preventDefault();
    if (!form.ticker || !form.quantity || !form.avg_cost) return;
    setBusy(true);
    try {
      const res = await api.post('/portfolio', {
        ticker: form.ticker.trim().toUpperCase(),
        quantity: parseFloat(form.quantity),
        avg_cost: parseFloat(form.avg_cost),
      });
      setData(res.data);
      setForm({ ticker: '', quantity: '', avg_cost: '' });
      toast.success(t('portfolio.saved'));
    } catch (e) { toast.error(t('auth.genericError')); }
    finally { setBusy(false); }
  };

  const remove = async (id) => {
    try { const res = await api.delete(`/portfolio/${id}`); setData(res.data); }
    catch (e) { toast.error(t('auth.genericError')); }
  };

  const exportCsv = () => {
    const rows = [['ticker', 'quantity', 'avg_cost', 'price', 'market_value', 'pnl', 'pnl_pct']];
    (data?.positions || []).forEach((p) => rows.push([p.ticker, p.quantity, p.avg_cost, p.price, p.market_value, p.pnl, p.pnl_pct]));
    const csv = rows.map((r) => r.join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a = document.createElement('a'); a.href = url; a.download = 'dipzee-portfolio.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  const totals = data?.totals || {};
  const cur = totals.currency || 'USD';

  return (
    <div data-testid="portfolio-inner">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('portfolio.title')}</h1>
          <p className="mt-1 text-[var(--dz-muted)]">{t('portfolio.subtitle')}</p>
        </div>
        <Button variant="outline" onClick={exportCsv} data-testid="portfolio-export-button" className="border-[var(--dz-border)]">
          <Download size={15} className="mr-2" /> CSV
        </Button>
      </div>

      <div className="mt-5 grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: t('portfolio.totalValue'), value: fmt(totals.market_value, cur), icon: Wallet },
          { label: t('portfolio.totalCost'), value: fmt(totals.cost_basis, cur), icon: Coins },
          { label: t('portfolio.totalPnl'), value: fmt(totals.pnl, cur), icon: TrendingUp, color: pctColor(totals.pnl) },
          { label: t('portfolio.annualIncome'), value: fmt(totals.annual_income, cur), icon: Coins },
        ].map((m, i) => (
          <Card key={i} className="p-4 border-[var(--dz-border)]">
            <div className="flex items-center gap-2 text-[var(--dz-muted)] text-xs"><m.icon size={14} /> {m.label}</div>
            <p className="mt-1 font-heading font-bold text-xl tnum" style={{ color: m.color || 'var(--dz-fg)' }} data-testid={`portfolio-metric-${i}`}>{m.value}</p>
          </Card>
        ))}
      </div>

      <Card className="mt-5 p-5 border-[var(--dz-border)]">
        <p className="font-heading font-semibold">{t('portfolio.addTitle')}</p>
        <form onSubmit={add} className="mt-3 grid grid-cols-1 sm:grid-cols-4 gap-3">
          <Input value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value })} placeholder={t('portfolio.ticker')} data-testid="portfolio-ticker-input" />
          <Input type="number" step="any" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} placeholder={t('portfolio.quantity')} data-testid="portfolio-quantity-input" />
          <Input type="number" step="any" value={form.avg_cost} onChange={(e) => setForm({ ...form, avg_cost: e.target.value })} placeholder={t('portfolio.avgCost')} data-testid="portfolio-cost-input" />
          <Button type="submit" disabled={busy} data-testid="portfolio-add-button" className="bg-[var(--dz-primary)] text-white">
            {busy ? <Loader2 size={16} className="animate-spin" /> : <><Plus size={16} className="mr-1" /> {t('portfolio.add')}</>}
          </Button>
        </form>
      </Card>

      <Card className="mt-5 overflow-hidden border-[var(--dz-border)]">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>{t('portfolio.ticker')}</TableHead>
              <TableHead className="text-right">{t('portfolio.quantity')}</TableHead>
              <TableHead className="text-right">{t('portfolio.avgCost')}</TableHead>
              <TableHead className="text-right">{t('portfolio.value')}</TableHead>
              <TableHead className="text-right">{t('portfolio.pnl')}</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? [1, 2, 3].map((i) => (
              <TableRow key={i}><TableCell colSpan={6}><Skeleton className="h-6 w-full" /></TableCell></TableRow>
            )) : (data?.positions || []).length === 0 ? (
              <TableRow><TableCell colSpan={6} className="text-center py-8 text-[var(--dz-muted)]">{t('portfolio.empty')}</TableCell></TableRow>
            ) : data.positions.map((p) => (
              <TableRow key={p.id} className="hover:bg-[var(--dz-primary-8)]">
                <TableCell>
                  <button className="font-medium hover:text-[var(--dz-primary)]" onClick={() => navigate(`/app/asset/${p.ticker}`)}>{p.ticker}</button>
                  <div className="text-xs text-[var(--dz-muted)] flex items-center gap-2">
                    {p.classification && <SignalBadge classification={p.classification} size="sm" />}
                  </div>
                </TableCell>
                <TableCell className="text-right tnum">{p.quantity}</TableCell>
                <TableCell className="text-right tnum">{fmt(p.avg_cost, p.currency)}</TableCell>
                <TableCell className="text-right tnum">{fmt(p.market_value, p.currency)}</TableCell>
                <TableCell className="text-right tnum font-medium" style={{ color: pctColor(p.pnl) }}>
                  {fmt(p.pnl, p.currency)}
                  {p.pnl_pct != null && <span className="block text-xs">{(p.pnl_pct * 100).toFixed(1)}%</span>}
                </TableCell>
                <TableCell className="text-right">
                  <button onClick={() => remove(p.id)} data-testid={`portfolio-remove-${p.ticker}`} className="text-[var(--dz-muted)] hover:text-[var(--dz-sell)] transition-colors"><Trash2 size={16} /></button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

export default function Portfolio() {
  const { t } = useTranslation();
  return (
    <div data-testid="portfolio-page">
      <FeatureGate feature="portfolio" title={t('portfolio.title')}>
        <PortfolioInner />
      </FeatureGate>
    </div>
  );
}
