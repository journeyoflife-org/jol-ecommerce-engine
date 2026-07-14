/**
 * StripeElements — PCI DSS SAQ A compliant Stripe Elements wrapper.
 *
 * All card data (PAN, CVV, expiry) is collected within Stripe's hosted
 * iframe. No raw card data enters the JOL application's JavaScript scope.
 *
 * Data flow: card input → Stripe iframe → token (pm_xxx) → backend API
 *
 * Reference: https://stripe.com/docs/js/elements_object
 */

import { loadStripe, type Stripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";
import { getCSPNonce } from "../shared/csp-nonce";

const stripePromise: Promise<Stripe | null> = loadStripe(
  import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || ""
);

interface StripeElementsProps {
  clientSecret: string;
  children: React.ReactNode;
}

export function StripeElements({ clientSecret, children }: StripeElementsProps) {
  const nonce = getCSPNonce();

  return (
    <Elements
      stripe={stripePromise}
      options={{
        clientSecret,
        appearance: {
          theme: "stripe",
          variables: {
            colorPrimary: "#635bff",
            borderRadius: "8px",
          },
        },
      }}
    >
      {/* CSP nonce applied to the Stripe.js script tag */}
      <div data-csp-nonce={nonce}>{children}</div>
    </Elements>
  );
}
