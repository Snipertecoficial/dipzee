import React, { useState } from 'react';
import { CheckCircle2, XCircle, KeyRound } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const PROVIDERS = [
  { key: 'openai', keyField: 'openai_api_key', modelField: 'openai_model', label: 'OpenAI', placeholder: 'sk-...' },
  { key: 'anthropic', keyField: 'anthropic_api_key', modelField: 'anthropic_model', label: 'Anthropic (Claude)', placeholder: 'sk-ant-...' },
  { key: 'google', keyField: 'google_api_key', modelField: 'gemini_model', label: 'Google (Gemini)', placeholder: 'AIza...' },
];

function ProviderCard({ meta, status, busy, onSave }) {
  const [draft, setDraft] = useState({});

  const setField = (field, value) => setDraft((d) => ({ ...d, [field]: value }));

  const save = () => {
    const payload = {};
    if (draft[meta.keyField] !== undefined) payload[meta.keyField] = draft[meta.keyField];
    if (draft[meta.modelField] !== undefined) payload[meta.modelField] = draft[meta.modelField];
    if (Object.keys(payload).length === 0) return;
    onSave(payload);
    setDraft({});
  };

  return (
    <Card className="p-5" data-testid={`admin-ai-card-${meta.key}`}>
      <div className="flex items-center justify-between gap-2">
        <h4 className="font-heading font-semibold">{meta.label}</h4>
        {status.configured ? (
          <span className="inline-flex items-center gap-1 text-xs text-[var(--dz-buy)] shrink-0">
            <CheckCircle2 size={14} /> {status.source === 'admin' ? 'Configurado aqui' : 'Configurado via .env'}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs text-[var(--dz-muted)] shrink-0">
            <XCircle size={14} /> Não configurado
          </span>
        )}
      </div>
      {status.masked_key && (
        <p className="mt-1 text-xs text-[var(--dz-muted)] font-mono">{status.masked_key}</p>
      )}
      {status.source === 'env' && (
        <p className="mt-1 text-[11px] text-[var(--dz-muted)]">
          Vem do <code>.env</code> do servidor. Salvando uma chave aqui passa a valer no lugar dela.
        </p>
      )}
      <div className="mt-4 space-y-3">
        <div className="space-y-1">
          <Label className="text-xs">Chave de API</Label>
          <Input
            type="password"
            autoComplete="off"
            placeholder={meta.placeholder}
            value={draft[meta.keyField] ?? ''}
            onChange={(e) => setField(meta.keyField, e.target.value)}
            data-testid={`admin-ai-key-${meta.key}`}
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Modelo</Label>
          <Input
            placeholder={status.model || 'ex: gpt-4o'}
            value={draft[meta.modelField] ?? ''}
            onChange={(e) => setField(meta.modelField, e.target.value)}
            data-testid={`admin-ai-model-${meta.key}`}
          />
        </div>
        <Button
          size="sm"
          className="w-full bg-[var(--dz-primary)] text-white"
          disabled={busy}
          onClick={save}
          data-testid={`admin-ai-save-${meta.key}`}
        >
          {busy ? 'Salvando...' : 'Salvar'}
        </Button>
      </div>
    </Card>
  );
}

export function AdminAiTab({ aiConfig, onSaveProvider, onSaveActive, busy }) {
  if (!aiConfig) return null;

  return (
    <div className="space-y-6">
      <Card className="p-6 max-w-md">
        <div className="flex items-center gap-2">
          <KeyRound size={18} className="text-[var(--dz-primary)]" />
          <h3 className="font-heading font-semibold">Provedor de IA ativo</h3>
        </div>
        <p className="text-sm text-[var(--dz-muted)] mt-1">
          Qual IA o Analista Virtual usa para gerar as análises agora.
        </p>
        <div className="mt-4">
          <Select value={aiConfig.active_provider} onValueChange={onSaveActive}>
            <SelectTrigger data-testid="admin-ai-active-provider"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="anthropic">Anthropic (Claude)</SelectItem>
              <SelectItem value="openai">OpenAI</SelectItem>
              <SelectItem value="gemini">Google (Gemini)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      <div className="grid md:grid-cols-3 gap-5">
        {PROVIDERS.map((meta) => (
          <ProviderCard
            key={meta.key}
            meta={meta}
            status={aiConfig.providers[meta.key]}
            busy={busy === `ai-${meta.key}`}
            onSave={(payload) => onSaveProvider(meta.key, payload)}
          />
        ))}
      </div>
    </div>
  );
}
