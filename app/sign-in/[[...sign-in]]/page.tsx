import { SignIn } from "@clerk/nextjs";
import { Logo } from "@/components/ui";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-paper">
      <Logo size={22} />
      <SignIn />
    </div>
  );
}
