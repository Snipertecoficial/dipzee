// Privacy Policy + Terms of Service content, per locale.
//
// Kept as structured data (not i18n JSON) on purpose: these are dated, legal
// documents that must read as one coherent voice per language, not a bag of
// independently-interpolated UI strings. `LAST_UPDATED` and `TERMS_VERSION`
// must be bumped together, and must match `TERMS_VERSION` in
// backend/routes_auth.py so the stored per-user consent timestamp lines up
// with the text that was actually in force when someone registered.
//
// NOTE: Dipzee is currently operated by its founders; formal incorporation
// in Canada is in progress. Update the "who we are" section with the legal
// entity name/registration number/address once that's complete.

export const LAST_UPDATED = {
  pt: '17 de julho de 2026',
  en: 'July 17, 2026',
  es: '17 de julio de 2026',
  fr: '17 juillet 2026',
};

export const PRIVACY_CONTENT = {
  pt: [
    {
      heading: '1. Quem somos',
      paragraphs: [
        'O Dipzee ("nós", "nosso") é uma plataforma de análise e monitoramento de ações (screener, lista de observação, alertas, acompanhamento de portfólio e análises educacionais gerdas por IA). O Dipzee não é uma corretora, não custodia ativos e não executa ordens de compra ou venda.',
        'O Dipzee é atualmente operado por seus fundadores, com a formalização de uma pessoa jurídica no Canadá em andamento. Assim que a constituição for concluída, esta política será atualizada com a razão social, número de registro e endereço da empresa.',
        'Para questões de privacidade, escreva para privacidade@dipzee.com. Para suporte geral, use suporte@dipzee.com.',
      ],
    },
    {
      heading: '2. Quais dados coletamos',
      list: [
        'Dados de conta: e-mail e senha (armazenada com hash, nunca em texto puro), idioma e moeda preferidos.',
        'Dados de perfil opcionais: nome de exibição, biografia, telefone, país e foto de perfil.',
        'Dados de uso que você mesmo cadastra: ativos na lista de observação, alertas configurados e posições de portfólio (quantidade e preço médio informados por você — não nos conectamos a nenhuma corretora real).',
        'Dados de pagamento: processados diretamente pelo Stripe; nunca armazenamos o número do cartão. Guardamos apenas identificadores de cliente/assinatura e o histórico de transações (valor, plano, datas).',
        'Dados técnicos: endereço IP e registros de acesso, usados temporariamente para segurança (prevenção de fraude e força bruta).',
        'Canais de notificação opcionais: ID de chat do Telegram e URL de webhook, somente se você optar por configurá-los.',
      ],
    },
    {
      heading: '3. Cookies e armazenamento local',
      paragraphs: [
        'Não usamos cookies de rastreamento de terceiros nem publicidade comportamental. A sua sessão de login é mantida por armazenamento local do navegador (localStorage), não por cookies — isso é estritamente necessário para o funcionamento do serviço.',
      ],
    },
    {
      heading: '4. Para que usamos seus dados',
      list: [
        'Criar e manter sua conta e autenticar seu login.',
        'Fornecer as funcionalidades da plataforma (screener, alertas, portfólio, análises).',
        'Processar pagamentos e gerenciar sua assinatura.',
        'Enviar e-mails operacionais (boas-vindas, redefinição de senha, alertas que você mesmo configurou).',
        'Prevenir fraude e abuso (limite de tentativas de login, limite de requisições).',
        'Cumprir obrigações legais e fiscais.',
      ],
    },
    {
      heading: '5. Base legal do tratamento',
      list: [
        'Execução de contrato: para fornecer o serviço que você contratou.',
        'Consentimento: para comunicações e canais de notificação opcionais que você ativa.',
        'Legítimo interesse: para segurança, prevenção de fraude e melhoria do serviço.',
        'Obrigação legal: para retenção de registros financeiros e fiscais.',
      ],
    },
    {
      heading: '6. Com quem compartilhamos dados',
      list: [
        'Stripe (processamento de pagamentos) — recebe e-mail e dados de cobrança.',
        'Resend (envio de e-mails transacionais) — recebe seu e-mail e o conteúdo da mensagem.',
        'Provedor de hospedagem da infraestrutura — armazena o banco de dados da aplicação.',
        'Telegram (opcional, somente se você ativar alertas por Telegram) — recebe o texto do alerta.',
        'Provedores de dados de mercado (ex. FMP, Finnhub, Polygon, Alpha Vantage, Twelve Data, Marketstack, Yahoo Finance) e provedores de IA (OpenAI, Anthropic, Google) — recebem apenas o ticker e dados do ativo consultado, nunca seus dados pessoais.',
      ],
      paragraphs: ['Não vendemos seus dados pessoais a terceiros.'],
    },
    {
      heading: '7. Retenção e exclusão',
      paragraphs: [
        'Mantemos seus dados enquanto sua conta estiver ativa. Você pode excluir sua conta a qualquer momento em Configurações → Meus Dados; isso remove permanentemente seu perfil, lista de observação, alertas e posições de portfólio.',
        'Registros de pagamento e faturamento são mantidos mesmo após a exclusão da conta, pelo prazo exigido pela legislação fiscal/contábil aplicável — nesse caso, apenas a assinatura ativa é cancelada, sem novas cobranças.',
      ],
    },
    {
      heading: '8. Segurança',
      list: [
        'Senhas armazenadas com hash (bcrypt), nunca em texto puro.',
        'Conexão criptografada (HTTPS/TLS) em produção.',
        'Limite de tentativas de login e bloqueio temporário após tentativas malsucedidas.',
        'Segredos e chaves de API mantidos fora do código-fonte.',
      ],
    },
    {
      heading: '9. Seus direitos, por jurisdição',
      list: [
        'Brasil (LGPD): confirmação da existência de tratamento, acesso, correção, anonimização ou eliminação, portabilidade, informação sobre compartilhamento e revogação do consentimento.',
        'União Europeia / França (GDPR): acesso, retificação, apagamento, limitação do tratamento, portabilidade, oposição, e o direito de reclamar junto à autoridade de proteção de dados local (a CNIL, na França).',
        'Canadá (PIPEDA / Lei 25 do Quebec): acesso às suas informações pessoais, correção, e o direito de apresentar reclamação ao Escritório do Comissário de Privacidade do Canadá.',
        'Estados Unidos, especialmente Califórnia (CCPA/CPRA): direito de saber quais dados coletamos, direito de exclusão e direito de não sofrer discriminação por exercer esses direitos. Não vendemos nem compartilhamos dados pessoais para publicidade direcionada.',
        'Outros países da América Latina com lei própria de proteção de dados (ex. LFPDPPP no México, Lei 1581 de 2012 na Colômbia, Lei 25.326 na Argentina, Lei 19.628/21.719 no Chile): direitos equivalentes de acesso, retificação, cancelamento e oposição (direitos ARCO).',
      ],
      paragraphs: [
        'Para exercer qualquer um desses direitos, use as ferramentas de autoatendimento em Configurações → Meus Dados (baixar meus dados / excluir minha conta) ou escreva para privacidade@dipzee.com. Respondemos em até 15 dias corridos.',
      ],
    },
    {
      heading: '10. Transferência internacional de dados',
      paragraphs: [
        'Seus dados podem ser processados em servidores fora do seu país — por exemplo, a infraestrutura de hospedagem e provedores como Stripe e Resend operam globalmente. Adotamos medidas contratuais e técnicas razoáveis para proteger seus dados nessas transferências.',
      ],
    },
    {
      heading: '11. Menores de idade',
      paragraphs: ['O Dipzee não é direcionado a menores de 18 anos e não coletamos intencionalmente dados de menores.'],
    },
    {
      heading: '12. Alterações nesta política',
      paragraphs: ['Podemos atualizar esta política periodicamente. Mudanças relevantes serão comunicadas por e-mail ou aviso no aplicativo. A data da última atualização está no topo desta página.'],
    },
    {
      heading: '13. Contato',
      paragraphs: ['privacidade@dipzee.com (privacidade e dados pessoais) · suporte@dipzee.com (suporte geral)'],
    },
  ],

  en: [
    {
      heading: '1. Who we are',
      paragraphs: [
        'Dipzee ("we", "our") is a stock analysis and monitoring platform (screener, watchlist, alerts, self-tracked portfolio, and AI-generated educational analysis). Dipzee is not a broker-dealer, does not custody assets, and does not execute buy or sell orders.',
        'Dipzee is currently operated by its founders, with formal incorporation in Canada in progress. Once that is complete, this policy will be updated with the legal entity name, registration number, and address.',
        'For privacy questions, write to privacidade@dipzee.com. For general support, use suporte@dipzee.com.',
      ],
    },
    {
      heading: '2. What data we collect',
      list: [
        'Account data: email and password (stored hashed, never in plain text), preferred language and currency.',
        'Optional profile data: display name, bio, phone, country, and profile photo.',
        'Usage data you enter yourself: watchlist assets, alerts you configure, and portfolio positions (quantity and average cost you report — we never connect to a real brokerage account).',
        'Payment data: processed directly by Stripe; we never store your card number. We keep only customer/subscription identifiers and a transaction history (amount, plan, dates).',
        'Technical data: IP address and access logs, kept temporarily for security (fraud and brute-force prevention).',
        'Optional notification channels: Telegram chat ID and webhook URL, only if you choose to configure them.',
      ],
    },
    {
      heading: '3. Cookies and local storage',
      paragraphs: [
        'We do not use third-party tracking cookies or behavioral advertising. Your login session is kept via the browser’s local storage (localStorage), not cookies — this is strictly necessary for the service to work.',
      ],
    },
    {
      heading: '4. How we use your data',
      list: [
        'To create and maintain your account and authenticate your login.',
        'To provide the platform’s features (screener, alerts, portfolio, analysis).',
        'To process payments and manage your subscription.',
        'To send operational emails (welcome, password reset, alerts you configured yourself).',
        'To prevent fraud and abuse (login attempt limits, rate limiting).',
        'To comply with legal and tax obligations.',
      ],
    },
    {
      heading: '5. Legal basis for processing',
      list: [
        'Performance of a contract: to provide the service you signed up for.',
        'Consent: for optional communications and notification channels you turn on.',
        'Legitimate interest: for security, fraud prevention, and service improvement.',
        'Legal obligation: for retaining financial and tax records.',
      ],
    },
    {
      heading: '6. Who we share data with',
      list: [
        'Stripe (payment processing) — receives your email and billing details.',
        'Resend (transactional email delivery) — receives your email address and message content.',
        'Our infrastructure hosting provider — stores the application database.',
        'Telegram (optional, only if you turn on Telegram alerts) — receives the alert text.',
        'Market data providers (e.g. FMP, Finnhub, Polygon, Alpha Vantage, Twelve Data, Marketstack, Yahoo Finance) and AI providers (OpenAI, Anthropic, Google) — receive only the ticker/asset data being queried, never your personal data.',
      ],
      paragraphs: ['We do not sell your personal data to third parties.'],
    },
    {
      heading: '7. Retention and deletion',
      paragraphs: [
        'We keep your data while your account is active. You can delete your account at any time from Settings → My Data; this permanently removes your profile, watchlist, alerts, and portfolio positions.',
        'Payment and billing records are kept even after account deletion, for as long as applicable tax/accounting law requires — in that case, only the active subscription is canceled, so you are never billed again.',
      ],
    },
    {
      heading: '8. Security',
      list: [
        'Passwords are stored hashed (bcrypt), never in plain text.',
        'Encrypted connection (HTTPS/TLS) in production.',
        'Login attempt limiting and temporary lockout after failed attempts.',
        'Secrets and API keys kept out of source code.',
      ],
    },
    {
      heading: '9. Your rights, by jurisdiction',
      list: [
        'Brazil (LGPD): confirmation that processing exists, access, correction, anonymization or deletion, portability, information about data sharing, and the right to withdraw consent.',
        'European Union / France (GDPR): access, rectification, erasure, restriction of processing, portability, objection, and the right to lodge a complaint with your local data protection authority (the CNIL, in France).',
        'Canada (PIPEDA / Quebec’s Law 25): access to your personal information, correction, and the right to file a complaint with the Office of the Privacy Commissioner of Canada.',
        'United States, especially California (CCPA/CPRA): the right to know what data we collect, the right to delete it, and the right not to be discriminated against for exercising these rights. We do not sell or share personal data for targeted advertising.',
        'Other Latin American countries with their own data protection law (e.g. Mexico’s LFPDPPP, Colombia’s Law 1581 of 2012, Argentina’s Law 25,326, Chile’s Law 19,628/21,719): equivalent access, rectification, cancellation, and objection rights (ARCO rights).',
      ],
      paragraphs: [
        'To exercise any of these rights, use the self-service tools in Settings → My Data (download my data / delete my account) or write to privacidade@dipzee.com. We respond within 15 calendar days.',
      ],
    },
    {
      heading: '10. International data transfers',
      paragraphs: [
        'Your data may be processed on servers outside your country — for example, our hosting infrastructure and providers like Stripe and Resend operate globally. We use reasonable contractual and technical safeguards to protect your data in these transfers.',
      ],
    },
    {
      heading: '11. Children’s privacy',
      paragraphs: ['Dipzee is not directed at anyone under 18, and we do not knowingly collect data from minors.'],
    },
    {
      heading: '12. Changes to this policy',
      paragraphs: ['We may update this policy from time to time. Material changes will be communicated by email or an in-app notice. The last-updated date is shown at the top of this page.'],
    },
    {
      heading: '13. Contact',
      paragraphs: ['privacidade@dipzee.com (privacy and personal data) · suporte@dipzee.com (general support)'],
    },
  ],

  es: [
    {
      heading: '1. Quiénes somos',
      paragraphs: [
        'Dipzee ("nosotros") es una plataforma de análisis y monitoreo de acciones (screener, lista de seguimiento, alertas, seguimiento de portafolio y análisis educativos generados por IA). Dipzee no es una correduría, no custodia activos y no ejecuta órdenes de compra o venta.',
        'Dipzee es operado actualmente por sus fundadores, con la constitución formal de una persona jurídica en Canadá en curso. Una vez completada, esta política se actualizará con la razón social, el número de registro y la dirección de la empresa.',
        'Para consultas de privacidad, escribe a privacidade@dipzee.com. Para soporte general, usa suporte@dipzee.com.',
      ],
    },
    {
      heading: '2. Qué datos recopilamos',
      list: [
        'Datos de cuenta: correo electrónico y contraseña (almacenada con hash, nunca en texto plano), idioma y moneda preferidos.',
        'Datos de perfil opcionales: nombre a mostrar, biografía, teléfono, país y foto de perfil.',
        'Datos de uso que tú mismo registras: activos en tu lista de seguimiento, alertas configuradas y posiciones de portafolio (cantidad y costo promedio que tú informas — nunca nos conectamos a una cuenta de corretaje real).',
        'Datos de pago: procesados directamente por Stripe; nunca almacenamos el número de tarjeta. Solo guardamos identificadores de cliente/suscripción y el historial de transacciones (monto, plan, fechas).',
        'Datos técnicos: dirección IP y registros de acceso, usados temporalmente por seguridad (prevención de fraude y fuerza bruta).',
        'Canales de notificación opcionales: ID de chat de Telegram y URL de webhook, solo si decides configurarlos.',
      ],
    },
    {
      heading: '3. Cookies y almacenamiento local',
      paragraphs: [
        'No usamos cookies de rastreo de terceros ni publicidad conductual. Tu sesión de acceso se mantiene mediante almacenamiento local del navegador (localStorage), no mediante cookies — esto es estrictamente necesario para el funcionamiento del servicio.',
      ],
    },
    {
      heading: '4. Para qué usamos tus datos',
      list: [
        'Crear y mantener tu cuenta y autenticar tu acceso.',
        'Proveer las funciones de la plataforma (screener, alertas, portafolio, análisis).',
        'Procesar pagos y gestionar tu suscripción.',
        'Enviar correos operativos (bienvenida, restablecimiento de contraseña, alertas que tú configuraste).',
        'Prevenir fraude y abuso (límite de intentos de acceso, límite de solicitudes).',
        'Cumplir obligaciones legales y fiscales.',
      ],
    },
    {
      heading: '5. Base legal del tratamiento',
      list: [
        'Ejecución de contrato: para proveer el servicio que contrataste.',
        'Consentimiento: para comunicaciones y canales de notificación opcionales que actives.',
        'Interés legítimo: para seguridad, prevención de fraude y mejora del servicio.',
        'Obligación legal: para la retención de registros financieros y fiscales.',
      ],
    },
    {
      heading: '6. Con quién compartimos datos',
      list: [
        'Stripe (procesamiento de pagos) — recibe tu correo y datos de facturación.',
        'Resend (envío de correos transaccionales) — recibe tu correo y el contenido del mensaje.',
        'Nuestro proveedor de hosting de infraestructura — almacena la base de datos de la aplicación.',
        'Telegram (opcional, solo si activas alertas por Telegram) — recibe el texto de la alerta.',
        'Proveedores de datos de mercado (p. ej. FMP, Finnhub, Polygon, Alpha Vantage, Twelve Data, Marketstack, Yahoo Finance) y proveedores de IA (OpenAI, Anthropic, Google) — reciben solo el ticker/datos del activo consultado, nunca tus datos personales.',
      ],
      paragraphs: ['No vendemos tus datos personales a terceros.'],
    },
    {
      heading: '7. Retención y eliminación',
      paragraphs: [
        'Conservamos tus datos mientras tu cuenta esté activa. Puedes eliminar tu cuenta en cualquier momento desde Configuración → Mis Datos; esto elimina permanentemente tu perfil, lista de seguimiento, alertas y posiciones de portafolio.',
        'Los registros de pago y facturación se conservan incluso después de eliminar la cuenta, durante el plazo que exija la legislación fiscal/contable aplicable — en ese caso, solo se cancela la suscripción activa, sin nuevos cobros.',
      ],
    },
    {
      heading: '8. Seguridad',
      list: [
        'Contraseñas almacenadas con hash (bcrypt), nunca en texto plano.',
        'Conexión cifrada (HTTPS/TLS) en producción.',
        'Límite de intentos de acceso y bloqueo temporal tras intentos fallidos.',
        'Secretos y claves de API mantenidos fuera del código fuente.',
      ],
    },
    {
      heading: '9. Tus derechos, por jurisdicción',
      list: [
        'Brasil (LGPD): confirmación de la existencia de tratamiento, acceso, corrección, anonimización o eliminación, portabilidad, información sobre el uso compartido y revocación del consentimiento.',
        'Unión Europea / Francia (RGPD): acceso, rectificación, supresión, limitación del tratamiento, portabilidad, oposición, y el derecho a presentar una reclamación ante tu autoridad local de protección de datos (la CNIL, en Francia).',
        'Canadá (PIPEDA / Ley 25 de Quebec): acceso a tu información personal, corrección, y el derecho a presentar una queja ante la Oficina del Comisionado de Privacidad de Canadá.',
        'Estados Unidos, especialmente California (CCPA/CPRA): derecho a saber qué datos recopilamos, derecho a eliminarlos y derecho a no sufrir discriminación por ejercer estos derechos. No vendemos ni compartimos datos personales para publicidad dirigida.',
        'Otros países de América Latina con ley propia de protección de datos (p. ej. LFPDPPP en México, Ley 1581 de 2012 en Colombia, Ley 25.326 en Argentina, Ley 19.628/21.719 en Chile): derechos equivalentes de acceso, rectificación, cancelación y oposición (derechos ARCO).',
      ],
      paragraphs: [
        'Para ejercer cualquiera de estos derechos, usa las herramientas de autoservicio en Configuración → Mis Datos (descargar mis datos / eliminar mi cuenta) o escribe a privacidade@dipzee.com. Respondemos dentro de 15 días corridos.',
      ],
    },
    {
      heading: '10. Transferencia internacional de datos',
      paragraphs: [
        'Tus datos pueden procesarse en servidores fuera de tu país — por ejemplo, nuestra infraestructura de hosting y proveedores como Stripe y Resend operan globalmente. Adoptamos medidas contractuales y técnicas razonables para proteger tus datos en estas transferencias.',
      ],
    },
    {
      heading: '11. Privacidad de menores',
      paragraphs: ['Dipzee no está dirigido a menores de 18 años y no recopilamos intencionalmente datos de menores.'],
    },
    {
      heading: '12. Cambios a esta política',
      paragraphs: ['Podemos actualizar esta política periódicamente. Los cambios importantes se comunicarán por correo o aviso dentro de la aplicación. La fecha de la última actualización aparece en la parte superior de esta página.'],
    },
    {
      heading: '13. Contacto',
      paragraphs: ['privacidade@dipzee.com (privacidad y datos personales) · suporte@dipzee.com (soporte general)'],
    },
  ],

  fr: [
    {
      heading: '1. Qui sommes-nous',
      paragraphs: [
        'Dipzee (« nous ») est une plateforme d’analyse et de suivi d’actions (screener, liste de suivi, alertes, suivi de portefeuille et analyses éducatives générées par IA). Dipzee n’est pas un courtier, ne conserve pas d’actifs et n’exécute aucun ordre d’achat ou de vente.',
        'Dipzee est actuellement exploité par ses fondateurs, la constitution formelle d’une personne morale au Canada étant en cours. Une fois celle-ci finalisée, cette politique sera mise à jour avec la raison sociale, le numéro d’immatriculation et l’adresse de l’entreprise.',
        'Pour toute question relative à la vie privée, écrivez à privacidade@dipzee.com. Pour le support général, utilisez suporte@dipzee.com.',
      ],
    },
    {
      heading: '2. Quelles données nous collectons',
      list: [
        'Données de compte : e-mail et mot de passe (stocké haché, jamais en clair), langue et devise préférées.',
        'Données de profil facultatives : nom affiché, biographie, téléphone, pays et photo de profil.',
        'Données d’usage que vous saisissez vous-même : actifs suivis, alertes configurées et positions de portefeuille (quantité et coût moyen que vous déclarez — nous ne nous connectons jamais à un compte de courtage réel).',
        'Données de paiement : traitées directement par Stripe ; nous ne stockons jamais le numéro de carte. Nous conservons uniquement les identifiants client/abonnement et l’historique des transactions (montant, forfait, dates).',
        'Données techniques : adresse IP et journaux d’accès, conservés temporairement à des fins de sécurité (prévention de la fraude et des attaques par force brute).',
        'Canaux de notification facultatifs : identifiant de chat Telegram et URL de webhook, uniquement si vous choisissez de les configurer.',
      ],
    },
    {
      heading: '3. Cookies et stockage local',
      paragraphs: [
        'Nous n’utilisons pas de cookies de suivi tiers ni de publicité comportementale. Votre session de connexion est maintenue via le stockage local du navigateur (localStorage), et non par des cookies — ceci est strictement nécessaire au fonctionnement du service.',
      ],
    },
    {
      heading: '4. Comment nous utilisons vos données',
      list: [
        'Créer et maintenir votre compte et authentifier votre connexion.',
        'Fournir les fonctionnalités de la plateforme (screener, alertes, portefeuille, analyses).',
        'Traiter les paiements et gérer votre abonnement.',
        'Envoyer des e-mails opérationnels (bienvenue, réinitialisation de mot de passe, alertes que vous avez configurées).',
        'Prévenir la fraude et les abus (limite de tentatives de connexion, limitation du nombre de requêtes).',
        'Respecter nos obligations légales et fiscales.',
      ],
    },
    {
      heading: '5. Base légale du traitement',
      list: [
        'Exécution d’un contrat : pour fournir le service auquel vous avez souscrit.',
        'Consentement : pour les communications et canaux de notification facultatifs que vous activez.',
        'Intérêt légitime : pour la sécurité, la prévention de la fraude et l’amélioration du service.',
        'Obligation légale : pour la conservation des registres financiers et fiscaux.',
      ],
    },
    {
      heading: '6. Avec qui nous partageons des données',
      list: [
        'Stripe (traitement des paiements) — reçoit votre e-mail et vos données de facturation.',
        'Resend (envoi d’e-mails transactionnels) — reçoit votre adresse e-mail et le contenu du message.',
        'Notre hébergeur d’infrastructure — stocke la base de données de l’application.',
        'Telegram (facultatif, uniquement si vous activez les alertes Telegram) — reçoit le texte de l’alerte.',
        'Fournisseurs de données de marché (ex. FMP, Finnhub, Polygon, Alpha Vantage, Twelve Data, Marketstack, Yahoo Finance) et fournisseurs d’IA (OpenAI, Anthropic, Google) — reçoivent uniquement le symbole boursier/les données de l’actif consulté, jamais vos données personnelles.',
      ],
      paragraphs: ['Nous ne vendons pas vos données personnelles à des tiers.'],
    },
    {
      heading: '7. Conservation et suppression',
      paragraphs: [
        'Nous conservons vos données tant que votre compte est actif. Vous pouvez supprimer votre compte à tout moment depuis Paramètres → Mes données ; cela supprime définitivement votre profil, votre liste de suivi, vos alertes et vos positions de portefeuille.',
        'Les registres de paiement et de facturation sont conservés même après la suppression du compte, pendant la durée requise par la législation fiscale/comptable applicable — dans ce cas, seul l’abonnement actif est annulé, sans nouveau prélèvement.',
      ],
    },
    {
      heading: '8. Sécurité',
      list: [
        'Mots de passe stockés hachés (bcrypt), jamais en clair.',
        'Connexion chiffrée (HTTPS/TLS) en production.',
        'Limitation des tentatives de connexion et blocage temporaire après des tentatives infructueuses.',
        'Secrets et clés d’API conservés en dehors du code source.',
      ],
    },
    {
      heading: '9. Vos droits, selon votre juridiction',
      list: [
        'Brésil (LGPD) : confirmation de l’existence d’un traitement, accès, correction, anonymisation ou suppression, portabilité, information sur le partage des données et retrait du consentement.',
        'Union européenne / France (RGPD) : accès, rectification, effacement, limitation du traitement, portabilité, opposition, et le droit d’introduire une réclamation auprès de votre autorité de protection des données (la CNIL, en France).',
        'Canada (LPRPDE / Loi 25 du Québec) : accès à vos renseignements personnels, correction, et le droit de déposer une plainte auprès du Commissariat à la protection de la vie privée du Canada.',
        'États-Unis, en particulier la Californie (CCPA/CPRA) : droit de savoir quelles données nous collectons, droit de suppression, et droit de ne pas subir de discrimination pour l’exercice de ces droits. Nous ne vendons ni ne partageons de données personnelles à des fins de publicité ciblée.',
        'Autres pays d’Amérique latine dotés de leur propre loi sur la protection des données (ex. LFPDPPP au Mexique, Loi 1581 de 2012 en Colombie, Loi 25.326 en Argentine, Loi 19.628/21.719 au Chili) : droits équivalents d’accès, de rectification, d’annulation et d’opposition (droits ARCO).',
      ],
      paragraphs: [
        'Pour exercer l’un de ces droits, utilisez les outils en libre-service dans Paramètres → Mes données (télécharger mes données / supprimer mon compte) ou écrivez à privacidade@dipzee.com. Nous répondons sous 15 jours calendaires.',
      ],
    },
    {
      heading: '10. Transferts internationaux de données',
      paragraphs: [
        'Vos données peuvent être traitées sur des serveurs situés hors de votre pays — par exemple, notre infrastructure d’hébergement et des fournisseurs comme Stripe et Resend opèrent à l’échelle mondiale. Nous mettons en œuvre des garanties contractuelles et techniques raisonnables pour protéger vos données lors de ces transferts.',
      ],
    },
    {
      heading: '11. Protection des mineurs',
      paragraphs: ['Dipzee ne s’adresse pas aux personnes de moins de 18 ans et nous ne collectons pas sciemment de données concernant des mineurs.'],
    },
    {
      heading: '12. Modifications de cette politique',
      paragraphs: ['Nous pouvons mettre à jour cette politique de temps à autre. Les changements importants seront communiqués par e-mail ou par une notification dans l’application. La date de dernière mise à jour figure en haut de cette page.'],
    },
    {
      heading: '13. Contact',
      paragraphs: ['privacidade@dipzee.com (vie privée et données personnelles) · suporte@dipzee.com (support général)'],
    },
  ],
};

