import type { Dictionary } from "@/lib/i18n/dictionary";

import styles from "../Header.module.css";
import { FacebookIcon } from "./FacebookIcon";
import { InstagramIcon } from "./InstagramIcon";
import { LinkedInIcon } from "./LinkedInIcon";

/**
 * Rejestr platform social media obsługiwanych w headerze — zamknięty zbiór
 * (`linkedin`/`instagram`/`facebook`), zgodny z `branding.SocialPlatform` po
 * stronie backendu. Ikonki SVG i klasy CSS są zaszyte tutaj (nie w panelu),
 * bo dowolny SVG/HTML z bazy renderowany bez sanityzacji byłby luką
 * bezpieczeństwa (`.claude/rules/security.md`) — nowa platforma wymaga
 * jednorazowej zmiany kodu, to świadoma granica, nie brakująca funkcja.
 */
export interface SocialIconDefinition {
  className: string;
  ariaLabel: string;
  Icon: () => React.JSX.Element;
}

/** Zbuduj rejestr `platform -> definicja ikony` dla danego słownika językowego. */
export function getSocialIconRegistry(
  headerDict: Dictionary["header"],
): Record<string, SocialIconDefinition> {
  return {
    linkedin: {
      className: styles.isLinkedin,
      ariaLabel: headerDict.linkedinAriaLabel,
      Icon: LinkedInIcon,
    },
    instagram: {
      className: styles.isInstagram,
      ariaLabel: headerDict.instagramAriaLabel,
      Icon: InstagramIcon,
    },
    facebook: {
      className: styles.isFacebook,
      ariaLabel: headerDict.facebookAriaLabel,
      Icon: FacebookIcon,
    },
  };
}
