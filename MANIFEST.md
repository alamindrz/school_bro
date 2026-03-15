# THE DETs TOOLKIT: PLATFORM MANIFESTO

Domain: Nigerian SMS K-12 (6-3-3-4) Infrastructure
Vision: A decoupled, pluggable ecosystem sold as a "School-in-a-Box" for semi-autonomous income.

## Core Architecture Rules

1. **No Models in Views** - Views call Services (write) or Selectors (read)
2. **No Cross-App Signals** - Signals only trigger within same app
3. **Service-Mediated Communication** - Apps never import each other's models directly
4. **Permission-Based Navigation** - Dynamic menus based on user.has_perm()
5. **The "No-Customization" Rule** - Everything is a toggle in SiteConfig

See `/docs/ARCHITECTURE.md` for complete details.
