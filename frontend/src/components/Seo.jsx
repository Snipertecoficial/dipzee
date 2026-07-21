import React from 'react';
import { Helmet } from 'react-helmet-async';

const SITE = 'https://dipzee.com';
const DEFAULT_IMAGE = `${SITE}/og-image.png`;

// Per-route <title>/description/canonical. This is a client-rendered SPA
// with no SSR, so these tags only reach crawlers that execute JavaScript
// (Googlebot, Bingbot and most modern AI crawlers do) — the static
// index.html meta/JSON-LD block is what covers crawlers that don't.
export function Seo({ title, description, path = '/', noindex = false }) {
  const fullTitle = title ? `${title} | Dipzee` : 'Dipzee — Buy Low, Earn Dividends, Sell High | Opportunity Score';
  const url = `${SITE}${path}`;
  return (
    <Helmet>
      <title>{fullTitle}</title>
      {description && <meta name="description" content={description} />}
      <meta name="robots" content={noindex ? 'noindex, nofollow' : 'index, follow'} />
      <link rel="canonical" href={url} />
      <meta property="og:title" content={fullTitle} />
      {description && <meta property="og:description" content={description} />}
      <meta property="og:url" content={url} />
      <meta property="og:image" content={DEFAULT_IMAGE} />
      <meta name="twitter:title" content={fullTitle} />
      {description && <meta name="twitter:description" content={description} />}
      <meta name="twitter:image" content={DEFAULT_IMAGE} />
    </Helmet>
  );
}
