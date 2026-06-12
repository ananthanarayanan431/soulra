import { SignUp } from "@clerk/nextjs";
import { Wordmark } from "@/components/ui";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-paper">
      <Wordmark size={22} />
      <SignUp />
    </div>
  );
}
