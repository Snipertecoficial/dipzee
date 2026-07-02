import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Megaphone, Trash2, Plus, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { TH_CLASS, TD_CLASS, fmtDate } from './AdminShared';
import api from '../../lib/api';
import { toast } from 'sonner';

export function AdminAnnouncementsTab() {
  const { t, i18n } = useTranslation();
  const locale = i18n.language?.slice(0, 2) || 'en';

  const [announcements, setAnnouncements] = useState([]);
  const [content, setContent] = useState('');
  const [type, setType] = useState('info');
  const [active, setActive] = useState(true);
  const [expiresAt, setExpiresAt] = useState('');
  const [busy, setBusy] = useState(false);

  const loadAnnouncements = async () => {
    try {
      const { data } = await api.get('/admin/announcements');
      setAnnouncements(data.announcements || []);
    } catch (e) {
      toast.error('Erro ao carregar comunicados');
    }
  };

  useEffect(() => {
    loadAnnouncements();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!content.trim()) return;
    setBusy(true);
    try {
      await api.post('/admin/announcements', {
        content: content.trim(),
        type,
        active,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      });
      toast.success('Comunicado criado com sucesso');
      setContent('');
      setExpiresAt('');
      loadAnnouncements();
    } catch (err) {
      toast.error('Erro ao criar comunicado');
    } finally {
      setBusy(false);
    }
  };

  const handleToggleActive = async (item) => {
    try {
      await api.put(`/admin/announcements/${item.id}`, {
        ...item,
        active: !item.active,
      });
      toast.success('Status atualizado');
      loadAnnouncements();
    } catch (err) {
      toast.error('Erro ao atualizar status');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Tem certeza que deseja excluir este comunicado?')) return;
    try {
      await api.delete(`/admin/announcements/${id}`);
      toast.success('Comunicado excluído');
      loadAnnouncements();
    } catch (err) {
      toast.error('Erro ao excluir comunicado');
    }
  };

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      {/* Create form */}
      <Card className="p-5 lg:col-span-1 h-fit">
        <div className="flex items-center gap-2 mb-4">
          <Megaphone size={18} className="text-[var(--dz-primary)]" />
          <h3 className="font-heading font-semibold text-lg">Novo Comunicado</h3>
        </div>
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-[var(--dz-muted)] block mb-1">Mensagem do Comunicado</label>
            <textarea
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Digite o aviso para todos os usuários..."
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--dz-muted)] block mb-1">Tipo de Alerta</label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="info">Info (Azul)</SelectItem>
                <SelectItem value="warning">Aviso (Laranja)</SelectItem>
                <SelectItem value="success">Sucesso (Verde)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--dz-muted)] block mb-1">Data de Expiração (Opcional)</label>
            <Input
              type="date"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="ann-active"
              checked={active}
              onChange={(e) => setActive(e.target.checked)}
              className="rounded border-[var(--dz-border)] text-[var(--dz-primary)] focus:ring-0"
            />
            <label htmlFor="ann-active" className="text-xs font-medium text-[var(--dz-muted)] cursor-pointer">Ativar imediatamente</label>
          </div>
          <Button type="submit" className="w-full mt-2" disabled={busy}>
            {busy ? <Loader2 size={16} className="animate-spin mr-1" /> : <Plus size={16} className="mr-1" />}
            Criar Comunicado
          </Button>
        </form>
      </Card>

      {/* Announcements list */}
      <Card className="p-5 lg:col-span-2 overflow-x-auto">
        <h3 className="font-heading font-semibold text-lg mb-4">Comunicados Ativos</h3>
        {announcements.length === 0 ? (
          <p className="text-sm text-[var(--dz-muted)] text-center py-8">Nenhum comunicado criado ainda.</p>
        ) : (
          <table className="w-full min-w-[500px]">
            <thead>
              <tr>
                <th className={TH_CLASS}>Mensagem</th>
                <th className={TH_CLASS}>Tipo</th>
                <th className={TH_CLASS}>Expira em</th>
                <th className={TH_CLASS}>Status</th>
                <th className={TH_CLASS}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {announcements.map((item) => (
                <tr key={item.id}>
                  <td className={TD_CLASS + ' max-w-[200px] truncate'}>{item.content}</td>
                  <td className={TD_CLASS}>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold uppercase ${
                      item.type === 'success' ? 'bg-green-100 text-green-800' :
                      item.type === 'warning' ? 'bg-amber-100 text-amber-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {item.type}
                    </span>
                  </td>
                  <td className={TD_CLASS}>{item.expires_at ? fmtDate(item.expires_at, locale) : 'Nunca'}</td>
                  <td className={TD_CLASS}>
                    <Button
                      variant="outline"
                      size="sm"
                      className={`h-7 px-3 text-xs ${item.active ? 'text-[var(--dz-buy)] border-[var(--dz-buy)]/30 bg-green-50/50' : 'text-[var(--dz-muted)]'}`}
                      onClick={() => handleToggleActive(item)}
                    >
                      {item.active ? 'Ativo' : 'Inativo'}
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
