/**
 * InvoiceDownload — download invoice PDF with VAT breakdown.
 */

interface InvoiceDownloadProps {
  invoiceNumber: string;
  orderId: string;
}

export function InvoiceDownload({ invoiceNumber, orderId }: InvoiceDownloadProps) {
  const handleDownload = async () => {
    try {
      const response = await fetch(
        `/api/v1/orders/${orderId}/invoice`,
        { credentials: "include" }
      );

      if (!response.ok) {
        throw new Error("Failed to download invoice");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `invoice-${invoiceNumber}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      console.error("Invoice download failed");
    }
  };

  return (
    <button onClick={handleDownload} className="invoice-download-btn">
      Download Invoice ({invoiceNumber})
    </button>
  );
}
