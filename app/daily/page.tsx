import { getActivePractice } from "@/lib/api";
import { DailyScreen } from "@/components/screens/DailyScreen";

export default async function DailyPage() {
  const arc = await getActivePractice();
  return <DailyScreen arc={arc} />;
}
