import React from 'react';
import { useTranslation } from 'react-i18next';
import { LegalPage } from './legal/LegalPage';
import { TERMS_CONTENT, LAST_UPDATED } from './legal/legalContent';

const TITLE = { pt: 'Termos de Uso', en: 'Terms of Service', es: 'Términos de Servicio', fr: 'Conditions d’utilisation' };
const UPDATED_LABEL = { pt: 'Última atualização', en: 'Last updated', es: 'Última actualización', fr: 'Dernière mise à jour' };

export default function TermsOfService() {
  const { i18n } = useTranslation();
  const locale = ['pt', 'en', 'es', 'fr'].includes(i18n.language?.slice(0, 2)) ? i18n.language.slice(0, 2) : 'en';

  return (
    <LegalPage
      testId="terms-of-service-page"
      title={TITLE[locale]}
      lastUpdated={`${UPDATED_LABEL[locale]}: ${LAST_UPDATED[locale]}`}
      sections={TERMS_CONTENT[locale]}
    />
  );
}
