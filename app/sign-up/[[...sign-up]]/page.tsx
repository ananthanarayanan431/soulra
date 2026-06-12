import Link from "next/link";
import { SignUp } from "@clerk/nextjs";
import { Wordmark } from "@/components/ui";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-paper">
      <Wordmark size={22} />
      <SignUp />
      <p className="text-sm text-muted">
        Already have an account?{" "}
        <Link href="/sign-in" className="text-[#7a5c3e] hover:text-ink">
          Sign in
        </Link>
      </p>
    </div>
  );
}
