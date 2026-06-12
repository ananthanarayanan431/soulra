import Link from "next/link";
import { SignUp } from "@clerk/nextjs";
import { AuthLayout } from "@/components/layout";

export default function SignUpPage() {
  return (
    <AuthLayout>
      <div className="flex flex-col items-center gap-6">
        <SignUp />
        <p className="text-sm text-muted">
          Already have an account?{" "}
          <Link href="/sign-in" className="text-[#7a5c3e] hover:text-ink">
            Sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
