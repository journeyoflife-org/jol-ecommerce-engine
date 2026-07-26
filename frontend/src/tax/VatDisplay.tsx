/**
 * VatDisplay — shows VAT breakdown for a given country and amount.
 */

interface VatDisplayProps {
  netAmount: string;
  vatAmount: string;
  grossAmount: string;
  vatRate: string;
  countryCode: string;
  currency?: string;
}

export function VatDisplay({
  netAmount,
  vatAmount,
  grossAmount,
  vatRate,
  countryCode,
  currency = "EUR",
}: VatDisplayProps) {
  const formatCurrency = (amount: string) => {
    const num = parseFloat(amount);
    return new Intl.NumberFormat("en-EU", {
      style: "currency",
      currency,
    }).format(num);
  };

  const formatRate = (rate: string) => {
    return `${(parseFloat(rate) * 100).toFixed(1)}%`;
  };

  return (
    <div className="vat-display">
      <table>
        <tbody>
          <tr>
            <td>Net amount:</td>
            <td>{formatCurrency(netAmount)}</td>
          </tr>
          <tr>
            <td>VAT ({formatRate(vatRate)} — {countryCode}):</td>
            <td>{formatCurrency(vatAmount)}</td>
          </tr>
          <tr className="total">
            <td><strong>Total:</strong></td>
            <td><strong>{formatCurrency(grossAmount)}</strong></td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
