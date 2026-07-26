import React from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, AlertTriangle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

// Shared loading / load-error state for list pages, so every page fails the
// same way (a clear "couldn't load — retry" instead of a blank screen or a
// misleading empty state) without duplicating the markup. Render it only when
// loading or error is truthy; the caller renders its own content/empty state
// otherwise:
//   {loading || error ? <ListState loading={loading} error={error} onRetry={load} /> : (...)}
export function ListState({ loading, error, onRetry }) {
  const { t } = useTranslation();
  if (loading) {
    return (
      <div className="mt-8 flex justify-center py-12" data-testid="list-loading">
        <Loader2 className="animate-spin text-[var(--dz-muted)]" />
      </div>
    );
  }
  if (error) {
    return (
      <Card className="mt-8 p-10 text-center" data-testid="list-error">
        <AlertTriangle className="mx-auto text-[var(--dz-sell)]" />
        <p className="mt-3 text-[var(--dz-muted)]">{t('common.loadError')}</p>
        {onRetry && (
          <Button variant="outline" onClick={onRetry} className="mt-4 border-[var(--dz-border)]">
            {t('common.retry')}
          </Button>
        )}
      </Card>
    );
  }
  return null;
}
