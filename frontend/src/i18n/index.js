import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import en from '../locales/en.json';
import fr from '../locales/fr.json';
import pt from '../locales/pt.json';
import es from '../locales/es.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      fr: { translation: fr },
      pt: { translation: pt },
      es: { translation: es },
    },
    lng: undefined,
    fallbackLng: 'en',
    supportedLngs: ['en', 'fr', 'pt', 'es'],
    detection: {
      // English is the product default: only ever switch away from it when
      // the visitor has explicitly picked a language before (persisted to
      // dz_locale). Browser/navigator language is deliberately NOT used for
      // detection so a visitor's OS/browser locale never silently changes
      // the site's language on first visit.
      order: ['localStorage'],
      lookupLocalStorage: 'dz_locale',
      caches: ['localStorage'],
    },
    interpolation: { escapeValue: false },
  });

export default i18n;
