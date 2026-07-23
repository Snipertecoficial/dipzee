import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Landmark, Trash2, Plus, Loader2, ExternalLink } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { TH_CLASS, TD_CLASS } from './AdminShared';
import api from '../../lib/api';
import { toast } from 'sonner';

export function AdminAdsTab() {
  const { t } = useTranslation();
  const [ads, setAds] = useState([]);
  const [partnerName, setPartnerName] = useState('');
  const [description, setDescription] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [placement, setPlacement] = useState('sidebar');
  const [active, setActive] = useState(true);
  const [busy, setBusy] = useState(false);

  const loadAds = async () => {
    try {
      const { data } = await api.get('/admin/partner-ads');
      setAds(data.ads || []);
    } catch (e) {
      toast.error(t('admin.ads.toastLoadError'));
    }
  };

  useEffect(() => {
    loadAds();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!partnerName.trim() || !description.trim() || !targetUrl.trim()) return;
    setBusy(true);
    try {
      await api.post('/admin/partner-ads', {
        partner_name: partnerName.trim(),
        description: description.trim(),
        target_url: targetUrl.trim(),
        image_url: imageUrl.trim() || null,
        placement,
        active,
      });
      toast.success(t('admin.ads.toastCreated'));
      setPartnerName('');
      setDescription('');
      setTargetUrl('');
      setImageUrl('');
      loadAds();
    } catch (err) {
      toast.error(t('admin.ads.toastCreateError'));
    } finally {
      setBusy(false);
    }
  };

  const handleToggleActive = async (item) => {
    try {
      await api.put(`/admin/partner-ads/${item.id}`, {
        ...item,
        active: !item.active,
      });
      toast.success(t('admin.ads.toastStatusUpdated'));
      loadAds();
    } catch (err) {
      toast.error(t('admin.ads.toastUpdateError'));
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('admin.ads.confirmDelete'))) return;
    try {
      await api.delete(`/admin/partner-ads/${id}`);
      toast.success(t('admin.ads.toastDeleted'));
      loadAds();
    } catch (err) {
      toast.error(t('admin.ads.toastDeleteError'));
    }
  };

  const placementLabel = (p) => (
    p === 'sidebar' ? t('admin.ads.placementSidebar').split(' (')[0]
      : p === 'dashboard' ? t('admin.ads.placementDashboard').split(' (')[0]
        : t('admin.ads.placementAssetDetail')
  );

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      {/* Create form */}
      <Card className="p-5 lg:col-span-1 h-fit">
        <div className="flex items-center gap-2 mb-4">
          <Landmark size={18} className="text-[var(--dz-primary)]" />
          <h3 className="font-heading font-semibold text-lg">{t('admin.ads.newPartner')}</h3>
        </div>
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-[var(--dz-muted)] block mb-1">{t('admin.ads.partnerNameLabel')}</label>
            <Input
              value={partnerName}
              onChange={(e) => setPartnerName(e.target.value)}
              placeholder={t('admin.ads.partnerNamePh')}
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--dz-muted)] block mb-1">{t('admin.ads.adCopyLabel')}</label>
            <textarea
              className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('admin.ads.adCopyPh')}
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--dz-muted)] block mb-1">{t('admin.ads.targetUrlLabel')}</label>
            <Input
              type="url"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="https://broker.com/promo?ref=dipzee"
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--dz-muted)] block mb-1">{t('admin.ads.imageUrlLabel')}</label>
            <Input
              type="url"
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              placeholder="https://example.com/logo.png"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--dz-muted)] block mb-1">{t('admin.ads.placementLabel')}</label>
            <Select value={placement} onValueChange={setPlacement}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sidebar">{t('admin.ads.placementSidebar')}</SelectItem>
                <SelectItem value="dashboard">{t('admin.ads.placementDashboard')}</SelectItem>
                <SelectItem value="asset_detail">{t('admin.ads.placementAssetDetail')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="ad-active"
              checked={active}
              onChange={(e) => setActive(e.target.checked)}
              className="rounded border-[var(--dz-border)] text-[var(--dz-primary)] focus:ring-0"
            />
            <label htmlFor="ad-active" className="text-xs font-medium text-[var(--dz-muted)] cursor-pointer">{t('admin.activateNow')}</label>
          </div>
          <Button type="submit" className="w-full mt-2" disabled={busy}>
            {busy ? <Loader2 size={16} className="animate-spin mr-1" /> : <Plus size={16} className="mr-1" />}
            {t('admin.ads.createCta')}
          </Button>
        </form>
      </Card>

      {/* Ads list */}
      <Card className="p-5 lg:col-span-2 overflow-x-auto">
        <h3 className="font-heading font-semibold text-lg mb-4">{t('admin.partnersAndCampaigns')}</h3>
        {ads.length === 0 ? (
          <p className="text-sm text-[var(--dz-muted)] text-center py-8">{t('admin.ads.noAdsYet')}</p>
        ) : (
          <table className="w-full min-w-[550px]">
            <thead>
              <tr>
                <th className={TH_CLASS}>{t('admin.ads.colPartnerAd')}</th>
                <th className={TH_CLASS}>{t('admin.ads.colPlacement')}</th>
                <th className={TH_CLASS}>{t('admin.ads.colClicks')}</th>
                <th className={TH_CLASS}>{t('admin.colStatus')}</th>
                <th className={TH_CLASS}>{t('admin.colActions')}</th>
              </tr>
            </thead>
            <tbody>
              {ads.map((item) => (
                <tr key={item.id}>
                  <td className={TD_CLASS}>
                    <div className="font-semibold text-sm flex items-center gap-1.5">
                      {item.partner_name}
                      <a href={item.target_url} target="_blank" rel="noopener noreferrer" className="text-[var(--dz-muted)] hover:text-[var(--dz-primary)]">
                        <ExternalLink size={12} />
                      </a>
                    </div>
                    <div className="text-xs text-[var(--dz-muted)] max-w-[240px] truncate">{item.description}</div>
                  </td>
                  <td className={TD_CLASS}>
                    <span className="px-2 py-0.5 rounded bg-[var(--dz-canvas)] text-xs text-[var(--dz-primary)] border border-[var(--dz-border)] font-medium">
                      {placementLabel(item.placement)}
                    </span>
                  </td>
                  <td className={TD_CLASS + ' tnum font-bold text-[var(--dz-primary)]'}>{item.clicks || 0}</td>
                  <td className={TD_CLASS}>
                    <Button
                      variant="outline"
                      size="sm"
                      className={`h-7 px-3 text-xs ${item.active ? 'text-[var(--dz-buy)] border-[var(--dz-buy)]/30 bg-green-50/50' : 'text-[var(--dz-muted)]'}`}
                      onClick={() => handleToggleActive(item)}
                    >
                      {item.active ? t('admin.ads.statusActive') : t('admin.ads.statusInactive')}
                    </Button>
                  </td>
                  <td className={TD_CLASS}>
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(item.id)}>
                      <Trash2 size={15} className="text-[var(--dz-sell)]" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
