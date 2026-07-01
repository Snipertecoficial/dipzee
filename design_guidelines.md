{
  "design_personality": {
    "brand_attributes": [
      "institucional",
      "sólido",
      "preciso",
      "transparente",
      "seguro",
      "global (multilíngue)"
    ],
    "north_star": "Parece uma fintech estabelecida (nível banco/corretora), com linguagem visual de infraestrutura: tipografia forte, grids rígidos, números em destaque, prova de confiança acima da dobra, e detalhes de produto reais (ScoreDial/RangeGauge + oportunidades ao vivo).",
    "anti_patterns": [
      "hero genérico com ilustração SaaS",
      "gradientes saturados ou dominantes",
      "layout centralizado tipo template",
      "promessas falsas (ex.: 'garantido', 'sem risco')",
      "excesso de badges/selos (máx. 3 por viewport)"
    ]
  },
  "existing_brand_constraints": {
    "must_keep": {
      "palette": {
        "primary_indigo": "#1A1F4D",
        "accent_mint": "#16E0A3",
        "canvas": "#F6F8FB",
        "signals": {
          "buy": "#16A34A",
          "hold": "#F59E0B",
          "reduce": "#F97316",
          "sell": "#E5484D"
        }
      },
      "typography": {
        "headings": "Sora",
        "body": "Inter"
      },
      "tokens_source": "/app/frontend/src/index.css"
    },
    "cta_copy": {
      "primary": "Iniciar teste grátis de 7 dias",
      "note": "Trial exige cartão. Cancelamento a qualquer momento."
    },
    "removed_sections": [
      "Remover seção atual: 'Um número. Uma decisão clara.' (score explainer)"
    ]
  },
  "design_tokens": {
    "css_custom_properties": {
      "note": "NÃO inventar nova paleta; apenas organizar usos e criar tokens derivados (tints/alphas) a partir dos existentes.",
      "add_to_index_css": {
        "surface_layers": {
          "--dz-surface-2": "color-mix(in srgb, var(--dz-surface) 92%, var(--dz-primary))",
          "--dz-surface-3": "color-mix(in srgb, var(--dz-surface) 86%, var(--dz-primary))"
        },
        "alpha_overlays": {
          "--dz-primary-8": "rgba(26, 31, 77, 0.08)",
          "--dz-primary-12": "rgba(26, 31, 77, 0.12)",
          "--dz-mint-10": "rgba(22, 224, 163, 0.10)",
          "--dz-mint-16": "rgba(22, 224, 163, 0.16)"
        },
        "focus": {
          "--dz-ring": "0 0 0 3px var(--dz-mint-16)",
          "--dz-ring-strong": "0 0 0 4px var(--dz-mint-16), 0 0 0 1px var(--dz-primary)"
        },
        "radius": {
          "--dz-radius-sm": "0.75rem",
          "--dz-radius-md": "0.875rem",
          "--dz-radius-lg": "1.25rem"
        },
        "shadows": {
          "--dz-shadow-card": "0 1px 2px rgba(15, 20, 36, 0.06), 0 12px 28px rgba(15, 20, 36, 0.08)",
          "--dz-shadow-float": "0 18px 40px rgba(15, 20, 36, 0.14)"
        }
      }
    },
    "tailwind_usage": {
      "backgrounds": [
        "bg-[var(--dz-bg)]",
        "bg-[var(--dz-surface)]",
        "bg-[color:var(--dz-surface-2)]"
      ],
      "text": [
        "text-[var(--dz-fg)]",
        "text-[var(--dz-muted)]",
        "text-[color:var(--dz-primary)]"
      ],
      "borders": [
        "border-[var(--dz-border)]",
        "ring-1 ring-[var(--dz-primary-12)]"
      ]
    },
    "gradients": {
      "restriction": "Aplicar gradientes apenas como fundo decorativo de seção (hero/CTA final) e sempre <20% do viewport. Nunca em áreas de leitura ou elementos pequenos.",
      "allowed_examples": [
        {
          "name": "hero-institutional-wash",
          "css": "radial-gradient(900px 420px at 15% 10%, rgba(22,224,163,0.14) 0%, rgba(22,224,163,0.00) 60%), radial-gradient(900px 420px at 85% 0%, rgba(26,31,77,0.10) 0%, rgba(26,31,77,0.00) 55%)",
          "usage": "Somente no background do hero (atrás do conteúdo), com noise overlay leve."
        },
        {
          "name": "cta-footer-wash",
          "css": "radial-gradient(700px 320px at 50% 0%, rgba(22,224,163,0.12) 0%, rgba(22,224,163,0.00) 60%)",
          "usage": "CTA final (faixa curta), não no footer inteiro."
        }
      ]
    },
    "texture": {
      "noise_overlay": {
        "css": "background-image: url('data:image/svg+xml,%3Csvg xmlns=\"http://www.w3.org/2000/svg\" width=\"160\" height=\"160\"%3E%3Cfilter id=\"n\"%3E%3CfeTurbulence type=\"fractalNoise\" baseFrequency=\"0.9\" numOctaves=\"3\" stitchTiles=\"stitch\"/%3E%3C/filter%3E%3Crect width=\"160\" height=\"160\" filter=\"url(%23n)\" opacity=\"0.08\"/%3E%3C/svg%3E');",
        "usage": "Aplicar como pseudo-elemento ::before em hero e CTA final (opacidade 0.06–0.10)."
      }
    }
  },
  "typography": {
    "fonts": {
      "headings": {
        "family": "var(--dz-font-heading)",
        "usage": "Headlines, números-chave, títulos de seção"
      },
      "body": {
        "family": "var(--dz-font-body)",
        "usage": "Parágrafos, labels, microcopy, FAQ"
      },
      "numeric": {
        "class": "tnum",
        "usage": "Preços, percentuais, scores, tabelas"
      }
    },
    "scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight",
      "h2": "text-base md:text-lg text-[var(--dz-muted)]",
      "section_title": "text-2xl sm:text-3xl font-semibold",
      "card_title": "text-lg font-semibold",
      "body": "text-sm sm:text-base leading-relaxed",
      "small": "text-xs sm:text-sm text-[var(--dz-muted)]"
    },
    "copy_rules_for_i18n": [
      "Evitar linhas muito longas: limitar blocos de texto a max-w-[60ch]",
      "Botões com padding horizontal generoso para acomodar traduções (ex.: FR)",
      "Nunca truncar textos críticos; permitir wrap"
    ]
  },
  "layout_and_grid": {
    "container": "max-w-6xl mx-auto px-4 sm:px-6 lg:px-8",
    "section_spacing": {
      "default": "py-14 sm:py-18 lg:py-24",
      "dense": "py-10 sm:py-12",
      "hero": "pt-10 sm:pt-14 lg:pt-18 pb-12 sm:pb-16"
    },
    "grid_patterns": {
      "hero": "grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-start",
      "two_col": "grid grid-cols-1 md:grid-cols-2 gap-8",
      "three_col": "grid grid-cols-1 md:grid-cols-3 gap-6",
      "bento": "grid grid-cols-1 md:grid-cols-12 gap-6"
    },
    "reading_flow": "Sempre alinhado à esquerda; usar F-pattern com blocos curtos e números grandes para credibilidade."
  },
  "components": {
    "component_path": {
      "shadcn_primary": [
        "/app/frontend/src/components/ui/button.jsx",
        "/app/frontend/src/components/ui/card.jsx",
        "/app/frontend/src/components/ui/accordion.jsx",
        "/app/frontend/src/components/ui/navigation-menu.jsx",
        "/app/frontend/src/components/ui/sheet.jsx",
        "/app/frontend/src/components/ui/separator.jsx",
        "/app/frontend/src/components/ui/badge.jsx",
        "/app/frontend/src/components/ui/table.jsx",
        "/app/frontend/src/components/ui/tooltip.jsx",
        "/app/frontend/src/components/ui/sonner.jsx"
      ],
      "existing_app_components_to_reuse": [
        "Logo / LogoMark",
        "ScoreDial",
        "RangeGauge52w",
        "SignalBadge",
        "PricingCards"
      ]
    },
    "button_system": {
      "style": "Professional/Corporate com toque premium: radius 10–14px, sombra leve, hover com elevação e borda.",
      "variants": {
        "primary": {
          "usage": "CTA principal (trial)",
          "classes": "bg-[var(--dz-primary)] text-white hover:bg-[color:color-mix(in_srgb,var(--dz-primary)_92%,black)] shadow-[var(--dz-elev-1)] hover:shadow-[var(--dz-elev-2)]",
          "data_testid_examples": [
            "home-hero-primary-cta-button",
            "pricing-primary-cta-button",
            "auth-submit-button"
          ]
        },
        "secondary": {
          "usage": "Ações secundárias (ver pricing, ver como funciona)",
          "classes": "bg-[var(--dz-surface)] text-[var(--dz-primary)] border border-[var(--dz-border)] hover:bg-[color:var(--dz-surface-2)]"
        },
        "ghost": {
          "usage": "Links de navegação e ações discretas",
          "classes": "text-[var(--dz-primary)] hover:bg-[var(--dz-primary-8)]"
        }
      },
      "interaction": {
        "press": "active:scale-[0.98]",
        "transition": "transition-colors transition-shadow duration-200",
        "focus": "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] focus-visible:ring-offset-2"
      }
    },
    "cards": {
      "style": "Cartões institucionais: fundo branco, borda sutil, sombra controlada, header com título + microcopy.",
      "classes": "bg-[var(--dz-surface)] border border-[var(--dz-border)] rounded-[var(--radius)] shadow-[var(--dz-shadow-card)]"
    }
  },
  "page_blueprints": {
    "home_public": {
      "topbar": {
        "goal": "Navegação institucional + idioma + CTA persistente.",
        "structure": [
          "Left: LogoMark + wordmark",
          "Center (desktop): NavigationMenu (Como funciona, Oportunidades, Preços, FAQ, Segurança)",
          "Right: Language switch (DropdownMenu) + Entrar (ghost) + CTA (primary)"
        ],
        "mobile": "Usar Sheet (hamburger) com links + seletor de idioma + CTA fixo no final do menu.",
        "data_testids": [
          "public-topbar",
          "public-topbar-language-menu",
          "public-topbar-login-link",
          "public-topbar-primary-cta-button",
          "public-topbar-mobile-menu-button"
        ],
        "micro_interactions": [
          "Topbar sticky com blur leve: backdrop-blur + bg branco com alpha (sem glass pesado)",
          "Shadow aparece ao scroll (framer-motion ou CSS class toggle)"
        ]
      },
      "hero": {
        "layout": "Split editorial: esquerda copy + CTAs; direita 'Product Proof' (ScoreDial + RangeGauge + mini tabela de oportunidades).",
        "content": {
          "headline": "Opportunity Score para comprar na baixa, receber dividendos e vender na alta.",
          "subhead": "Sinais claros (0–100) com contexto de 52 semanas e oportunidades ao vivo. Feito para investidores de varejo que exigem disciplina.",
          "cta_primary": "Iniciar teste grátis de 7 dias",
          "cta_secondary": "Ver preços",
          "microcopy": "7 dias grátis • Cartão obrigatório • Cancele quando quiser"
        },
        "credibility_band": {
          "pattern": "Uma faixa compacta abaixo dos CTAs com 3 itens (não logos falsos):",
          "items": [
            "Criptografia em trânsito e em repouso",
            "Pagamentos processados com segurança (PCI-ready messaging sem afirmar certificação)",
            "Dados e privacidade: controles e transparência"
          ],
          "component": "Badge + Separator",
          "data_testid": "home-hero-credibility-band"
        },
        "product_proof_panel": {
          "composition": [
            "Card grande: ScoreDial (com label 'Opportunity Score')",
            "Card médio: RangeGauge52w",
            "Card pequeno: 'Top oportunidades agora' (3 linhas)"
          ],
          "note": "Evitar mock falso: usar skeleton enquanto carrega /public/top-opportunities."
        },
        "background": "Aplicar hero-institutional-wash + noise overlay (opacidade baixa).",
        "data_testids": [
          "home-hero",
          "home-hero-primary-cta-button",
          "home-hero-secondary-cta-button",
          "home-hero-score-dial",
          "home-hero-range-gauge",
          "home-hero-top-opportunities-preview"
        ]
      },
      "proof_of_scale_strip": {
        "goal": "Substituir 'logo wall' por prova de escala honesta (sem inventar marcas).",
        "layout": "Faixa horizontal com 3–4 métricas + 1 frase de confiança.",
        "examples": [
          "Atualizado em tempo real",
          "Cobertura multi-mercado (se aplicável via i18n)",
          "Sinais: Buy/Hold/Reduce/Sell",
          "Uptime/latência apenas se houver dado real; senão usar 'Infraestrutura monitorada 24/7'"
        ],
        "components": "Card (flat) + icons lucide-react",
        "data_testid": "home-proof-strip"
      },
      "how_it_works": {
        "structure": "3 passos em cards numerados (01/02/03) com microcopy curto.",
        "steps": [
          "Conecte seu objetivo (dividendos/valor)",
          "Veja o Opportunity Score + faixa 52 semanas",
          "Aja com disciplina: comprar, segurar, reduzir, vender"
        ],
        "components": "Card + Badge (número) + Button link",
        "data_testid": "home-how-it-works"
      },
      "live_top_opportunities": {
        "goal": "Prova de produto com dados reais via /public/top-opportunities.",
        "layout": "Tabela institucional (Table) com colunas: Ticker, Score, Sinal, Dividend Yield (se existir), Atualizado.",
        "states": [
          "loading: Skeleton rows",
          "error: Alert com retry",
          "empty: Card com explicação"
        ],
        "components": "Table + SignalBadge + Tooltip",
        "data_testids": [
          "home-top-opportunities-section",
          "home-top-opportunities-table",
          "home-top-opportunities-refresh-button"
        ],
        "micro_interactions": [
          "Refresh com rotação do ícone + toast (sonner) 'Atualizado'",
          "Row hover: bg-[var(--dz-primary-8)]"
        ]
      },
      "feature_grid": {
        "layout": "Bento grid (md:grid-cols-12) com 5–6 cards: 2 grandes + 4 pequenos.",
        "feature_themes": [
          "Score 0–100 com contexto",
          "Faixa 52 semanas",
          "Sinais claros (Buy/Hold/Reduce/Sell)",
          "Alertas/Watchlist (se existir; senão 'Acompanhe oportunidades')",
          "Multilíngue",
          "Transparência de preços"
        ],
        "data_testid": "home-feature-grid"
      },
      "security_trust_section": {
        "goal": "Resolver objeção 'posso confiar meu cartão e meus dados?'.",
        "layout": "2 colunas: esquerda texto + bullets; direita cards com 'Controles' e 'Boas práticas'.",
        "content_rules": [
          "Não afirmar certificações específicas (SOC2/PCI) se não forem verdade.",
          "Usar linguagem: 'padrões de mercado', 'criptografia', 'boas práticas', 'processadores de pagamento confiáveis' (sem citar nomes se não houver)."
        ],
        "modules": [
          "Criptografia em trânsito (TLS) e em repouso",
          "Princípio do menor privilégio",
          "Monitoramento e logs",
          "Privacidade e controle de dados",
          "Pagamentos: checkout seguro + cancelamento fácil"
        ],
        "components": "Card + Badge (mint) + Separator",
        "data_testid": "home-security-trust"
      },
      "pricing": {
        "goal": "3 planos pagos + trial 7 dias com cartão.",
        "component": "PricingCards (existente)",
        "requirements": [
          "Todos CTAs: 'Iniciar teste grátis de 7 dias'",
          "Mostrar microcopy: 'Cartão obrigatório' perto do CTA",
          "Destacar plano do meio (Pro) com borda mint sutil (não gradiente)"
        ],
        "data_testids": [
          "home-pricing",
          "home-pricing-plan-iniciante",
          "home-pricing-plan-pro",
          "home-pricing-plan-investidor"
        ]
      },
      "faq": {
        "component": "Accordion (shadcn)",
        "topics": [
          "Como funciona o trial de 7 dias?",
          "Posso cancelar a qualquer momento?",
          "O Opportunity Score é recomendação? (disclaimer)",
          "Quais mercados/ações são cobertos?",
          "Como vocês lidam com meus dados?",
          "Idiomas suportados"
        ],
        "data_testid": "home-faq"
      },
      "final_cta": {
        "layout": "Faixa curta com fundo suave (cta-footer-wash) + card central com CTA.",
        "copy": "Comece com 7 dias grátis e veja oportunidades ao vivo.",
        "data_testid": "home-final-cta"
      },
      "footer": {
        "goal": "Rodapé institucional robusto (links + idiomas + disclaimer).",
        "layout": "Grid 2–4 colunas + bloco de disclaimer separado por Separator.",
        "links": [
          "Produto (Como funciona, Preços, FAQ)",
          "Empresa (Contato, Segurança, Privacidade, Termos)",
          "Idiomas (EN/FR/PT/ES)",
          "Social (se existir)"
        ],
        "disclaimer": "Conteúdo informativo; não constitui recomendação de investimento. Investimentos envolvem riscos.",
        "data_testids": [
          "public-footer",
          "public-footer-language-links",
          "public-footer-disclaimer"
        ]
      }
    },
    "auth_login_register": {
      "layout": "AuthLayout split-screen: esquerda 'brand + live opportunities', direita formulário.",
      "left_panel": {
        "content": [
          "Logo + tagline curta",
          "Mini bloco 'Top oportunidades agora' (mesma API /public/top-opportunities)",
          "Bloco 'Segurança' com 2 bullets (criptografia, checkout seguro)"
        ],
        "visual": "Fundo canvas com wash leve (sem gradiente pesado) + cards brancos.",
        "data_testid": "auth-left-panel"
      },
      "right_panel_form": {
        "login": {
          "fields": [
            "email",
            "password"
          ],
          "actions": [
            "Entrar (primary)",
            "Esqueci minha senha (link)",
            "Criar conta (secondary link)"
          ],
          "trust_microcopy": "Ao entrar, seus dados permanecem protegidos.",
          "data_testids": [
            "login-form",
            "login-email-input",
            "login-password-input",
            "login-submit-button",
            "login-forgot-password-link",
            "login-signup-link"
          ]
        },
        "register": {
          "fields": [
            "name (se existir)",
            "email",
            "password",
            "confirm password"
          ],
          "actions": [
            "Iniciar teste grátis de 7 dias (primary)",
            "Já tenho conta (link)"
          ],
          "trial_notice": "7 dias grátis • Cartão obrigatório • Cancele quando quiser",
          "payment_trust": "Adicionar linha com ícone de cadeado + 'Checkout seguro' (sem afirmar PCI/SOC2).",
          "data_testids": [
            "register-form",
            "register-email-input",
            "register-password-input",
            "register-submit-button",
            "register-login-link",
            "register-trial-notice"
          ]
        }
      },
      "form_components": [
        "Input (shadcn)",
        "Label (shadcn)",
        "Button (shadcn)",
        "Card (shadcn)",
        "Sonner toasts for errors/success"
      ],
      "micro_interactions": [
        "Validação inline com transição de opacidade (duration-150)",
        "Botão submit com estado loading (spinner lucide) e disabled",
        "Toast de erro com mensagem curta e ação 'Tentar novamente'"
      ]
    }
  },
  "motion_and_microinteractions": {
    "library": "framer-motion (já instalado)",
    "principles": [
      "Motion como feedback, não decoração",
      "Duração curta (150–240ms) e easing suave",
      "Evitar animações contínuas pesadas"
    ],
    "recommended_patterns": {
      "section_reveal": {
        "description": "Entrada sutil ao scroll (opacity + y).",
        "js_scaffold": "// .js\nimport { motion } from 'framer-motion'\n\nconst fadeUp = {\n  hidden: { opacity: 0, y: 10 },\n  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] } }\n}\n\n// usage: <motion.div variants={fadeUp} initial=\"hidden\" whileInView=\"show\" viewport={{ once: true, margin: '-80px' }} />"
      },
      "topbar_shadow_on_scroll": {
        "description": "Adicionar sombra/borda quando scrollY > 8.",
        "js_scaffold": "// .js\nconst [scrolled, setScrolled] = useState(false)\nuseEffect(() => {\n  const onScroll = () => setScrolled(window.scrollY > 8)\n  onScroll()\n  window.addEventListener('scroll', onScroll)\n  return () => window.removeEventListener('scroll', onScroll)\n}, [])"
      }
    },
    "no_universal_transition_rule": "Nunca usar transition-all. Usar transition-colors/transition-shadow/transition-opacity conforme necessário."
  },
  "accessibility": {
    "requirements": [
      "Contraste AA: texto muted apenas em fundos claros e com tamanho adequado",
      "Focus visível em todos inputs/botões (ring mint)",
      "Estados disabled claros",
      "Tabelas com headers semânticos",
      "Links com underline no hover/focus"
    ],
    "keyboard": [
      "NavigationMenu e Sheet navegáveis por teclado",
      "Accordion com aria (shadcn já cobre)"
    ]
  },
  "data_testid_policy": {
    "rule": "Todo elemento interativo e toda informação crítica deve ter data-testid em kebab-case.",
    "examples": [
      "home-hero-primary-cta-button",
      "home-top-opportunities-table",
      "pricing-plan-pro-cta-button",
      "auth-language-menu",
      "footer-privacy-policy-link"
    ]
  },
  "image_urls": {
    "note": "Preferir SEM fotos stock para manter ar institucional e evitar 'SaaS genérico'. Usar UI real (ScoreDial/RangeGauge) + padrões gráficos (noise/wash). Se precisar de imagem, usar apenas 1 foto editorial discreta (ex.: mãos digitando em notebook) e manter baixa saturação.",
    "categories": [
      {
        "category": "optional-editorial-hero",
        "description": "Foto editorial discreta para reforçar 'investidor real' (usar apenas se o hero parecer vazio).",
        "urls": []
      }
    ]
  },
  "additional_libraries": {
    "recommended": [],
    "avoid": [
      "three.js/R3F (desnecessário para institucional e pode parecer gimmick)",
      "particles (risco de parecer cripto/marketing)"
    ]
  },
  "instructions_to_main_agent": {
    "implementation_notes": [
      "Manter tokens e fontes existentes (Sora/Inter) e cores Dipzee; apenas reorganizar layout e hierarquia.",
      "Home deve parecer 'institucional': tipografia forte, números, tabelas, prova de confiança acima da dobra.",
      "Não inventar logos de parceiros/selos. Use mensagens de segurança genéricas e honestas.",
      "Remover seção 'Um número. Uma decisão clara.' e substituir por: proof strip + security/trust section.",
      "CTAs sempre 'Iniciar teste grátis de 7 dias' (sem plano grátis).",
      "Garantir light/dark: usar tokens HSL do shadcn já definidos; evitar fundos muito escuros no marketing (usar dark mode como alternativa, não default).",
      "Todos elementos interativos/informativos com data-testid."
    ],
    "suggested_section_order": [
      "Topbar",
      "Hero (com product proof + credibility band)",
      "Proof of scale strip",
      "Como funciona (3 passos)",
      "Top oportunidades ao vivo (tabela)",
      "Feature bento grid",
      "Segurança & confiança",
      "Pricing (3 planos pagos)",
      "FAQ",
      "CTA final",
      "Footer institucional"
    ]
  }
}