export const TERMS_CONTENT = {
  pt: [
    {
      heading: '1. Aceitação dos termos',
      paragraphs: ['Ao criar uma conta ou usar o Dipzee, você concorda com estes Termos de Uso e com nossa Política de Privacidade. Se não concordar, não utilize a plataforma.'],
    },
    {
      heading: '2. O que é o Dipzee',
      paragraphs: [
        'O Dipzee é uma ferramenta de informação e análise de mercado: screener de ações, listas de observação, alertas de preço, acompanhamento de portfólio auto-declarado e análises geradas por IA.',
        'O Dipzee NÃO é uma corretora de valores, não custodia ativos, não executa ordens de compra ou venda e não é registrado como consultor de investimentos em nenhuma jurisdição.',
        'Todo o conteúdo, incluindo o "Opportunity Score" e as análises geradas por IA, tem finalidade exclusivamente educacional e informativa, e NÃO constitui recomendação ou aconselhamento financeiro. Decisões de investimento são de sua exclusiva responsabilidade.',
        'Os dados de mercado exibidos são obtidos de provedores terceiros (bolsas, APIs de dados financeiros, fontes públicas) e podem conter atrasos, imprecisões ou indisponibilidade temporária. Não garantimos exatidão, completude ou atualidade desses dados.',
      ],
    },
    {
      heading: '3. Elegibilidade e conta',
      list: [
        'Você precisa ter 18 anos ou mais para usar o Dipzee.',
        'Você é responsável por manter a confidencialidade de sua senha e por todas as atividades realizadas em sua conta.',
        'Uma conta é pessoal e intransferível.',
      ],
    },
    {
      heading: '4. Assinaturas e cobrança',
      list: [
        'Os planos pagos (Starter, Pro, Investidor) são cobrados de forma recorrente (mensal ou anual) via Stripe, com um período de teste gratuito de 7 dias mediante cartão de crédito válido.',
        'Ao final do período de teste, a cobrança do plano escolhido é feita automaticamente, salvo cancelamento antes do fim do teste.',
        'Você pode mudar de plano (upgrade ou downgrade) a qualquer momento em Configurações → Assinatura; a mudança é aplicada imediatamente e eventuais diferenças de valor são ajustadas proporcionalmente na fatura seguinte.',
        'Você pode cancelar sua assinatura a qualquer momento pelo mesmo menu. O cancelamento encerra a renovação automática — você mantém acesso ao plano pago até o fim do período já pago, sem cobranças futuras.',
        'Não realizamos reembolso proporcional de períodos já pagos, exceto quando exigido por lei aplicável.',
      ],
    },
    {
      heading: '5. Uso aceitável',
      paragraphs: ['Você concorda em não:'],
      list: [
        'Tentar acessar áreas restritas do sistema sem autorização.',
        'Fazer engenharia reversa ou raspagem (scraping) automatizada da plataforma.',
        'Revender ou redistribuir os dados/análises do Dipzee sem autorização.',
        'Usar a plataforma para fins ilegais.',
      ],
    },
    {
      heading: '6. Propriedade intelectual',
      paragraphs: ['A marca, o logotipo, o design e o código do Dipzee pertencem a seus operadores. Dados de mercado de terceiros pertencem aos respectivos provedores e são usados sob suas condições de licenciamento.'],
    },
    {
      heading: '7. Isenção de responsabilidade',
      paragraphs: [
        'O serviço é fornecido "como está" e "conforme disponível". Não garantimos que a plataforma estará livre de erros ou interrupções.',
        'Não somos responsáveis por perdas financeiras decorrentes de decisões de investimento tomadas com base em informações, scores ou análises da plataforma.',
      ],
    },
    {
      heading: '8. Limitação de responsabilidade',
      paragraphs: ['Na máxima extensão permitida por lei, nossa responsabilidade total por qualquer reclamação relacionada ao serviço está limitada ao valor pago por você nos 12 meses anteriores ao evento que originou a reclamação.'],
    },
    {
      heading: '9. Rescisão',
      paragraphs: ['Podemos suspender ou encerrar contas que violem estes termos. Você pode encerrar sua própria conta a qualquer momento pelas ferramentas de autoatendimento em Configurações → Meus Dados.'],
    },
    {
      heading: '10. Lei aplicável',
      paragraphs: ['Estes termos são regidos pelas leis do Canadá, jurisdição de constituição da empresa operadora do Dipzee (formalização em andamento), sem prejuízo dos direitos obrigatórios que a legislação do seu país de residência (por exemplo, Brasil/LGPD ou União Europeia/GDPR) lhe garanta como consumidor.'],
    },
    {
      heading: '11. Alterações nestes termos',
      paragraphs: ['Podemos atualizar estes termos periodicamente. Mudanças relevantes serão comunicadas com antecedência razoável, por e-mail ou aviso no aplicativo.'],
    },
    {
      heading: '12. Contato',
      paragraphs: ['suporte@dipzee.com'],
    },
  ],

  en: [
    {
      heading: '1. Acceptance of terms',
      paragraphs: ['By creating an account or using Dipzee, you agree to these Terms of Service and our Privacy Policy. If you do not agree, do not use the platform.'],
    },
    {
      heading: '2. What Dipzee is',
      paragraphs: [
        'Dipzee is a market information and analysis tool: a stock screener, watchlists, price alerts, self-reported portfolio tracking, and AI-generated analysis.',
        'Dipzee is NOT a broker-dealer, does not custody assets, does not execute buy or sell orders, and is not registered as an investment adviser in any jurisdiction.',
        'All content, including the "Opportunity Score" and AI-generated analysis, is for educational and informational purposes only and does NOT constitute financial or investment advice. Investment decisions are entirely your own responsibility.',
        'Market data shown is sourced from third-party providers (exchanges, financial data APIs, public sources) and may be delayed, inaccurate, or temporarily unavailable. We do not guarantee the accuracy, completeness, or timeliness of this data.',
      ],
    },
    {
      heading: '3. Eligibility and your account',
      list: [
        'You must be 18 or older to use Dipzee.',
        'You are responsible for keeping your password confidential and for all activity under your account.',
        'An account is personal and non-transferable.',
      ],
    },
    {
      heading: '4. Subscriptions and billing',
      list: [
        'Paid plans (Starter, Pro, Investor) are billed on a recurring basis (monthly or annual) via Stripe, with a 7-day free trial that requires a valid credit card.',
        'At the end of the trial, the chosen plan is billed automatically unless you cancel before the trial ends.',
        'You can change plans (upgrade or downgrade) at any time from Settings → Subscription; the change takes effect immediately, and any price difference is prorated on your next invoice.',
        'You can cancel your subscription at any time from the same menu. Canceling stops auto-renewal — you keep access to the paid plan until the end of the period you already paid for, with no future charges.',
        'We do not provide prorated refunds for already-paid periods, except where required by applicable law.',
      ],
    },
    {
      heading: '5. Acceptable use',
      paragraphs: ['You agree not to:'],
      list: [
        'Attempt to access restricted areas of the system without authorization.',
        'Reverse-engineer or run automated scraping against the platform.',
        'Resell or redistribute Dipzee’s data or analysis without authorization.',
        'Use the platform for any unlawful purpose.',
      ],
    },
    {
      heading: '6. Intellectual property',
      paragraphs: ['Dipzee’s brand, logo, design, and code belong to its operators. Third-party market data belongs to its respective providers and is used under their licensing terms.'],
    },
    {
      heading: '7. Disclaimer',
      paragraphs: [
        'The service is provided "as is" and "as available." We do not guarantee the platform will be free of errors or interruptions.',
        'We are not responsible for financial losses resulting from investment decisions made based on information, scores, or analysis from the platform.',
      ],
    },
    {
      heading: '8. Limitation of liability',
      paragraphs: ['To the maximum extent permitted by law, our total liability for any claim related to the service is limited to the amount you paid in the 12 months before the event giving rise to the claim.'],
    },
    {
      heading: '9. Termination',
      paragraphs: ['We may suspend or terminate accounts that violate these terms. You can close your own account at any time using the self-service tools in Settings → My Data.'],
    },
    {
      heading: '10. Governing law',
      paragraphs: ['These terms are governed by the laws of Canada, the jurisdiction where Dipzee’s operating entity is being formally incorporated, without prejudice to any mandatory consumer rights granted by the law of your country of residence (for example, Brazil’s LGPD or the EU’s GDPR).'],
    },
    {
      heading: '11. Changes to these terms',
      paragraphs: ['We may update these terms periodically. Material changes will be communicated with reasonable notice, by email or an in-app notice.'],
    },
    {
      heading: '12. Contact',
      paragraphs: ['suporte@dipzee.com'],
    },
  ],

  es: [
    {
      heading: '1. Aceptación de los términos',
      paragraphs: ['Al crear una cuenta o usar Dipzee, aceptas estos Términos de Servicio y nuestra Política de Privacidad. Si no estás de acuerdo, no utilices la plataforma.'],
    },
    {
      heading: '2. Qué es Dipzee',
      paragraphs: [
        'Dipzee es una herramienta de información y análisis de mercado: screener de acciones, listas de seguimiento, alertas de precio, seguimiento de portafolio autodeclarado y análisis generados por IA.',
        'Dipzee NO es una correduría, no custodia activos, no ejecuta órdenes de compra o venta y no está registrado como asesor de inversiones en ninguna jurisdicción.',
        'Todo el contenido, incluido el "Opportunity Score" y los análisis generados por IA, tiene fines exclusivamente educativos e informativos y NO constituye asesoramiento financiero ni de inversión. Las decisiones de inversión son de tu exclusiva responsabilidad.',
        'Los datos de mercado mostrados provienen de proveedores externos (bolsas, APIs de datos financieros, fuentes públicas) y pueden contener retrasos, imprecisiones o indisponibilidad temporal. No garantizamos la exactitud, integridad ni actualidad de estos datos.',
      ],
    },
    {
      heading: '3. Elegibilidad y tu cuenta',
      list: [
        'Debes tener 18 años o más para usar Dipzee.',
        'Eres responsable de mantener la confidencialidad de tu contraseña y de toda actividad realizada en tu cuenta.',
        'Una cuenta es personal e intransferible.',
      ],
    },
    {
      heading: '4. Suscripciones y facturación',
      list: [
        'Los planes pagos (Starter, Pro, Investidor) se cobran de forma recurrente (mensual o anual) a través de Stripe, con un período de prueba gratuito de 7 días que requiere una tarjeta de crédito válida.',
        'Al finalizar la prueba, el plan elegido se cobra automáticamente salvo que canceles antes de que termine.',
        'Puedes cambiar de plan (subir o bajar de nivel) en cualquier momento desde Configuración → Suscripción; el cambio se aplica de inmediato y cualquier diferencia de precio se prorratea en tu próxima factura.',
        'Puedes cancelar tu suscripción en cualquier momento desde el mismo menú. Cancelar detiene la renovación automática — conservas el acceso al plan pago hasta el final del período ya pagado, sin cargos futuros.',
        'No ofrecemos reembolsos prorrateados de períodos ya pagados, salvo que la ley aplicable lo exija.',
      ],
    },
    {
      heading: '5. Uso aceptable',
      paragraphs: ['Aceptas no:'],
      list: [
        'Intentar acceder a áreas restringidas del sistema sin autorización.',
        'Realizar ingeniería inversa o scraping automatizado contra la plataforma.',
        'Revender o redistribuir los datos o análisis de Dipzee sin autorización.',
        'Usar la plataforma con fines ilegales.',
      ],
    },
    {
      heading: '6. Propiedad intelectual',
      paragraphs: ['La marca, el logotipo, el diseño y el código de Dipzee pertenecen a sus operadores. Los datos de mercado de terceros pertenecen a sus respectivos proveedores y se usan bajo sus condiciones de licencia.'],
    },
    {
      heading: '7. Exención de responsabilidad',
      paragraphs: [
        'El servicio se proporciona "tal cual" y "según disponibilidad". No garantizamos que la plataforma esté libre de errores o interrupciones.',
        'No somos responsables de pérdidas financieras derivadas de decisiones de inversión basadas en información, puntuaciones o análisis de la plataforma.',
      ],
    },
    {
      heading: '8. Limitación de responsabilidad',
      paragraphs: ['En la máxima medida permitida por la ley, nuestra responsabilidad total por cualquier reclamo relacionado con el servicio se limita al monto que hayas pagado en los 12 meses anteriores al evento que originó el reclamo.'],
    },
    {
      heading: '9. Terminación',
      paragraphs: ['Podemos suspender o cancelar cuentas que violen estos términos. Puedes cerrar tu propia cuenta en cualquier momento usando las herramientas de autoservicio en Configuración → Mis Datos.'],
    },
    {
      heading: '10. Ley aplicable',
      paragraphs: ['Estos términos se rigen por las leyes de Canadá, jurisdicción donde se está constituyendo formalmente la entidad operadora de Dipzee, sin perjuicio de los derechos obligatorios que la legislación de tu país de residencia (por ejemplo, la LGPD de Brasil o el RGPD de la UE) te otorgue como consumidor.'],
    },
    {
      heading: '11. Cambios a estos términos',
      paragraphs: ['Podemos actualizar estos términos periódicamente. Los cambios importantes se comunicarán con antelación razonable, por correo o aviso dentro de la aplicación.'],
    },
    {
      heading: '12. Contacto',
      paragraphs: ['suporte@dipzee.com'],
    },
  ],

  fr: [
    {
      heading: '1. Acceptation des conditions',
      paragraphs: ['En créant un compte ou en utilisant Dipzee, vous acceptez les présentes Conditions d’utilisation ainsi que notre Politique de confidentialité. Si vous n’êtes pas d’accord, n’utilisez pas la plateforme.'],
    },
    {
      heading: '2. Ce qu’est Dipzee',
      paragraphs: [
        'Dipzee est un outil d’information et d’analyse de marché : screener d’actions, listes de suivi, alertes de prix, suivi de portefeuille autodéclaré et analyses générées par IA.',
        'Dipzee N’EST PAS un courtier, ne conserve pas d’actifs, n’exécute aucun ordre d’achat ou de vente et n’est enregistré comme conseiller en placement dans aucune juridiction.',
        'L’ensemble du contenu, y compris le « Opportunity Score » et les analyses générées par IA, est fourni à des fins éducatives et informatives uniquement et ne constitue PAS un conseil financier ou en investissement. Les décisions d’investissement relèvent entièrement de votre responsabilité.',
        'Les données de marché affichées proviennent de fournisseurs tiers (bourses, API de données financières, sources publiques) et peuvent être retardées, inexactes ou temporairement indisponibles. Nous ne garantissons ni l’exactitude, ni l’exhaustivité, ni l’actualité de ces données.',
      ],
    },
    {
      heading: '3. Éligibilité et votre compte',
      list: [
        'Vous devez avoir 18 ans ou plus pour utiliser Dipzee.',
        'Vous êtes responsable de la confidentialité de votre mot de passe et de toute activité effectuée depuis votre compte.',
        'Un compte est personnel et non transférable.',
      ],
    },
    {
      heading: '4. Abonnements et facturation',
      list: [
        'Les forfaits payants (Starter, Pro, Investisseur) sont facturés de manière récurrente (mensuelle ou annuelle) via Stripe, avec un essai gratuit de 7 jours nécessitant une carte de crédit valide.',
        'À la fin de l’essai, le forfait choisi est facturé automatiquement sauf annulation avant la fin de l’essai.',
        'Vous pouvez changer de forfait (mise à niveau ou rétrogradation) à tout moment depuis Paramètres → Abonnement ; le changement prend effet immédiatement et toute différence de prix est proratisée sur votre prochaine facture.',
        'Vous pouvez annuler votre abonnement à tout moment depuis le même menu. L’annulation arrête le renouvellement automatique — vous conservez l’accès au forfait payant jusqu’à la fin de la période déjà payée, sans frais futurs.',
        'Nous ne remboursons pas au prorata les périodes déjà payées, sauf si la loi applicable l’exige.',
      ],
    },
    {
      heading: '5. Utilisation acceptable',
      paragraphs: ['Vous acceptez de ne pas :'],
      list: [
        'Tenter d’accéder à des zones restreintes du système sans autorisation.',
        'Effectuer de l’ingénierie inverse ou du scraping automatisé de la plateforme.',
        'Revendre ou redistribuer les données ou analyses de Dipzee sans autorisation.',
        'Utiliser la plateforme à des fins illégales.',
      ],
    },
    {
      heading: '6. Propriété intellectuelle',
      paragraphs: ['La marque, le logo, le design et le code de Dipzee appartiennent à ses exploitants. Les données de marché tierces appartiennent à leurs fournisseurs respectifs et sont utilisées selon leurs conditions de licence.'],
    },
    {
      heading: '7. Avertissement',
      paragraphs: [
        'Le service est fourni « tel quel » et « selon disponibilité ». Nous ne garantissons pas que la plateforme sera exempte d’erreurs ou d’interruptions.',
        'Nous ne sommes pas responsables des pertes financières résultant de décisions d’investissement prises sur la base d’informations, de scores ou d’analyses de la plateforme.',
      ],
    },
    {
      heading: '8. Limitation de responsabilité',
      paragraphs: ['Dans toute la mesure permise par la loi, notre responsabilité totale pour toute réclamation liée au service est limitée au montant que vous avez payé au cours des 12 mois précédant l’événement à l’origine de la réclamation.'],
    },
    {
      heading: '9. Résiliation',
      paragraphs: ['Nous pouvons suspendre ou résilier les comptes qui enfreignent les présentes conditions. Vous pouvez fermer votre propre compte à tout moment à l’aide des outils en libre-service dans Paramètres → Mes données.'],
    },
    {
      heading: '10. Loi applicable',
      paragraphs: ['Les présentes conditions sont régies par les lois du Canada, juridiction dans laquelle l’entité exploitant Dipzee est en cours de constitution formelle, sans préjudice des droits impératifs accordés aux consommateurs par la loi de votre pays de résidence (par exemple la LGPD au Brésil ou le RGPD dans l’UE).'],
    },
    {
      heading: '11. Modifications des présentes conditions',
      paragraphs: ['Nous pouvons mettre à jour ces conditions périodiquement. Les changements importants seront communiqués avec un préavis raisonnable, par e-mail ou par une notification dans l’application.'],
    },
    {
      heading: '12. Contact',
      paragraphs: ['suporte@dipzee.com'],
    },
  ],
};
