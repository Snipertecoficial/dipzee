import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity, ShieldCheck, Database, Calendar, Key, AlertTriangle, RefreshCcw } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '../../lib/api';

export function AdminHealthTab() {
  const { t } = useTranslation();
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadHealth = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/admin/health');
      setHealth(data);
    } catch (e) {
      // noop
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-heading font-semibold text-lg flex items-center gap-2">
          <Activity size={18} className="text-[var(--dz-primary)]" />
          Status e Saúde do Sistema
        </h3>
        <Button variant="outline" size="sm" onClick={loadHealth} disabled={loading} className="gap-1">
          <RefreshCcw size={14} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </Button>
      </div>

      {health && (
        <div className="grid md:grid-cols-3 gap-5">
          {/* MongoDB Health */}
          <Card className="p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-[var(--dz-muted)] uppercase tracking-wide">Banco de Dados</span>
                <Database size={20} className={health.db_connected ? 'text-[var(--dz-buy)]' : 'text-[var(--dz-sell)]'} />
              </div>
              <div className="space-y-1">
                <p className="text-2xl font-bold font-heading">{health.db_connected ? 'Conectado' : 'Desconectado'}</p>
                {health.db_connected && (
                  <p className="text-sm text-[var(--dz-muted)]">Latência do Ping: <span className="font-bold text-[var(--dz-primary)] tnum">{health.db_latency_ms} ms</span></p>
                )}
              </div>
            </div>
            {!health.db_connected && (
              <div className="mt-4 flex items-center gap-1.5 text-xs text-[var(--dz-sell)] font-semibold">
                <AlertTriangle size={14} /> Conexão do MongoDB instável
              </div>
            )}
          </Card>

          {/* Scheduler Health */}
          <Card className="p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-[var(--dz-muted)] uppercase tracking-wide">Agendador (Cron)</span>
                <Calendar size={20} className={health.scheduler_running ? 'text-[var(--dz-buy)]' : 'text-[var(--dz-sell)]'} />
              </div>
              <div className="space-y-1">
                <p className="text-2xl font-bold font-heading">{health.scheduler_running ? 'Executando' : 'Parado'}</p>
                <p className="text-sm text-[var(--dz-muted)]">APScheduler ativo para tarefas de background</p>
              </div>
            </div>
          </Card>

          {/* Upstream Provider */}
          <Card className="p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-[var(--dz-muted)] uppercase tracking-wide">Provedor de Mercado</span>
                <ShieldCheck size={20} className="text-[var(--dz-primary)]" />
              </div>
              <div className="space-y-1">
                <p className="text-2xl font-bold font-heading uppercase">{health.provider}</p>
                <p className="text-sm text-[var(--dz-muted)]">
                  {health.provider !== 'yfinance' ? 'Acesso ao provedor configurado ativo' : 'Acesso fallback de emergência ativo'}
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {health && (
        <Card className="p-5">
          <h4 className="font-heading font-semibold text-base mb-4 flex items-center gap-1.5">
            <Key size={16} className="text-[var(--dz-primary)]" />
            Integridade das Chaves de API externas
          </h4>
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Finnhub API', key: 'finnhub_key_present' },
              { label: 'FMP API', key: 'fmp_key_present' },
              { label: 'Polygon API', key: 'polygon_key_present' },
              { label: 'Alpha Vantage', key: 'alphavantage_key_present' },
              { label: 'Twelve Data', key: 'twelvedata_key_present' },
              { label: 'Marketstack', key: 'marketstack_key_present' },
              { label: 'Stripe (Pagamentos)', key: 'stripe_key_present' },
              { label: 'Resend (Emails)', key: 'resend_key_present' },
            ].map((item, idx) => (
              <div key={idx} className="p-3 bg-[var(--dz-canvas)] rounded-lg border border-[var(--dz-border)] flex flex-col justify-between">
                <span className="text-xs font-semibold text-[var(--dz-muted)]">{item.label}</span>
                <span className={`mt-2 inline-flex items-center w-fit px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                  health[item.key] ? 'bg-green-100 text-green-800' : 'bg-rose-100 text-rose-800'
                }`}>
                  {health[item.key] ? 'Configurada' : 'Ausente'}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
