/**
 * CheckoutForm — payment form using Stripe Elements hosted fields.
 *
 * The PaymentElement renders card input fields inside a Stripe-hosted
 * iframe, ensuring raw card data never enters JOL's JavaScript scope.
 * This maintains PCI DSS SAQ A eligibility.
 */

import { useState } from "react";
import { PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";

interface CheckoutFormProps {
  orderId: string;
  onSuccess: (paymentIntentId: string) => void;
  onError: (error: string) => void;
}

export function CheckoutForm({ orderId, onSuccess, onError }: CheckoutFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);

    const { error, paymentIntent } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/payment/result?order=${orderId}`,
      },
      redirect: "if_required",
    });

    setIsProcessing(false);

    if (error) {
      const msg = error.message || "An unexpected error occurred.";
      setErrorMessage(msg);
      onError(msg);
    } else if (paymentIntent && paymentIntent.status === "succeeded") {
      onSuccess(paymentIntent.id);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="checkout-form">
      <PaymentElement
        options={{
          layout: "tabs",
          defaultValues: {
            billingDetails: {
              address: {
                country: "LT",
              },
            },
          },
        }}
      />

      {errorMessage && (
        <div className="error-message" role="alert">
          {errorMessage}
        </div>
      )}

      <button
        type="submit"
        disabled={isProcessing || !stripe || !elements}
        className="pay-button"
      >
        {isProcessing ? "Processing..." : "Pay Now"}
      </button>
    </form>
  );
}
