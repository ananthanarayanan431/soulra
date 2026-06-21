import Link from "next/link";
import { SignIn } from "@clerk/nextjs";
import { AuthLayout } from "@/components/layout";

export default function SignInPage() {
  return (
    <AuthLayout>
      <div className="flex flex-col items-center gap-6">
        <SignIn />
        <p className="text-sm text-muted">
          Don&rsquo;t have an account?{" "}
          <Link href="/sign-up" className="text-[#7a5c3e] hover:text-ink">
            Sign up
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
