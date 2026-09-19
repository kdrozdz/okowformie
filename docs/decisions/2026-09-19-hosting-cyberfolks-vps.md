# Hosting: Cyberfolks VPS zamiast AWS

- **Decyzja:** Deploy całego stacku (frontend, backend, Postgres, Redis — wszystko przez docker-compose) na jednym serwerze VPS Cyberfolks, linia **vroot** (root/SSH, KVM, pełna kontrola). Rekomendowany plan: **vroot_SPRINT!** (4 vCPU, 8 GB RAM, 100 GB NVMe) — patrz uzasadnienie w rozmowie z 2026-09-19.
- **Kontekst:** Wcześniejsze `CLAUDE.md` zakładało hosting na AWS (ECS/App Runner/Lightsail, RDS, S3, Secrets Manager, CloudFront). Użytkownik zdecydował: bez AWS, serwer kupujemy na Cyberfolks.
- **Alternatywy rozważone (oferta Cyberfolks, dane z 2026-09-19, ceny promocyjne, weryfikować przy zakupie):**
  - `vroot_START!` — 1 vCPU, 2 GB RAM, 30 GB NVMe, ~24,90 zł/mies. Odrzucone: za mało RAM na Next.js + Django + Postgres + Redis jednocześnie, zero marginesu.
  - `vroot_RUN!` — 2 vCPU, 4 GB RAM, 60 GB NVMe, ~49,90 zł/mies promo. Realny fallback budżetowy, ale ciasny margines pod wzrost.
  - `vroot_SPRINT!` (wybrany) — 4 vCPU, 8 GB RAM, 100 GB NVMe. W promocji ta sama cena co RUN (~49,90 zł/mies), 2x zasobów — najlepszy stosunek ceny do możliwości, zapas pod fazę 2/3.
  - `vroot_JUMP!` — 8 vCPU, 12 GB RAM, 160 GB NVMe, ~89,90 zł/mies promo. Odrzucone na start jako przewymiarowane dla bloga fazy 1; do rozważenia przy realnym wzroście ruchu.
  - VPS zarządzane (`vps_*`, panel typu cPanel) — odrzucone: ograniczają pełny dostęp root potrzebny pod własny stack Docker.
- **Status:** aktywna.

## Otwarte pytania (nie rozstrzygnięte tą decyzją)
Rezygnacja z AWS zostawia kilka referencji w regułach projektu, które trzeba jeszcze pojednać z nową rzeczywistością:
- Media/upload obrazów — dotąd zakładane S3 (`.claude/rules/scope.md`). Zostajemy przy S3 jako czystym object storage, czy przechodzimy na coś natywnego dla Cyberfolks / wolumen na VPS?
- Sekrety — dotąd AWS Secrets Manager (`.claude/rules/security.md`). Alternatywa dla pojedynczego VPS: `.env` poza repo, uprawnienia 600, bez wildcardów w dostępie.
- CDN przed API i mediami — dotąd CloudFront (`.claude/rules/performance.md`).
- `infra-agent` i jego reguły są w większości pisane pod AWS (IAM/OIDC, Terraform/CDK, ECS) — wymagają przepisania pod deploy VPS (SSH + docker compose, CI/CD przez GitHub Actions → SSH zamiast OIDC → AWS).

Nierozstrzygnięte do czasu jawnej decyzji użytkownika — nie zgadywać.
