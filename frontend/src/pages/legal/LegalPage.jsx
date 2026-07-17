import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Logo } from '../../components/Logo';
import { LanguageSwitcher } from '../../components/Switchers';

export function LegalPage({ title, lastUpdated, sections, testId }) {
  return (
    <div className="min-h-screen bg-[var(--dz-bg)]">
      <div className="h-16 px-4 sm:px-6 flex items-center justify-between border-b border-[var(--dz-border)]">
        <Link to="/"><Logo /></Link>
        <LanguageSwitcher />
      </div>
      <div className="mx-auto max-w-3xl px-4 sm:px-6 py-12" data-testid={testId}>
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-[var(--dz-muted)] hover:text-[var(--dz-primary)]">
          <ArrowLeft size={14} /> Dipzee
        </Link>
        <h1 className="mt-4 font-heading font-bold text-3xl">{title}</h1>
        <p className="mt-2 text-sm text-[var(--dz-muted)]">{lastUpdated}</p>
        <div className="mt-8 space-y-8">
          {sections.map((s, i) => (
            <section key={i}>
              <h2 className="font-heading font-semibold text-lg">{s.heading}</h2>
              <div className="mt-2 space-y-3 text-sm text-[var(--dz-fg)] leading-relaxed">
                {s.paragraphs?.map((p, j) => <p key={j}>{p}</p>)}
                {s.list && (
                  <ul className="list-disc pl-5 space-y-1.5">
                    {s.list.map((li, j) => <li key={j}>{li}</li>)}
                  </ul>
                )}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
