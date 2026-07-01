import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Newspaper, ExternalLink, RefreshCw } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '../lib/api';

export default function News() {
  const { t } = useTranslation();
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get('/news/market'); setNews(data.news || []); }
    catch (e) { /* noop */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const fmt = (d) => {
    try { return new Date(typeof d === 'number' ? d * 1000 : d).toLocaleString(); } catch (e) { return ''; }
  };

  return (
    <div>
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl flex items-center gap-2"><Newspaper size={24} />{t('news.title')}</h1>
          <p className="mt-1 text-[var(--dz-muted)]">{t('news.subtitle')}</p>
        </div>
        <Button variant="outline" onClick={load} data-testid="news-refresh-button"><RefreshCw size={16} className={loading ? 'animate-spin mr-2' : 'mr-2'} />{t('common.retry')}</Button>
      </div>

      {loading ? null : news.length === 0 ? (
        <Card className="mt-6 p-10 text-center text-[var(--dz-muted)]">{t('news.empty')}</Card>
      ) : (
        <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="market-news-grid">
          {news.map((n, i) => (
            <a key={n.id || i} href={n.url} target="_blank" rel="noopener noreferrer" data-testid="market-news-item">
              <Card className="overflow-hidden h-full hover:shadow-[var(--dz-elev-2)] transition-shadow flex flex-col">
                {n.image ? <img src={n.image} alt="" className="h-40 w-full object-cover" onError={(e) => { e.target.style.display = 'none'; }} /> : <div className="h-2 bg-[var(--dz-mint)]" />}
                <div className="p-4 flex-1 flex flex-col">
                  <p className="font-medium text-[var(--dz-fg)] leading-snug line-clamp-3">{n.headline}</p>
                  {n.summary && <p className="text-xs text-[var(--dz-muted)] mt-2 line-clamp-2">{n.summary}</p>}
                  <div className="mt-auto pt-3 flex items-center justify-between text-[11px] text-[var(--dz-muted)]">
                    <span className="flex items-center gap-1">{n.source} <ExternalLink size={11} /></span>
                    <span>{fmt(n.datetime)}</span>
                  </div>
                </div>
              </Card>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
