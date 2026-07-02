// Localized testimonials for the landing page carousel.
// The list is selected by the active i18n language so PT users see Brazilian
// investors, EN users see US investors, etc. Falls back to English.

export const TESTIMONIALS = {
  pt: [
    { name: 'Ricardo Santos', role: 'Investidor de Varejo', content: 'A Dipzee me poupou horas de pesquisa. O Opportunity Score é surpreendentemente preciso e os alertas instantâneos me deixam tranquilo, sem medo de perder a oportunidade.' },
    { name: 'Juliana Mendes', role: 'Day Trader', content: 'Opero no mercado americano todos os dias. Ter preços e dividendos convertidos para BRL e a agilidade do Screener foi a melhor descoberta do meu ano.' },
    { name: 'Marcio Alves', role: 'Engenheiro de Software', content: 'A arquitetura e a velocidade da plataforma impressionam. Integrei os Webhooks na minha rotina e automatizei minhas decisões de Hold. Nota 10.' },
    { name: 'Camila Farias', role: 'Gestora de Portfólio', content: 'Usamos as análises fundamentalistas e o veredito dos analistas para montar carteiras. Os alvos de 52 semanas são cirúrgicos. Vale cada centavo do plano Investor.' },
    { name: 'Bruno Carvalho', role: 'Investidor de Dividendos', content: 'Acompanho o yield e o histórico de proventos direto no painel. O backtest me ajudou a validar minha estratégia de comprar nas quedas antes de arriscar de verdade.' },
  ],
  en: [
    { name: 'John Mitchell', role: 'Retail Investor', content: "I've been looking for a tool that pairs deep fundamentals with a beautiful UI. Dipzee's Opportunity Score is the best feature — an absolute game-changer." },
    { name: 'Sarah Thompson', role: 'Day Trader', content: 'The real-time alerts are instant and reliable. I finally stopped staring at charts all day and let Dipzee flag the setups that actually matter.' },
    { name: 'David Chen', role: 'Software Engineer', content: 'The architecture and speed are seriously impressive. I wired the Webhooks into my own automations and now my hold decisions run themselves. 10/10.' },
    { name: 'Emily Rodriguez', role: 'Portfolio Manager', content: 'We rely on the fundamentals and analyst verdicts to build our books. The 52-week targets are surgical — worth every penny of the Investor plan.' },
    { name: 'Michael Brooks', role: 'Dividend Investor', content: 'Tracking yield and payout history in one dashboard is a dream. The backtest let me validate my buy-the-dip approach before committing real capital.' },
  ],
  es: [
    { name: 'Carlos Herrera', role: 'Inversor Minorista', content: 'Buscaba una herramienta que combinara fundamentales profundos con una interfaz cuidada. El Opportunity Score de Dipzee lo cambió todo para mí.' },
    { name: 'Lucía Fernández', role: 'Day Trader', content: 'Opero en el mercado estadounidense a diario. Las alertas en tiempo real son instantáneas y el Screener me ahorra muchísimo tiempo cada mañana.' },
    { name: 'Diego Morales', role: 'Ingeniero de Software', content: 'La arquitectura y la velocidad de la plataforma impresionan. Integré los Webhooks en mis automatizaciones y mis decisiones de Hold se ejecutan solas. 10/10.' },
    { name: 'Sofía Ramírez', role: 'Gestora de Cartera', content: 'Usamos los fundamentales y el veredicto de los analistas para armar carteras. Los objetivos de 52 semanas son quirúrgicos. Vale cada céntimo del plan Investor.' },
    { name: 'Andrés Vargas', role: 'Inversor de Dividendos', content: 'Seguir el yield y el histórico de dividendos en un solo panel es genial. El backtest me permitió validar mi estrategia antes de arriesgar capital real.' },
  ],
  fr: [
    { name: 'Julien Moreau', role: 'Investisseur particulier', content: "Je cherchais un outil qui associe des fondamentaux poussés à une interface soignée. L'Opportunity Score de Dipzee a tout changé pour moi." },
    { name: 'Camille Dubois', role: 'Day Trader', content: 'Je trade le marché américain tous les jours. Les alertes en temps réel sont instantanées et le Screener me fait gagner un temps précieux chaque matin.' },
    { name: 'Thomas Lefebvre', role: 'Ingénieur logiciel', content: "L'architecture et la vitesse de la plateforme sont bluffantes. J'ai branché les Webhooks sur mes automatisations et mes décisions de Hold tournent seules. 10/10." },
    { name: 'Amélie Laurent', role: 'Gestionnaire de portefeuille', content: 'Nous utilisons les fondamentaux et le verdict des analystes pour composer nos portefeuilles. Les objectifs à 52 semaines sont chirurgicaux. Le plan Investor vaut chaque centime.' },
    { name: 'Nicolas Girard', role: 'Investisseur en dividendes', content: 'Suivre le rendement et l’historique des dividendes au même endroit est un vrai plaisir. Le backtest m’a permis de valider ma stratégie avant d’engager du capital réel.' },
  ],
};

export function getTestimonials(locale) {
  const code = (locale || 'en').slice(0, 2).toLowerCase();
  return TESTIMONIALS[code] || TESTIMONIALS.en;
}
