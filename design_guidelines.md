{
  "meta": {
    "product": "Dipzee",
    "scope": "Redesign das áreas logadas (app shell + páginas internas) mantendo 100% identidade de marca e tokens existentes",
    "non_goals": [
      "Não redesenhar landing page",
      "Não redesenhar login (já split-screen)",
      "Não alterar tokens de cor/tipografia já definidos; apenas evoluir layout, hierarquia, densidade e estados"
    ],
    "tech": {
      "frontend": "React (CRA) .js/.jsx + Tailwind",
      "ui": "shadcn/ui (Radix) em /app/frontend/src/components/ui",
      "icons": "lucide-react",
      "i18n": "react-i18next (strings longas EN/FR/PT/ES)",
      "backend": "FastAPI",
      "testing": "data-testid obrigatório em elementos interativos e informativos"
    }
  },

  "brand_and_personality": {
    "attributes": [
      "Fintech premium",
      "Calmo e transparente",
      "Decisão em 3 segundos (clareza > decoração)",
      "Alta densidade com respiro (informação compacta, mas legível)",
      "Confiança: consistência, estados bem definidos, números alinhados"
    ],
    "keep_existing": {
      "colors": {
        "primary": "#1A1F4D",
        "accent": "#16E0A3",
        "canvas": "#F6F8FB",
        "signals": {
          "buy": "#16A34A",
          "hold": "#F59E0B",
          "reduce": "#F97316",
          "sell": "#E5484D"
        }
      },
      "fonts": {
        "headings": "Sora",
        "body": "Inter"
      },
      "dark_mode": "Suportado (não quebrar)."
    },
    "visual_style": {
      "layout_principles": [
        "Sidebar persistente em desktop (colapsável) + topbar compacta",
        "Bento grid para dashboard (cards com alturas coerentes)",
        "Progressive disclosure: resumo primeiro, detalhes em tabs/drawers",
        "F-pattern: métrica principal no topo-esquerda; ações no topo-direita"
      ],
      "surface_language": [
        "Canvas suave (dz-canvas) + cards brancos com borda sutil",
        "Sombras discretas (elev-1/elev-2) apenas para hierarquia",
        "Separators e linhas para tabelas (evitar excesso de cards)"
      ]
    }
  },

  "typography": {
    "font_pairing": {
      "heading": "var(--dz-font-heading)  // Sora",
      "body": "var(--dz-font-body)      // Inter",
      "numbers": "Inter + .tnum (tabular-nums) para preços/percentuais"
    },
    "scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl (usar só em páginas de marketing; nas áreas logadas preferir text-2xl/3xl)",
      "page_title": "text-2xl sm:text-3xl font-semibold tracking-tight",
      "section_title": "text-base md:text-lg font-semibold",
      "body": "text-sm md:text-base",
      "caption": "text-xs text-muted-foreground",
      "numeric": "text-sm md:text-base font-medium tnum"
    },
    "i18n_rules": [
      "Evitar truncar títulos críticos; preferir wrap + max-w",
      "Para labels longas: usar text-xs + leading-snug",
      "Botões: permitir quebra em 2 linhas apenas em mobile (whitespace-normal)"
    ]
  },

  "layout_and_grid": {
    "app_shell": {
      "desktop": {
        "structure": "Sidebar (w-64) + Main (flex-1) + Topbar sticky",
        "sidebar_behavior": "Colapsável para ícones (w-16) com tooltips; persistente em >=lg",
        "topbar": "Sticky top-0 com blur leve; contém search, quick actions, idioma/moeda, notificações, usuário"
      },
      "mobile": {
        "structure": "Topbar + Sheet/Drawer para navegação",
        "nav": "Hamburger abre Sheet com nav + watchlists + settings"
      },
      "content_container": {
        "max_width": "max-w-[1400px] (somente para páginas com leitura; tabelas podem ser full)",
        "padding": "px-4 sm:px-6 lg:px-8 py-5",
        "vertical_rhythm": "gap-4 sm:gap-6"
      }
    },
    "page_templates": {
      "dashboard": "grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6",
      "two_panel": "lg:grid-cols-12 com painel esquerdo (filtros) 4 cols + resultados 8 cols",
      "detail": "header + grid 12 cols: summary 8 + side insights 4 (vira 1 col no mobile)",
      "admin": "tabs + table-first (densidade alta)"
    }
  },

  "color_and_tokens_usage": {
    "rule": "Reutilizar tokens existentes em /app/frontend/src/index.css (dz-*) e HSL shadcn (:root --primary/--accent etc).",
    "semantic_usage": {
      "buy": "Somente para sinal/ação positiva (Badge, delta, highlights)",
      "hold": "Somente para neutro/atenção",
      "reduce": "Somente para reduzir exposição",
      "sell": "Somente para risco/negativo/destructive"
    },
    "dark_mode_notes": [
      "Garantir contraste AA em badges e textos",
      "Evitar fundos muito saturados; usar surfaces e bordas"
    ]
  },

  "components_and_paths": {
    "primary_shell": {
      "use": [
        {
          "name": "Sheet",
          "path": "/app/frontend/src/components/ui/sheet.jsx",
          "purpose": "Sidebar mobile"
        },
        {
          "name": "ScrollArea",
          "path": "/app/frontend/src/components/ui/scroll-area.jsx",
          "purpose": "Sidebar com listas longas (watchlists, admin menus)"
        },
        {
          "name": "Command",
          "path": "/app/frontend/src/components/ui/command.jsx",
          "purpose": "Global search (assets/news) com teclado"
        },
        {
          "name": "Breadcrumb",
          "path": "/app/frontend/src/components/ui/breadcrumb.jsx",
          "purpose": "Contexto de navegação"
        },
        {
          "name": "DropdownMenu",
          "path": "/app/frontend/src/components/ui/dropdown-menu.jsx",
          "purpose": "Menu usuário, idioma/moeda"
        },
        {
          "name": "Tabs",
          "path": "/app/frontend/src/components/ui/tabs.jsx",
          "purpose": "Sub-navegação em páginas densas (Asset, Admin, Settings)"
        }
      ]
    },
    "data_display": {
      "use": [
        {
          "name": "Card",
          "path": "/app/frontend/src/components/ui/card.jsx",
          "purpose": "Agrupar métricas e blocos"
        },
        {
          "name": "Badge",
          "path": "/app/frontend/src/components/ui/badge.jsx",
          "purpose": "SignalBadge wrapper/estados"
        },
        {
          "name": "Table",
          "path": "/app/frontend/src/components/ui/table.jsx",
          "purpose": "Watchlist (modo tabela), Screener results, Admin users"
        },
        {
          "name": "Skeleton",
          "path": "/app/frontend/src/components/ui/skeleton.jsx",
          "purpose": "Loading states premium"
        },
        {
          "name": "Separator",
          "path": "/app/frontend/src/components/ui/separator.jsx",
          "purpose": "Divisões em listas e painéis"
        },
        {
          "name": "Tooltip",
          "path": "/app/frontend/src/components/ui/tooltip.jsx",
          "purpose": "Explicar métricas (Opportunity Score, target)"
        },
        {
          "name": "HoverCard",
          "path": "/app/frontend/src/components/ui/hover-card.jsx",
          "purpose": "Preview rápido de ativo ao hover em tabelas"
        }
      ]
    },
    "forms_filters": {
      "use": [
        {
          "name": "Input",
          "path": "/app/frontend/src/components/ui/input.jsx",
          "purpose": "Search local, filtros"
        },
        {
          "name": "Select",
          "path": "/app/frontend/src/components/ui/select.jsx",
          "purpose": "Filtros do screener"
        },
        {
          "name": "Slider",
          "path": "/app/frontend/src/components/ui/slider.jsx",
          "purpose": "Ranges (dividend yield, score, price)"
        },
        {
          "name": "Checkbox",
          "path": "/app/frontend/src/components/ui/checkbox.jsx",
          "purpose": "Colunas visíveis / filtros"
        },
        {
          "name": "Calendar",
          "path": "/app/frontend/src/components/ui/calendar.jsx",
          "purpose": "Alertas por data (se aplicável)"
        },
        {
          "name": "Switch",
          "path": "/app/frontend/src/components/ui/switch.jsx",
          "purpose": "Toggles (notificações, dark mode)"
        },
        {
          "name": "Dialog",
          "path": "/app/frontend/src/components/ui/dialog.jsx",
          "purpose": "Criar/editar alertas"
        }
      ]
    },
    "feedback": {
      "use": [
        {
          "name": "Alert",
          "path": "/app/frontend/src/components/ui/alert.jsx",
          "purpose": "Error state inline"
        },
        {
          "name": "Sonner",
          "path": "/app/frontend/src/components/ui/sonner.jsx",
          "purpose": "Toasts (salvo, alerta criado, etc.)"
        }
      ]
    }
  },

  "page_blueprints": {
    "1_app_shell": {
      "sidebar": {
        "sections": [
          {
            "label": "Core",
            "items": [
              "Dashboard",
              "Watchlists",
              "Screener",
              "News",
              "Alerts",
              "Notifications"
            ]
          },
          {
            "label": "Account",
            "items": [
              "Settings",
              "Upgrade"
            ]
          },
          {
            "label": "Admin",
            "items": [
              "Superadmin (role-gated)"
            ]
          }
        ],
        "footer": "Plano atual + CTA Upgrade (apenas se não for Investidor)"
      },
      "topbar": {
        "left": "Breadcrumb + Page title",
        "center": "Global search (Command) com placeholder i18n",
        "right": "Idioma/moeda (DropdownMenu), Notifications bell, User menu"
      },
      "micro_interactions": [
        "Sidebar collapse: width transition (transition-[width] duration-200) + labels fade (transition-opacity)",
        "Nav item hover: bg-muted/60 + left indicator (2px) em accent",
        "Search open: Command dialog com shortcut hint (⌘K/Ctrl+K)"
      ],
      "data_testid": {
        "sidebar": "app-shell-sidebar",
        "sidebar-toggle": "app-shell-sidebar-toggle",
        "global-search": "app-shell-global-search",
        "notifications-button": "app-shell-notifications-button",
        "user-menu": "app-shell-user-menu",
        "language-switch": "app-shell-language-switch",
        "currency-switch": "app-shell-currency-switch"
      }
    },

    "2_dashboard": {
      "goal": "Responder em 3 segundos: quais são as melhores oportunidades hoje e o que fazer agora.",
      "layout": {
        "grid": "lg:grid-cols-12",
        "left_main": "col-span-12 lg:col-span-8",
        "right_rail": "col-span-12 lg:col-span-4"
      },
      "sections": [
        {
          "name": "Oportunidades de hoje",
          "component": "OpportunityScoreCardRow",
          "notes": "Linha de 3 cards com ScoreDial + SignalBadge + 52w mini gauge + CTA 'Ver detalhe'",
          "loading": "Skeleton cards (altura fixa)",
          "empty": "Card com explicação + botão 'Ajustar filtros do screener'"
        },
        {
          "name": "Watchlist",
          "component": "WatchlistTableOrCards",
          "notes": "Default: tabela em desktop (densidade). Mobile: cards empilhados. Ordenar por score.",
          "actions": "Sort, filter, quick alert",
          "loading": "Skeleton table rows",
          "empty": "Empty state com CTA 'Adicionar ativos' (abre Command)"
        },
        {
          "name": "Descubra oportunidades",
          "component": "DiscoveryBento",
          "notes": "Bento com 4 tiles: 'Dividendos altos', 'Perto da mínima 52w', 'Analistas otimistas', 'Score subindo'. Cada tile abre screener com filtros predefinidos."
        }
      ],
      "data_testid": {
        "today-opportunities": "dashboard-today-opportunities",
        "watchlist": "dashboard-watchlist",
        "discovery": "dashboard-discovery"
      }
    },

    "3_screener": {
      "layout": "two_panel",
      "left_filters": {
        "container": "Card + ScrollArea",
        "controls": [
          "Select: mercado/país",
          "Slider: Opportunity Score min",
          "Slider: Dividend yield range",
          "Slider: distância da mínima 52w",
          "Checkbox: somente com target price",
          "Button: Reset"
        ],
        "sticky": "Em desktop, filtros sticky top-16"
      },
      "results": {
        "header": "Resumo: N resultados + chips de filtros (Badge) + export/columns",
        "table": "Table com colunas: Asset, Price, 52w range mini, Target, Yield, Score, Signal, Actions",
        "row_actions": "Add to watchlist, Create alert, Open detail",
        "pagination": "Pagination + page size"
      },
      "states": {
        "loading": "Skeleton rows + skeleton filter controls",
        "empty": "Card: 'Nenhum ativo corresponde' + botão Reset + sugestão de relaxar filtros",
        "error": "Alert com retry"
      },
      "data_testid": {
        "filters-panel": "screener-filters-panel",
        "results-table": "screener-results-table",
        "reset-filters": "screener-reset-filters-button"
      }
    },

    "4_asset_detail": {
      "layout": "detail",
      "header": {
        "left": "Nome + ticker + exchange + price + delta",
        "right": "CTAs: Add to watchlist, Create alert, Share (optional)",
        "below": "SignalBadge + Opportunity Score (ScoreDial)"
      },
      "main": {
        "tabs": [
          "Overview",
          "Dividends",
          "Analyst target",
          "News"
        ],
        "overview_grid": [
          "Card: RangeGauge 52w (low/current/high/target)",
          "Card: Key stats (yield, payout, next ex-date, etc.)",
          "Card: Explanation 'Por que este score?' (texto curto + bullets)"
        ]
      },
      "right_rail": {
        "cards": [
          "Alerts for this asset (list + quick create)",
          "Recent news (ScrollArea)"
        ]
      },
      "states": {
        "loading": "Skeleton header + skeleton cards",
        "empty": "Se faltar target/yield: mostrar placeholders e tooltip 'dados indisponíveis'",
        "error": "Alert + retry"
      },
      "data_testid": {
        "asset-detail-header": "asset-detail-header",
        "asset-detail-score": "asset-detail-opportunity-score",
        "asset-detail-range": "asset-detail-52w-range",
        "asset-detail-add-watchlist": "asset-detail-add-to-watchlist-button",
        "asset-detail-create-alert": "asset-detail-create-alert-button"
      }
    },

    "5_news": {
      "layout": "grid 12 cols",
      "left": "Feed (col-span-12 lg:col-span-8) com cards compactos",
      "right": "Filtros + trending tickers (col-span-12 lg:col-span-4)",
      "components": [
        "Tabs: All / Dividends / Macro / Earnings",
        "Card list com fonte, timestamp, tickers relacionados (Badge)",
        "Skeleton list"
      ],
      "data_testid": {
        "news-feed": "news-feed",
        "news-filters": "news-filters"
      }
    },

    "6_alerts": {
      "layout": "table-first",
      "header_actions": "Button 'Criar alerta' abre Dialog",
      "table": "Table com colunas: Asset, Condition, Threshold, Channel, Status, Last triggered, Actions",
      "edit": "Dialog com Form (shadcn form primitives)",
      "states": {
        "loading": "Skeleton rows",
        "empty": "Empty state com CTA criar primeiro alerta",
        "error": "Alert"
      },
      "data_testid": {
        "alerts-create": "alerts-create-button",
        "alerts-table": "alerts-table"
      }
    },

    "7_notifications_inbox": {
      "layout": "split list/detail em desktop; stack em mobile",
      "list": "ScrollArea com itens (unread highlight) + filtros (Tabs: All/Alerts/News/System)",
      "detail": "Card com conteúdo + ações (mark read, mute asset)",
      "states": {
        "empty": "Mensagem 'Tudo em dia' + sugestão de criar alertas",
        "loading": "Skeleton list"
      },
      "data_testid": {
        "notifications-list": "notifications-list",
        "notifications-detail": "notifications-detail",
        "notifications-mark-read": "notifications-mark-read-button"
      }
    },

    "8_settings": {
      "layout": "tabs",
      "tabs": [
        "Profile",
        "Preferences",
        "Notifications",
        "Billing"
      ],
      "preferences": "Idioma (Select), moeda (Select), timezone (Select)",
      "notifications": "Switches por categoria + frequência (Select)",
      "billing": "Plano atual + histórico + CTA upgrade",
      "data_testid": {
        "settings-tabs": "settings-tabs",
        "settings-language": "settings-language-select",
        "settings-currency": "settings-currency-select",
        "settings-save": "settings-save-button"
      }
    },

    "9_upgrade_pricing": {
      "goal": "Upgrade dentro do app (não marketing): claro, comparável, confiável.",
      "layout": "3 cards em grid (1 col mobile, 3 col desktop) + comparação em tabela abaixo",
      "plans": [
        {
          "name": "Iniciante",
          "price": "$4,97",
          "cta": "Começar",
          "highlight": "neutro"
        },
        {
          "name": "Pro",
          "price": "$12,97",
          "cta": "Upgrade para Pro",
          "highlight": "recomendado (borda accent + badge)"
        },
        {
          "name": "Investidor",
          "price": "$24,99",
          "cta": "Upgrade para Investidor",
          "highlight": "premium (borda primary + sombra elev-2)"
        }
      ],
      "components": [
        "Card",
        "Badge",
        "Button",
        "Table (comparação de features)",
        "Alert (garantia/nota de cobrança)"
      ],
      "states": {
        "loading": "Skeleton cards",
        "error": "Alert + retry"
      },
      "data_testid": {
        "pricing-plan-starter": "pricing-plan-starter",
        "pricing-plan-pro": "pricing-plan-pro",
        "pricing-plan-investor": "pricing-plan-investor",
        "pricing-upgrade-pro": "pricing-upgrade-pro-button",
        "pricing-upgrade-investor": "pricing-upgrade-investor-button"
      }
    },

    "10_superadmin": {
      "layout": "tabs + stats cards + tables",
      "top": "KPI cards (users, MRR, alerts triggered, data provider status)",
      "tabs": [
        "Overview",
        "Users",
        "Subscriptions",
        "Data Providers",
        "Settings"
      ],
      "tables": "Alta densidade: sticky header, zebra sutil, row actions em DropdownMenu",
      "states": {
        "loading": "Skeleton cards + skeleton table",
        "empty": "Empty state contextual",
        "error": "Alert"
      },
      "data_testid": {
        "superadmin-tabs": "superadmin-tabs",
        "superadmin-users-table": "superadmin-users-table"
      }
    }
  },

  "motion_and_microinteractions": {
    "principles": [
      "Micro-animações curtas (150–220ms) para hover/press",
      "Sem transition: all (proibido)",
      "Preferir transition-colors, transition-opacity, transition-shadow, transition-[width]",
      "Entrada de páginas: fade + translate-y pequeno (Framer Motion opcional)"
    ],
    "recommended_library": {
      "name": "framer-motion",
      "why": "Animações de entrada e transições de layout (sidebar collapse, cards) sem hacks",
      "install": "npm i framer-motion",
      "usage_snippet_js": "import { motion } from 'framer-motion';\n\nexport default function Page(){\n  return (\n    <motion.div initial={{opacity:0, y:8}} animate={{opacity:1, y:0}} transition={{duration:0.18}} data-testid=\"page-container\">\n      ...\n    </motion.div>\n  );\n}"
    },
    "button_states": {
      "hover": "shadow-sm + bg shift",
      "press": "active:scale-[0.98] (somente botões)",
      "focus": "ring-2 ring-[color:var(--dz-focus)] ring-offset-2"
    }
  },

  "data_states": {
    "loading": {
      "rule": "Sempre mostrar Skeleton com dimensões finais (evita layout shift)",
      "patterns": [
        "Cards: skeleton title + 2 linhas + bloco circular para ScoreDial",
        "Tables: 8–12 linhas skeleton",
        "Side rails: skeleton list"
      ]
    },
    "empty": {
      "rule": "Explicar por que está vazio + ação primária",
      "components": [
        "Card + icon (lucide) + texto + Button"
      ]
    },
    "error": {
      "rule": "Alert inline + botão Retry + link 'Status do provedor' (admin) quando aplicável"
    }
  },

  "accessibility": {
    "requirements": [
      "WCAG AA contraste (especialmente badges em dark mode)",
      "Focus visível em todos os controles",
      "Tabelas: headers semânticos + aria-sort quando ordenável",
      "Command/search: navegação por teclado",
      "Tooltips: não conter informação crítica única (duplicar em texto quando necessário)"
    ]
  },

  "data_testid_convention": {
    "rule": "kebab-case, descrevendo função/role (não aparência)",
    "examples": [
      "watchlist-add-asset-button",
      "screener-apply-filters-button",
      "asset-detail-price",
      "notifications-unread-count"
    ]
  },

  "image_urls": {
    "note": "Áreas logadas: evitar fotos grandes; usar ilustrações/ícones leves apenas em empty states.",
    "empty_state_illustrations": [
      {
        "category": "empty-state",
        "description": "Ilustração abstrata suave para 'watchlist vazia' (usar como <img> opcional, com fallback sem imagem)",
        "url": "https://images.unsplash.com/photo-1559526324-593bc073d938?auto=format&fit=crop&w=1200&q=60"
      },
      {
        "category": "empty-state",
        "description": "Ilustração/texture para 'nenhuma notificação' (calma, minimal)",
        "url": "https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1200&q=60"
      }
    ],
    "textures": [
      {
        "category": "texture",
        "description": "Noise/grain overlay reference (preferir CSS, mas pode usar como background-image em baixa opacidade)",
        "url": "https://images.unsplash.com/photo-1528459801416-a9e53bbf4e17?auto=format&fit=crop&w=1200&q=60"
      }
    ]
  },

  "instructions_to_main_agent": [
    "Manter tokens existentes; não inventar nova paleta nem trocar fontes.",
    "Implementar novo AppShell com sidebar responsiva (Sheet no mobile, colapsável no desktop).",
    "Preservar/reutilizar componentes existentes: ScoreDial, RangeGauge, SignalBadge, AssetCard.",
    "Migrar watchlist para modo tabela em desktop (shadcn Table) e cards em mobile.",
    "Adicionar skeleton/empty/error states em todas as páginas listadas.",
    "Garantir tolerância a strings longas (i18n) e números com .tnum.",
    "Adicionar data-testid em todos os elementos interativos e informativos críticos.",
    "Não usar transition: all; usar transições específicas.",
    "Usar lucide-react para ícones; evitar emojis."
  ],

  "appendix_general_ui_ux_design_guidelines": "<General UI UX Design Guidelines>\n    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.\n</General UI UX Design Guidelines>"
}
