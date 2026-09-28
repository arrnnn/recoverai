import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const WORDMARK = [
  { text: "Recover", tone: "text-foreground" },
  { text: "AI", tone: "text-[#9c8362]" },
];

export default function SplashPage() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-gradient-to-br from-white via-slate-50 to-blue-50 px-6 text-center">
      {/* decorative chart illustration, top-left */}
      <svg
        aria-hidden="true"
        viewBox="0 0 220 160"
        className="animate-float-slow pointer-events-none absolute -left-6 top-16 h-40 w-56 opacity-40 sm:left-10 sm:top-24"
      >
        <rect x="20" y="90" width="20" height="50" rx="4" fill="#c7d7ee" />
        <rect x="55" y="65" width="20" height="75" rx="4" fill="#c7d7ee" />
        <rect x="90" y="100" width="20" height="40" rx="4" fill="#c7d7ee" />
        <rect x="125" y="45" width="20" height="95" rx="4" fill="#b7ccec" />
        <polyline
          points="30,80 65,55 100,70 135,25 170,15"
          fill="none"
          stroke="#8fb0e0"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {[30, 65, 100, 135, 170].map((x, i) => (
          <circle key={i} cx={x} cy={[80, 55, 70, 25, 15][i]} r="4" fill="#7ba3dd" />
        ))}
      </svg>

      {/* decorative card illustration, right side */}
      <svg
        aria-hidden="true"
        viewBox="0 0 220 150"
        className="animate-float-slow-delayed pointer-events-none absolute -right-8 top-1/3 h-44 w-64 opacity-40 sm:right-6"
      >
        <rect x="15" y="15" width="190" height="120" rx="16" fill="#dbe6f7" transform="rotate(-6 110 75)" />
        <rect x="35" y="45" width="28" height="20" rx="4" fill="#aec4e8" transform="rotate(-6 49 55)" />
        <circle cx="150" cy="95" r="4" fill="#aec4e8" />
        <circle cx="164" cy="95" r="4" fill="#aec4e8" />
        <circle cx="178" cy="95" r="4" fill="#aec4e8" />
      </svg>

      {/* soft wave at the bottom */}
      <svg
        aria-hidden="true"
        viewBox="0 0 1440 320"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-40 w-full opacity-50"
        preserveAspectRatio="none"
      >
        <path
          fill="#dbe6f7"
          d="M0,224L60,213.3C120,203,240,181,360,181.3C480,181,600,203,720,224C840,245,960,267,1080,256C1200,245,1320,203,1380,181.3L1440,160L1440,320L0,320Z"
        />
      </svg>

      {/* content */}
      <div className="relative z-10 flex flex-col items-center">
        <span className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-foreground text-2xl font-extrabold text-background shadow-lg">
          R
        </span>

        <h1 className="text-5xl font-extrabold tracking-tight sm:text-6xl">
          {WORDMARK.map((word, wi) => (
            <span key={wi} className={word.tone}>
              {word.text.split("").map((letter, li) => (
                <span
                  key={li}
                  className="inline-block transition-all duration-200 ease-out hover:-translate-y-1.5 hover:text-blue-600"
                >
                  {letter}
                </span>
              ))}
            </span>
          ))}
        </h1>

        <p className="mt-5 max-w-lg text-2xl font-semibold leading-snug text-[#41608a] sm:text-3xl">
          Smarter recovery. Higher revenue.
          <br />
          Powered by AI.
        </p>

        <p className="mt-4 max-w-md text-sm font-medium text-muted-foreground">
          Detects at-risk payments, finds the right action, and helps you recover more — automatically.
        </p>
        

        <Button
          asChild
          size="lg"
          className="mt-9 rounded-full px-8 py-6 text-base font-bold shadow-lg transition-transform duration-200 hover:scale-105 hover:shadow-xl"
        >
          <Link href="/dashboard">
            Start
            <ArrowRight className="size-4" />
          </Link>
        </Button>
      </div>
    </div>
  );
}