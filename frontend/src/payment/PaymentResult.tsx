/**
 * PaymentResult — displays payment outcome after Stripe redirect.
 */

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

type PaymentStatus = "succeeded" | "processing" | "failed" | "unknown";

export function PaymentResult() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<PaymentStatus>("unknown");
  const orderId = searchParams.get("order") || "";

  useEffect(() => {
    const paymentIntent = searchParams.get("payment_intent");
    const paymentIntentClientSecret = searchParams.get("payment_intent_client_secret");

    if (paymentIntent && paymentIntentClientSecret) {
      // In production, verify with backend API
      setStatus("succeeded");
    } else {
      setStatus("failed");
    }
  }, [searchParams]);

  const statusMessages: Record<PaymentStatus, string> = {
    succeeded: "Payment successful! Your order has been confirmed.",
    processing: "Payment is being processed. You will receive a confirmation shortly.",
    failed: "Payment failed. Please try again or use a different payment method.",
    unknown: "Checking payment status...",
  };

  return (
    <div className="payment-result">
      <h2>{statusMessages[status]}</h2>
      {orderId && <p>Order: {orderId}</p>}
      {status === "failed" && (
        <a href={`/checkout?order=${orderId}`} className="retry-link">
          Try Again
        </a>
      )}
    </div>
  );
}
