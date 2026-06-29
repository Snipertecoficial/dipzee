import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

const TYPES = ['buy_zone', 'sell_zone', 'target_reached', 'price_below', 'price_above', 'score_threshold', 'dividend_change', 'daily_drop'];
const NEEDS_PRICE = ['price_below', 'price_above'];
const NEEDS_SCORE = ['score_threshold'];
const NEEDS_PCT = ['daily_drop'];

export function CreateAlertDialog({ defaultTicker = '', currency = 'USD', trigger, onCreated }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [ticker, setTicker] = useState(defaultTicker);
  const [type, setType] = useState('buy_zone');
  const [value, setValue] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const needsValue = NEEDS_PRICE.includes(type) || NEEDS_SCORE.includes(type) || NEEDS_PCT.includes(type);

  const valueLabel = NEEDS_PRICE.includes(type)
    ? t('alerts.valuePrice', { currency: user?.currency || currency })
    : NEEDS_SCORE.includes(type) ? t('alerts.valueScore')
    : t('alerts.valuePercent');

  const submit = async () => {
    if (!ticker.trim()) return;
    setSubmitting(true);
    try {
      const params = needsValue && value !== '' ? { value: Number(value) } : {};
      await api.post('/alerts', { ticker: ticker.trim().toUpperCase(), type, params });
      toast.success(t('alerts.created'));
      setOpen(false);
      setValue('');
      if (onCreated) onCreated();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      if (detail?.code === 'alert_limit') {
        toast.error(t('alerts.limitReached'));
      } else {
        toast.error(typeof detail === 'string' ? detail : t('auth.genericError'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || <Button data-testid="create-alert-open-button" variant="outline">{t('alerts.create')}</Button>}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>{t('alerts.create')}</DialogTitle></DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label>{t('alerts.ticker')}</Label>
            <Input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder={t('alerts.tickerPlaceholder')} data-testid="create-alert-ticker-input" />
          </div>
          <div className="space-y-1.5">
            <Label>{t('alerts.type')}</Label>
            <Select value={type} onValueChange={(v) => setType(v)}>
              <SelectTrigger data-testid="create-alert-type-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                {TYPES.map((ty) => (<SelectItem key={ty} value={ty}>{t(`alerts.types.${ty}`)}</SelectItem>))}
              </SelectContent>
            </Select>
          </div>
          {needsValue && (
            <div className="space-y-1.5">
              <Label>{valueLabel}</Label>
              <Input type="number" value={value} onChange={(e) => setValue(e.target.value)} data-testid="create-alert-value-input" />
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          <Button onClick={submit} disabled={submitting} data-testid="create-alert-submit-button" className="bg-[var(--dz-primary)] text-white">
            {submitting ? t('common.saving') : t('alerts.submit')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
