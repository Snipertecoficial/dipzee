import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Search, Loader2 } from 'lucide-react';
import api from '../lib/api';

export function StockSearch({ onNavigate }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef(null);
  const timer = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const doSearch = useCallback((value) => {
    if (timer.current) clearTimeout(timer.current);
    if (!value || value.length < 1) { setResults([]); return; }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const { data } = await api.get('/assets/search', { params: { q: value } });
        setResults(data.results || []);
        setOpen(true);
      } catch (e) {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }, []);

  const go = (ticker) => {
    setOpen(false);
    setQ('');
    setResults([]);
    if (onNavigate) onNavigate();
    navigate(`/app/asset/${encodeURIComponent(ticker)}`);
  };

  const onSubmit = (e) => {
    e.preventDefault();
    if (q.trim()) go(q.trim().toUpperCase());
  };

  return (
    <div className="relative w-full max-w-md" ref={boxRef}>
      <form onSubmit={onSubmit}>
        <div className="flex items-center gap-2 rounded-[var(--dz-radius-pill,9999px)] border border-[var(--dz-border)] bg-white px-3 h-10 focus-within:ring-2 focus-within:ring-[var(--dz-focus)]">
          <Search size={16} className="text-[var(--dz-muted)]" />
          <input
            data-testid="stock-search-input"
            value={q}
            onChange={(e) => { setQ(e.target.value); doSearch(e.target.value); }}
            onFocus={() => results.length && setOpen(true)}
            placeholder={t('nav.searchPlaceholder')}
            className="flex-1 bg-transparent outline-none text-sm text-[var(--dz-fg)] placeholder:text-[var(--dz-muted)]"
          />
          {loading && <Loader2 size={15} className="animate-spin text-[var(--dz-muted)]" />}
        </div>
      </form>
      {open && results.length > 0 && (
        <div className="absolute z-50 mt-2 w-full rounded-[14px] border border-[var(--dz-border)] bg-white shadow-[var(--dz-elev-2)] overflow-hidden">
          {results.map((r) => (
            <button
              key={r.ticker}
              type="button"
              data-testid="stock-search-result-item"
              onClick={() => go(r.ticker)}
              className="w-full text-left px-3 py-2.5 hover:bg-[rgba(15,20,36,0.04)] flex items-center justify-between"
            >
              <span className="font-medium text-sm text-[var(--dz-fg)]">{r.ticker}</span>
              <span className="text-xs text-[var(--dz-muted)] truncate ml-3 max-w-[60%]">{r.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
