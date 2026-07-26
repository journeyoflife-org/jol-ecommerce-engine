/**
 * Header Monitor — PCI DSS v4.0.1 Requirement 11.6.1
 *
 * Automated detection of unauthorized HTTP header or cookie changes
 * on payment pages. This is mandatory under PCI DSS v4.0.1 regardless
 * of using Stripe or any other payment processor.
 *
 * Monitors:
 * - Content-Security-Policy header integrity
 * - Cookie modifications (unexpected Set-Cookie)
 * - Response header tampering via proxy/interception
 *
 * Reference: https://cside.com/blog/can-you-use-stripe-for-pci-dss
 */

interface HeaderChangeAlert {
  timestamp: string;
  type: "header_change" | "cookie_change" | "csp_violation";
  detail: string;
  severity: "warning" | "critical";
}

type AlertCallback = (alert: HeaderChangeAlert) => void;

/**
 * Expected security headers on payment pages.
 * These are set by the server via csp_headers.py.
 */
const EXPECTED_HEADERS: Record<string, string> = {
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY",
  "strict-transport-security": "max-age=63072000; includeSubDomains; preload",
  "referrer-policy": "strict-origin-when-cross-origin",
};

/**
 * Known and authorized cookie names on payment pages.
 * Any cookie outside this list triggers an alert.
 */
const AUTHORIZED_COOKIES: Set<string> = new Set([
  "session_id",
  "csrf_token",
  "__stripe_sid",
  "__stripe_mid",
]);

export class HeaderMonitor {
  private alerts: HeaderChangeAlert[] = [];
  private alertCallbacks: AlertCallback[] = [];
  private cookieObserver: MutationObserver | null = null;

  /**
   * Register a callback for header change alerts.
   */
  onAlert(callback: AlertCallback): void {
    this.alertCallbacks.push(callback);
  }

  /**
   * Start monitoring for unauthorized header/cookie changes.
   * Call this on payment page initialization.
   */
  start(): void {
    this.monitorCSPViolations();
    this.monitorCookieChanges();
    this.verifyInitialHeaders();
  }

  /**
   * Stop all monitoring.
   */
  stop(): void {
    if (this.cookieObserver) {
      this.cookieObserver.disconnect();
      this.cookieObserver = null;
    }
  }

  /**
   * Get all recorded alerts.
   */
  getAlerts(): HeaderChangeAlert[] {
    return [...this.alerts];
  }

  private emitAlert(alert: HeaderChangeAlert): void {
    this.alerts.push(alert);
    this.alertCallbacks.forEach((cb) => cb(alert));

    // In production, send to SIEM/monitoring endpoint
    if (alert.severity === "critical") {
      console.error("[PCI 11.6.1] CRITICAL:", alert.detail);
      this.reportToSIEM(alert);
    } else {
      console.warn("[PCI 11.6.1] WARNING:", alert.detail);
    }
  }

  private monitorCSPViolations(): void {
    document.addEventListener("securitypolicyviolation", (event: Event) => {
      const violation = event as SecurityPolicyViolationEvent;
      this.emitAlert({
        timestamp: new Date().toISOString(),
        type: "csp_violation",
        detail: `CSP violation: ${violation.violatedDirective} blocked ${violation.blockedURI}`,
        severity: "critical",
      });
    });
  }

  private monitorCookieChanges(): void {
    const originalCookie = document.cookie;
    let lastCookie = originalCookie;

    // Poll for cookie changes (MutationObserver doesn't watch document.cookie)
    const checkCookies = (): void => {
      if (document.cookie !== lastCookie) {
        const newCookies = this.parseCookies(document.cookie);
        const oldCookies = this.parseCookies(lastCookie);

        for (const [name] of newCookies) {
          if (!oldCookies.has(name) && !AUTHORIZED_COOKIES.has(name)) {
            this.emitAlert({
              timestamp: new Date().toISOString(),
              type: "cookie_change",
              detail: `Unauthorized cookie detected: ${name}`,
              severity: "warning",
            });
          }
        }

        lastCookie = document.cookie;
      }
    };

    setInterval(checkCookies, 2000);
  }

  private verifyInitialHeaders(): void {
    // Note: JavaScript cannot read response headers directly.
    // Server should expose expected headers via meta tags or API.
    // This verification checks via fetch to a dedicated endpoint.
    fetch("/api/v1/health", { credentials: "include" })
      .then((response) => {
        for (const [header, expectedValue] of Object.entries(EXPECTED_HEADERS)) {
          const actual = response.headers.get(header);
          if (actual !== expectedValue) {
            this.emitAlert({
              timestamp: new Date().toISOString(),
              type: "header_change",
              detail: `Header "${header}" expected "${expectedValue}" but got "${actual || "missing"}"`,
              severity: "critical",
            });
          }
        }
      })
      .catch(() => {
        this.emitAlert({
          timestamp: new Date().toISOString(),
          type: "header_change",
          detail: "Unable to verify security headers — health check failed",
          severity: "warning",
        });
      });
  }

  private parseCookies(cookieString: string): Map<string, string> {
    const cookies = new Map<string, string>();
    cookieString.split(";").forEach((pair) => {
      const [name, value] = pair.trim().split("=");
      if (name) {
        cookies.set(name, value || "");
      }
    });
    return cookies;
  }

  private reportToSIEM(alert: HeaderChangeAlert): void {
    // In production, POST to SIEM/monitoring endpoint
    fetch("/api/v1/security/alerts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(alert),
      credentials: "include",
    }).catch(() => {
      console.error("[PCI 11.6.1] Failed to report alert to SIEM");
    });
  }
}

/**
 * Singleton instance for use across the payment page.
 */
export const headerMonitor = new HeaderMonitor();