<General UI UX Design Guidelines>  
    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms
    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text
   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json

 **GRADIENT RESTRICTION RULE**
NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc
NEVER use dark gradients for logo, testimonial, footer etc
NEVER let gradients cover more than 20% of the viewport.
NEVER apply gradients to text-heavy content or reading areas.
NEVER use gradients on small UI elements (<100px width).
NEVER stack multiple gradient layers in the same viewport.

**ENFORCEMENT RULE:**
    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors

**How and where to use:**
   • Section backgrounds (not content backgrounds)
   • Hero section header content. Eg: dark to light to dark color
   • Decorative overlays and accent elements only
   • Hero section with 2-3 mild color
   • Gradients creation can be done for any angle say horizontal, vertical or diagonal

- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**

</Font Guidelines>

- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. 
   
- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.

- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.
   
- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly
    Eg: - if it implies playful/energetic, choose a colorful scheme
           - if it implies monochrome/minimal, choose a black–white/neutral scheme

**Component Reuse:**
	- Prioritize using pre-existing components from src/components/ui when applicable
	- Create new components that match the style and conventions of existing components when needed
	- Examine existing components to understand the project's component patterns before creating new ones

**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component

**Best Practices:**
	- Use Shadcn/UI as the primary component library for consistency and accessibility
	- Import path: ./components/[component-name]

**Export Conventions:**
	- Components MUST use named exports (export const ComponentName = ...)
	- Pages MUST use default exports (export default function PageName() {...})

**Toasts:**
  - Use `sonner` for toasts"
  - Sonner component are located in `/app/src/components/ui/sonner.tsx`

Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.
</General UI UX Design Guidelines>
