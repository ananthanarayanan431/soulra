import { listTraditions } from "@/lib/api";
import { TraditionsClient } from "@/components/screens/TraditionsClient";

export default async function TraditionsPage() {
  const data = await listTraditions();
  return <TraditionsClient initialData={data} />;
}
