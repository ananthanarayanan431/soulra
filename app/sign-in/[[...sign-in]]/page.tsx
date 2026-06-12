import Link from "next/link";
import { SignIn } from "@clerk/nextjs";
import { Wordmark } from "@/components/ui";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-paper">
      <Wordmark size={22} />
      <SignIn />
      <p className="text-sm text-muted">
        Don&rsquo;t have an account?{" "}
        <Link href="/sign-up" className="text-[#7a5c3e] hover:text-ink">
          Sign up
        </Link>
      </p>
    </div>
  );
}
