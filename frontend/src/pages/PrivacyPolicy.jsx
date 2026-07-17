import React from 'react';
import { useTranslation } from 'react-i18next';
import { LegalPage } from './legal/LegalPage';
import { PRIVACY_CONTENT, LAST_UPDATED } from './legal/legalContent';

const TITLE = { pt: 'Política de Privacidade', en: 'Privacy Policy', es: 'Política de Privacidad', fr: 'Politique de confidentialité' };
const UPDATED_LABEL = { pt: 'Última atualização', en: 'Last updated', es: 'Última actualización', fr: 'Dernière mise à jour' };

export default function PrivacyPolicy() {
  const { i18n } = useTranslation();
  const locale = ['pt', 'en', 'es', 'fr'].includes(i18n.language?.slice(0, 2)) ? i18n.language.slice(0, 2) : 'en';

  return (
    <LegalPage
      testId="privacy-policy-page"
      title={TITLE[locale]}
      lastUpdated={`${UPDATED_LABEL[locale]}: ${LAST_UPDATED[locale]}`}
      sections={PRIVACY_CONTENT[locale]}
    />
  );
}
