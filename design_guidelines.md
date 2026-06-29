{
  "brand": {
    "name": "Dipzee",
    "attributes": [
      "trustworthy",
      "calm premium fintech",
      "fast comprehension (3-second decision)",
      "transparent + explainable",
      "internationalized (EN/FR/PT/ES)"
    ],
    "design_principle": "Less is more: each screen answers ONE question with a big Score + plain-language explanation."
  },
  "design_tokens": {
    "css_variables": {
      "notes": "Implement these in /frontend/src/index.css :root and .dark. Keep shadcn HSL vars if needed, but map them to Dipzee tokens below. Prefer using these tokens via Tailwind arbitrary values (e.g., bg-[var(--dz-canvas)]).",
      "colors": {
        "--dz-primary": "#1A1F4D",
        "--dz-mint": "#16E0A3",
        "--dz-ink": "#0F1424",
        "--dz-slate": "#5B6478",
        "--dz-line": "#E6E9F0",
        "--dz-canvas": "#F6F8FB",
        "--dz-surface": "#FFFFFF",

        "--dz-buy": "#16A34A",
        "--dz-buy-deep": "#0E7C4A",
        "--dz-hold": "#F59E0B",
        "--dz-reduce": "#F97316",
        "--dz-sell": "#E5484D",

        "--dz-focus": "#16E0A3",
        "--dz-shadow": "rgba(15, 20, 36, 0.08)",
        "--dz-shadow-strong": "rgba(15, 20, 36, 0.14)",

        "--dz-bg": "var(--dz-canvas)",
        "--dz-fg": "var(--dz-ink)",
        "--dz-muted": "var(--dz-slate)",
        "--dz-border": "var(--dz-line)"
      },
      "dark_mode_mapping": {
        "--dz-bg": "#0E1222",
        "--dz-surface": "#171C2E",
        "--dz-fg": "#E7EAF3",
        "--dz-muted": "#9AA3B8",
        "--dz-border": "rgba(230,233,240,0.14)",
        "--dz-shadow": "rgba(0,0,0,0.35)",
        "--dz-shadow-strong": "rgba(0,0,0,0.55)",
        "note": "Signals (buy/hold/sell) remain the same hues; adjust usage to avoid neon-on-dark glare: use solid badges + subtle tinted backgrounds only."
      },
      "typography": {
        "--dz-font-heading": "'Sora', ui-sans-serif, system-ui",
        "--dz-font-body": "'Inter', ui-sans-serif, system-ui",
        "--dz-font-mono": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
        "--dz-tracking-tight": "-0.02em",
        "--dz-leading-tight": "1.15",
        "--dz-leading-body": "1.5"
      },
      "type_scale_px": {
        "display": 40,
        "h1": 32,
        "h2": 24,
        "h3": 20,
        "body": 16,
        "small": 14,
        "legend": 12
      },
      "radii": {
        "--dz-radius-sm": "10px",
        "--dz-radius-md": "14px",
        "--dz-radius-lg": "18px",
        "--dz-radius-pill": "9999px"
      },
      "shadows": {
        "--dz-elev-1": "0 1px 2px var(--dz-shadow)",
        "--dz-elev-2": "0 10px 24px var(--dz-shadow)",
        "--dz-elev-3": "0 18px 40px var(--dz-shadow-strong)"
      },
      "spacing_scale_px": {
        "2": 8,
        "3": 12,
        "4": 16,
        "5": 20,
        "6": 24,
        "8": 32,
        "10": 40,
        "12": 48,
        "16": 64
      }
    },
    "tailwind_usage": {
      "font": {
        "headings": "font-[var(--dz-font-heading)]",
        "body": "font-[var(--dz-font-body)]",
        "tabular_nums": "[font-variant-numeric:tabular-nums]"
      },
      "color_examples": {
        "page_bg": "bg-[var(--dz-bg)]",
        "card_bg": "bg-[var(--dz-surface)]",
        "text_primary": "text-[var(--dz-fg)]",
        "text_secondary": "text-[var(--dz-muted)]",
        "border": "border-[var(--dz-border)]",
        "primary_button": "bg-[var(--dz-primary)] text-white",
        "mint_cta": "bg-[var(--dz-mint)] text-[var(--dz-primary)]"
      }
    }
  },
  "layout_system": {
    "grid": {
      "app_shell": "Mobile-first. Use a top bar + optional left rail on lg. Content max width: max-w-6xl for dashboard pages; max-w-7xl for landing.",
      "page_padding": "px-4 sm:px-6 lg:px-8",
      "section_spacing": "py-10 sm:py-14 lg:py-16",
      "card_spacing": "p-4 sm:p-5 lg:p-6",
      "bento": "Use 12-col grid on lg: main content col-span-8, side insights col-span-4. On mobile stack with gap-4."
    },
    "navigation": {
      "top_bar": {
        "height": "h-14",
        "style": "Surface bar with bottom border. Left: Dipzee logo. Center (optional): search. Right: language + currency + notifications + user menu.",
        "language_currency": "Use dropdown-menu/select components; keep labels visible (not icon-only) on mobile via Sheet menu.",
        "data_testids": {
          "language_switcher": "topbar-language-switcher",
          "currency_switcher": "topbar-currency-switcher",
          "notifications_button": "topbar-notifications-button",
          "user_menu_button": "topbar-user-menu-button"
        }
      },
      "mobile_nav": "Use Sheet for hamburger. Include primary routes + upgrade CTA."
    }
  },
  "components": {
    "component_path": {
      "shadcn_primary": [
        "/app/frontend/src/components/ui/button.jsx",
        "/app/frontend/src/components/ui/card.jsx",
        "/app/frontend/src/components/ui/badge.jsx",
        "/app/frontend/src/components/ui/tabs.jsx",
        "/app/frontend/src/components/ui/table.jsx",
        "/app/frontend/src/components/ui/dialog.jsx",
        "/app/frontend/src/components/ui/sheet.jsx",
        "/app/frontend/src/components/ui/select.jsx",
        "/app/frontend/src/components/ui/dropdown-menu.jsx",
        "/app/frontend/src/components/ui/input.jsx",
        "/app/frontend/src/components/ui/tooltip.jsx",
        "/app/frontend/src/components/ui/sonner.jsx",
        "/app/frontend/src/components/ui/switch.jsx",
        "/app/frontend/src/components/ui/toggle-group.jsx",
        "/app/frontend/src/components/ui/accordion.jsx",
        "/app/frontend/src/components/ui/calendar.jsx",
        "/app/frontend/src/components/ui/skeleton.jsx",
        "/app/frontend/src/components/ui/separator.jsx",
        "/app/frontend/src/components/ui/scroll-area.jsx"
      ],
      "charts": "Prefer Recharts for simple time series; for the signature dial/gauge use SVG (custom) for pixel-perfect control."
    },
    "buttons": {
      "style": "Professional / Corporate with premium softness: radius 10–14px, subtle elevation, crisp focus ring mint.",
      "variants": {
        "primary": {
          "use": "Primary actions (Login, Create alert, Add to watchlist, Upgrade)",
          "classes": "bg-[var(--dz-primary)] text-white hover:brightness-[1.05] active:brightness-[0.98] shadow-[var(--dz-elev-1)]",
          "focus": "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--dz-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--dz-bg)]"
        },
        "mint_cta": {
          "use": "Landing hero CTA + Upgrade emphasis",
          "classes": "bg-[var(--dz-mint)] text-[var(--dz-primary)] hover:brightness-[0.98] active:brightness-[0.95] shadow-[var(--dz-elev-1)]"
        },
        "secondary": {
          "use": "Less prominent actions",
          "classes": "bg-white border border-[var(--dz-border)] text-[var(--dz-primary)] hover:bg-[rgba(26,31,77,0.04)]"
        },
        "ghost": {
          "use": "Icon buttons in top bar",
          "classes": "bg-transparent hover:bg-[rgba(15,20,36,0.04)]"
        }
      },
      "micro_interactions": {
        "hover": "Use transition-colors and transition-shadow only (no transition: all).",
        "press": "active:translate-y-[0.5px] active:shadow-none",
        "loading": "Use spinner inside button; keep width stable."
      },
      "data_testids": {
        "primary_cta": "primary-cta-button",
        "secondary_cta": "secondary-cta-button"
      }
    },
    "badges_and_signals": {
      "rule": "Signals are separate from brand colors. Never use mint/indigo to indicate Buy/Hold/Sell.",
      "badge_specs": {
        "shape": "rounded-full",
        "size": "text-xs px-2.5 py-1",
        "icon": "Use lucide-react icons (e.g., TrendingUp, Pause, TrendingDown) + label text.",
        "variants": {
          "strong_buy": "bg-[rgba(22,163,74,0.12)] text-[var(--dz-buy-deep)] border border-[rgba(22,163,74,0.25)]",
          "buy": "bg-[rgba(22,163,74,0.10)] text-[var(--dz-buy)] border border-[rgba(22,163,74,0.22)]",
          "hold": "bg-[rgba(245,158,11,0.14)] text-[rgba(146,64,14,1)] border border-[rgba(245,158,11,0.28)]",
          "reduce": "bg-[rgba(249,115,22,0.14)] text-[rgba(154,52,18,1)] border border-[rgba(249,115,22,0.28)]",
          "sell": "bg-[rgba(229,72,77,0.12)] text-[var(--dz-sell)] border border-[rgba(229,72,77,0.26)]"
        }
      },
      "accessibility": "Always pair color with label text (Strong Buy / Hold / Sell) and an icon. Provide aria-label on icon-only badges."
    },
    "opportunity_score_dial": {
      "purpose": "Signature component: instantly communicates actionability.",
      "implementation": {
        "tech": "SVG circle with stroke-dasharray; animate value changes with requestAnimationFrame or CSS transition on stroke-dashoffset.",
        "sizes": {
          "card": "w-[168px] h-[168px] sm:w-[184px] sm:h-[184px]",
          "hero": "w-[220px] h-[220px] lg:w-[260px] lg:h-[260px]"
        },
        "stroke": {
          "track": "stroke-[var(--dz-line)]",
          "track_width": 10,
          "value_width": 12,
          "cap": "round"
        },
        "center_content": {
          "score": "text-4xl font-semibold [font-variant-numeric:tabular-nums] text-[var(--dz-fg)]",
          "label": "text-xs text-[var(--dz-muted)]",
          "badge": "Place directly under score; keep within dial bounds."
        },
        "color_mapping": {
          "0-24": "sell",
          "25-44": "reduce",
          "45-64": "hold",
          "65-84": "buy",
          "85-100": "strong_buy"
        },
        "motion": {
          "enter": "Dial arc draws from 0 to value over 650ms with ease-out.",
          "update": "When score changes, animate 450ms; also crossfade explanation text.",
          "reduced_motion": "If prefers-reduced-motion, snap to value (no arc animation)."
        },
        "data_testids": {
          "dial": "opportunity-score-dial",
          "score_value": "opportunity-score-value",
          "score_badge": "opportunity-score-badge"
        }
      },
      "copy_guidance": "Always show a one-line verdict next to dial: e.g., 'Strong Buy: priced near 52-week low with high yield.' Keep it translatable and short."
    },
    "range_gauge_52w": {
      "purpose": "Shows where current price sits between 52w low/high + analyst target flag.",
      "layout": {
        "desktop": "Single horizontal track with markers: Low | Current | High, plus Target flag above track.",
        "mobile_under_380": "Stack into two rows: Row 1 track + Low/High labels; Row 2 chips for Current and Target with small vertical pointers to approximate positions. Prevent overlap by allowing chips to wrap and by clamping positions."
      },
      "spec": {
        "track": "h-2 rounded-full bg-[var(--dz-line)]",
        "fill": "Optional subtle fill from low->current using primary at 8% opacity (NOT gradient-heavy): bg-[rgba(26,31,77,0.10)]",
        "markers": {
          "low_high": "Tiny ticks at ends + labels below (legend size).",
          "current": "Pill marker (10–12px tall) with border; label chip below: 'Now $11.10'.",
          "target": "Flag chip above track with small caret; use mint border only for emphasis (not signal)."
        },
        "collision_rules": [
          "Clamp marker positions to [2%, 98%]",
          "If |target - current| < 8% then vertically offset target flag (two-tier) or move target chip to second row on mobile",
          "On very small widths, hide tick labels and show Low/High as left/right chips"
        ],
        "data_testids": {
          "gauge": "range-gauge-52w",
          "marker_current": "range-gauge-current-marker",
          "marker_target": "range-gauge-target-marker",
          "label_low": "range-gauge-low-label",
          "label_high": "range-gauge-high-label"
        }
      },
      "accessibility": "Provide a text summary under gauge: '52-week range: $11.04–$22.10. Current: $11.10. Target: $17.33.'"
    },
    "watchlist_cards": {
      "sorting": "Default sort by score desc.",
      "card_layout": {
        "left": "Ticker + company name + small exchange/currency tag",
        "right": "Mini dial (or score pill) + signal badge",
        "bottom": "Key stats row: Price, Yield, Upside to target, 52w position"
      },
      "filters": {
        "use": "toggle-group for chips",
        "chips": [
          "Buy zone only",
          "Income ≥ 4%",
          "Near 52w low",
          "High upside"
        ],
        "data_testids": {
          "filters": "watchlist-filter-chips",
          "card": "watchlist-asset-card"
        }
      },
      "empty_state": "Use Card with icon + short guidance + primary CTA 'Search stocks'."
    },
    "search": {
      "pattern": "Command palette style search (command.jsx) for fast ticker lookup; show recent searches.",
      "data_testids": {
        "search_input": "stock-search-input",
        "search_result": "stock-search-result-item"
      }
    },
    "alerts": {
      "create_modal": "Use dialog.jsx. Fields: symbol, condition (score above/below, price crosses, yield threshold), frequency, channel.",
      "components": ["select", "input", "switch"],
      "data_testids": {
        "open_modal": "create-alert-open-button",
        "submit": "create-alert-submit-button"
      }
    },
    "notifications_inbox": {
      "layout": "Two-column on lg: list left, detail right. On mobile: list only; tap opens detail in Sheet.",
      "components": ["tabs", "scroll-area", "badge"],
      "data_testids": {
        "inbox": "notifications-inbox",
        "notification_item": "notification-list-item"
      }
    },
    "pricing": {
      "toggle": "Use switch.jsx or tabs.jsx for Monthly/Annual. Keep it above pricing cards.",
      "table": "Use card-based pricing (3 cards). Highlight Pro with mint border + subtle shadow.",
      "data_testids": {
        "billing_toggle": "pricing-billing-toggle",
        "plan_card": "pricing-plan-card",
        "upgrade_button": "pricing-upgrade-button"
      }
    },
    "forms_auth": {
      "layout": "Centered column but content-aligned left; max-w-md; use Canvas background with a Surface card.",
      "components": ["card", "input", "button", "separator"],
      "data_testids": {
        "login_form": "login-form",
        "register_form": "register-form",
        "submit": "auth-submit-button"
      }
    }
  },
  "pages": {
    "landing": {
      "hero": {
        "layout": "Z-pattern: left copy + CTAs, right interactive mock (score dial + gauge).",
        "headline": "Buy low. Earn dividends. Sell high — automatically.",
        "subcopy": "Explain in one sentence; keep translatable.",
        "cta": "Start free",
        "email_capture": "Inline input + button; validate; show privacy microcopy.",
        "background": "Solid Canvas with a very subtle mint/indigo decorative blob (max 15% viewport, low opacity). No heavy gradients.",
        "data_testids": {
          "hero_cta": "landing-hero-start-free-button",
          "email_input": "landing-email-capture-input",
          "email_submit": "landing-email-capture-submit"
        }
      },
      "telus_example": {
        "content": "TELUS example card: 11.10 price / 11.04 low / 17.33 target / 10.8% yield -> Strong Buy 96/100.",
        "presentation": "Use a single card with dial + gauge + 4 stat chips. Keep numbers tabular."
      },
      "sections": [
        "3-step how it works",
        "Opportunity Score explainer",
        "Feature grid",
        "Pricing",
        "FAQ",
        "Footer disclaimer"
      ]
    },
    "dashboard": {
      "question": "What are my best opportunities today?",
      "above_fold": "Filters + top 3 opportunities cards.",
      "below_fold": "Table view toggle (cards/table)."
    },
    "asset_detail": {
      "question": "Is this stock a buy right now?",
      "layout": "Top: dial + verdict + actions. Middle: gauge + stats. Bottom: explanation + risks + alerts.",
      "actions": ["Add to watchlist", "Create alert"],
      "data_testids": {
        "add_watchlist": "asset-add-to-watchlist-button",
        "create_alert": "asset-create-alert-button"
      }
    },
    "settings": {
      "question": "How should Dipzee behave for me?",
      "sections": ["Language", "Currency", "Alert preferences", "Subscription"],
      "components": ["select", "switch", "card"],
      "data_testids": {
        "settings": "settings-page",
        "language": "settings-language-select",
        "currency": "settings-currency-select"
      }
    }
  },
  "motion": {
    "principles": [
      "Use motion to explain state changes (score updates, filter changes), not decoration.",
      "Prefer subtle translate (1–2px), opacity fades, and shadow changes.",
      "Respect prefers-reduced-motion."
    ],
    "recommended_library": {
      "name": "framer-motion",
      "why": "Entrance animations for landing hero mock + dial/gauge transitions + list reordering.",
      "install": "npm i framer-motion",
      "usage": "Wrap cards with motion.div; use layout prop for smooth reflow when filters change."
    }
  },
  "data_viz": {
    "recharts": {
      "use_cases": ["mini sparkline on watchlist cards", "dividend history (optional)", "price trend (optional)"],
      "install": "npm i recharts",
      "style": "Thin strokes (2px), muted gridlines using --dz-line, highlight current point with mint ring (not signal)."
    }
  },
  "i18n_and_currency": {
    "rules": [
      "All strings from react-i18next; avoid hard-coded text.",
      "Design for longer FR/PT/ES: allow wrapping; avoid fixed widths on buttons.",
      "Use tabular-nums for all prices/percentages.",
      "Currency formatting via Intl.NumberFormat; show currency code when ambiguous (CAD/USD)."
    ]
  },
  "accessibility": {
    "wcag": "AA",
    "focus": "Always visible focus ring: 2px mint ring + offset.",
    "color_not_alone": "Signals must include label + icon + (optional) pattern/tint.",
    "touch_targets": "Min 44px height for primary controls.",
    "aria": "Icon-only buttons must have aria-label; dial/gauge must have text equivalents."
  },
  "image_urls": {
    "landing_hero_background_optional": [
      {
        "url": "https://images.unsplash.com/photo-1604011237320-8e0506614fdf?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NDh8MHwxfHNlYXJjaHwxfHxjbGVhbiUyMGZpbnRlY2glMjBsaWdodCUyMGRhc2hib2FyZCUyMGFic3RyYWN0fGVufDB8fHxibHVlfDE3ODI2OTgyMDd8MA&ixlib=rb-4.1.0&q=85",
        "category": "landing",
        "description": "Abstract bokeh texture; use as very subtle blurred overlay (opacity 0.06) behind hero mock only."
      }
    ],
    "landing_social_proof_optional": [
      {
        "url": "https://images.unsplash.com/photo-1544717297-fa95b6ee9643?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzOTB8MHwxfHNlYXJjaHwxfHxtaW5pbWFsJTIwb2ZmaWNlJTIwaW52ZXN0b3IlMjBsYXB0b3AlMjBsaWdodHxlbnwwfHx8dGVhbHwxNzgyNjk4MjA3fDA&ixlib=rb-4.1.0&q=85",
        "category": "landing",
        "description": "Investor-at-desk photo; if used, crop to hands/laptop only; avoid faces."
      }
    ],
    "footer_or_about_optional": [
      {
        "url": "https://images.unsplash.com/photo-1601852812536-2f3c6e49a256?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTF8MHwxfHNlYXJjaHwyfHxtb2Rlcm4lMjBjaXR5JTIwc2t5bGluZSUyMG1vcm5pbmclMjBtaW5pbWFsfGVufDB8fHx3aGl0ZXwxNzgyNjk4MjA3fDA&ixlib=rb-4.1.0&q=85",
        "category": "landing",
        "description": "Soft skyline; use as grayscale, low opacity (0.05) in footer background only."
      }
    ]
  },
  "instructions_to_main_agent": {
    "global_css": [
      "Replace CRA default App.css styles; do NOT center align .App.",
      "In index.css, import Google Fonts Sora + Inter and set body font to Inter; headings use Sora.",
      "Map shadcn tokens to Dipzee tokens: background->--dz-bg, card->--dz-surface, border->--dz-border, primary->--dz-primary, ring->--dz-focus.",
      "Set body background to --dz-bg and text to --dz-fg."
    ],
    "component_build_notes_js": [
      "This repo uses .jsx/.js (not .tsx). Keep components in JS and use PropTypes only if already used; otherwise rely on runtime checks.",
      "All interactive and key informational elements MUST include data-testid (kebab-case).",
      "Use lucide-react for icons (no emoji)."
    ],
    "signature_components": [
      "Build OpportunityScoreDial as a reusable component with props: score (0-100), classification, size ('card'|'hero'), showBadge.",
      "Build RangeGauge52w with props: low, high, current, target, currency; implement collision rules for <380px widths.",
      "Ensure both components render an accessible text summary for screen readers."
    ],
    "i18n": [
      "Avoid concatenating strings; use i18next interpolation for numbers and labels.",
      "Allow wrapping for long translations; avoid fixed button widths; prefer flex-wrap."
    ]
  },
  "appendix_general_ui_ux_design_guidelines": "<General UI UX Design Guidelines>  \n    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.\n</General UI UX Design Guidelines>"
}
