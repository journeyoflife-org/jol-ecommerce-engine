/**
 * CSP Nonce Management — PCI DSS Req. 6.4.3
 *
 * Generates and manages Content Security Policy nonces for script
 * integrity on payment pages. Each page load receives a unique nonce
 * from the server, and this module provides access to it.
 *
 * Reference: PCI DSS v4.0.1 Requirement 6.4.3
 */

/**
 * Retrieve the CSP nonce from the server-injected meta tag.
 * The nonce is generated server-side per request and injected
 * into the HTML <meta> tag.
 */
export function getCSPNonce(): string {
  const metaTag = document.querySelector('meta[name="csp-nonce"]');
  if (metaTag) {
    return metaTag.getAttribute("content") || "";
  }
  console.warn("CSP nonce meta tag not found. Payment page script integrity may be compromised.");
  return "";
}

/**
 * Apply the CSP nonce to a dynamically created script element.
 * Use this when loading scripts programmatically on payment pages.
 */
export function applyNonceToScript(script: HTMLScriptElement): void {
  const nonce = getCSPNonce();
  if (nonce) {
    script.nonce = nonce;
  }
}

/**
 * Verify that all script elements on the page have valid nonces.
 * Called during payment page initialization for PCI Req. 6.4.3 compliance.
 */
export function verifyAllScriptsHaveNonce(): boolean {
  const scripts = document.querySelectorAll("script");
  const nonce = getCSPNonce();

  for (const script of scripts) {
    // External scripts (src) are governed by CSP script-src
    // Inline scripts must have a nonce
    if (!script.src && script.nonce !== nonce) {
      console.error(
        "PCI Req. 6.4.3 violation: inline script found without valid CSP nonce.",
        script
      );
      return false;
    }
  }
  return true;
}
